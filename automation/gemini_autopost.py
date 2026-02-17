#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import traceback
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# New SDK Import
try:
    from google import genai
    from google.genai import types
    from google.genai import errors
except ImportError:
    print("Error: 'google-genai' library is missing. Install via: pip install google-genai")
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parents[1]
AUTOMATION_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = AUTOMATION_DIR / "codex_cybersecurity_schema.json"
PHP_LIST_TITLES = AUTOMATION_DIR / "wp_get_post_titles.php"
PHP_LIST_CANDIDATES = AUTOMATION_DIR / "wp_get_profile_candidates.php"
PHP_INSERT_POST = AUTOMATION_DIR / "wp_insert_post.php"
LOCK_PATH = AUTOMATION_DIR / "gemini_autopost.lock"
LOG_DIR = AUTOMATION_DIR / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "gemini_autopost.log"

STOPWORDS = {
    "about", "after", "again", "against", "also", "and", "are", "been",
    "before", "being", "between", "could", "during", "from", "have", "into",
    "more", "most", "over", "that", "their", "them", "then", "there", "these",
    "they", "this", "through", "under", "using", "what", "when", "where",
    "which", "with", "your",
}

class LockHeldError(RuntimeError):
    pass

def timestamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def write_log(message: str, log_file: Path) -> None:
    line = f"[{timestamp()}] {message}"
    print(line, flush=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass

def run_command(args: list[str], *, stdin_text: str | None = None) -> str:
    process = subprocess.Popen(
        args,
        cwd=str(ROOT_DIR),
        stdin=subprocess.PIPE if stdin_text else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input=stdin_text)
    if process.returncode != 0:
        raise RuntimeError(f"Command failed:\n{stderr}")
    return stdout.strip()

def sanitize_schema(schema: dict) -> dict:
    """
    Recursively removes keys from the JSON schema that the Gemini API does not support.
    Specifically: $schema, title, additionalProperties (if boolean), etc.
    """
    if not isinstance(schema, dict):
        return schema

    clean = schema.copy()
    for key in ["$schema", "title", "additionalProperties", "definitions"]:
        clean.pop(key, None)

    if "properties" in clean:
        clean["properties"] = {k: sanitize_schema(v) for k, v in clean["properties"].items()}
    if "items" in clean:
        clean["items"] = sanitize_schema(clean["items"])

    return clean

def run_gemini(
    prompt: str,
    api_key: str,
    model_name: str,
    schema_path: Path,
) -> dict[str, Any]:

    with schema_path.open("r", encoding="utf-8") as f:
        raw_schema = json.load(f)

    clean_schema = sanitize_schema(raw_schema)
    client = genai.Client(api_key=api_key)

    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    config = types.GenerateContentConfig(
        tools=[google_search_tool],
        response_mime_type="application/json",
        response_schema=clean_schema,
        temperature=0.3
    )

    # --- RETRY LOGIC ADDED HERE ---
    max_retries = 3
    base_wait = 30 # Seconds

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )

            if not response.text:
                raise ValueError("Gemini returned empty text (safety block?).")

            return json.loads(response.text)

        except errors.ClientError as e:
            # Check for Rate Limit (429)
            if e.code == 429:
                if attempt < max_retries - 1:
                    wait_time = base_wait * (attempt + 1)
                    print(f"[{timestamp()}] Rate limit hit (429). Waiting {wait_time}s before retry {attempt+2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"Gemini API rate limit exceeded after {max_retries} attempts.") from e
            else:
                # Other errors (400, 403, 500) raise immediately
                raise RuntimeError(f"Gemini API error: {e}") from e
        except Exception as e:
             raise RuntimeError(f"Gemini unexpected error: {e}")

def domain_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = parsed.netloc.lower().strip()
    return host[4:] if host.startswith("www.") else host

def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()

def trim_to_max_chars(text: str, max_chars: int) -> str:
    text = normalize_ws(text)
    if len(text) <= max_chars: return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:-")

def trim_slug(slug: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", normalize_ws(slug).lower()))[:120].strip("-")

def normalize_seo_fields(payload: dict) -> dict:
    if payload.get("status") != "publish": return payload
    seo = payload.setdefault("seo", {})
    seo["focus_keyphrase"] = normalize_ws(seo.get("focus_keyphrase", "")) or "nepal election candidate"
    payload["slug"] = trim_slug(payload.get("slug", "") or seo["focus_keyphrase"])
    return payload

def build_prompt(topic, titles, candidates, min_sources, min_confidence) -> str:
    t_list = "\n".join(f"- {t}" for t in titles[:300]) or "- (none)"
    c_list = "\n".join(f"- {c}" for c in candidates[:300]) or "- (none)"
    return (
        f"Role: Expert Political Researcher.\nTopic: {topic}\nTarget Date: 2026-03-05\n\n"
        "TASK: Research ONE real candidate for the 2026 Nepal Election. Create a profile JSON.\n"
        "RULES:\n"
        "1. MUST use Google Search tool to find facts.\n"
        f"2. Use at least {min_sources} unique sources.\n"
        "3. Do NOT reuse these existing candidates:\n"
        f"{c_list}\n"
        "4. Avoid these existing topics:\n"
        f"{t_list}\n"
        "5. Output valid JSON matching schema.\n"
        f"6. Confidence must be >= {min_confidence}."
    )

def validate_payload(payload, titles, candidates, min_sources) -> list[str]:
    errs = []
    if payload.get("status") == "skip":
        if not payload.get("reason"): errs.append("Skip reason missing")
        return errs

    cand_name = payload.get("candidate_profile", {}).get("candidate_name", "").lower()
    if any(cand_name in c.lower() for c in candidates):
        errs.append("Candidate already exists")

    srcs = payload.get("sources", [])
    if len({domain_from_url(s.get("url")) for s in srcs}) < min_sources:
        errs.append(f"Not enough unique sources (found {len(srcs)})")

    return errs

def insert_post(payload: dict, status: str) -> dict:
    payload["post_status"] = status
    stdout = run_command(["php", str(PHP_INSERT_POST)], stdin_text=json.dumps(payload))
    return json.loads(stdout)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY"))
    parser.add_argument("--post-status", default="publish")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="gemini-2.0-flash")
    parser.add_argument("--min-sources", type=int, default=8)

    args = parser.parse_args()
    log_file = Path(DEFAULT_LOG_FILE)

    if not args.api_key:
        print("Error: --api-key required")
        return 1

    write_log("Job started.", log_file)
    try:
        # 1. Get WordPress Data
        titles = json.loads(run_command(["php", str(PHP_LIST_TITLES)]))
        cands = json.loads(run_command(["php", str(PHP_LIST_CANDIDATES)]))

        # 2. Build Prompt
        prompt = build_prompt("Nepal election candidate", titles, cands, args.min_sources, 85)

        # 3. Run Gemini (With Retry)
        write_log(f"Querying {args.model}...", log_file)
        payload = run_gemini(prompt, args.api_key, args.model, SCHEMA_PATH)

        # 4. Normalize & Validate
        payload = normalize_seo_fields(payload)
        errs = validate_payload(payload, titles, cands, args.min_sources)

        if errs:
            write_log(f"Validation failed: {errs}", log_file)
            return 1

        if payload.get("status") == "skip":
            write_log(f"Skipped: {payload.get('reason')}", log_file)
            return 0

        # 5. Insert or Dry Run
        if args.dry_run:
            write_log("Dry run success. Payload valid.", log_file)
            debug_path = LOG_DIR / "debug_payload.json"
            with debug_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"Debug payload saved to {debug_path}")
        else:
            res = insert_post(payload, args.post_status)
            write_log(f"Published: {res}", log_file)

    except Exception as e:
        write_log(f"Error: {e}\n{traceback.format_exc()}", log_file)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())