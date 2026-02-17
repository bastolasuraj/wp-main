#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
AUTOMATION_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = AUTOMATION_DIR / "codex_cybersecurity_schema.json"
PHP_LIST_TITLES = AUTOMATION_DIR / "wp_get_post_titles.php"
PHP_LIST_CANDIDATES = AUTOMATION_DIR / "wp_get_profile_candidates.php"
PHP_INSERT_POST = AUTOMATION_DIR / "wp_insert_post.php"
LOCK_PATH = AUTOMATION_DIR / "cybersecurity_autopost.lock"
LOG_DIR = AUTOMATION_DIR / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "cybersecurity_autopost.log"

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "and",
    "are",
    "been",
    "before",
    "being",
    "between",
    "could",
    "during",
    "from",
    "have",
    "into",
    "more",
    "most",
    "over",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "through",
    "under",
    "using",
    "what",
    "when",
    "where",
    "which",
    "with",
    "your",
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
    except OSError as exc:
        fallback_name = f"cybersecurity_autopost_fallback_{dt.datetime.now().strftime('%Y%m%d')}.log"
        fallback_path = LOG_DIR / fallback_name
        try:
            with fallback_path.open("a", encoding="utf-8") as fallback:
                fallback.write(f"[{timestamp()}] primary_log_unavailable={exc}\n")
                fallback.write(line + "\n")
        except OSError:
            pass


def run_command(
    args: list[str],
    *,
    cwd: Path = ROOT_DIR,
    stdin_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | None = None,
) -> str:
    process = subprocess.Popen(
        args,
        cwd=str(cwd),
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        stdout, stderr = process.communicate(input=stdin_text, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                text=True,
            )
        raise RuntimeError(
            f"Command timed out after {timeout_seconds} seconds: {' '.join(args)}"
        ) from exc

    if stdout is None:
        stdout = ""
    if stderr is None:
        stderr = ""

    if process.returncode != 0:
        raise RuntimeError(
            "Command failed.\n"
            f"cmd: {' '.join(args)}\n"
            f"exit: {process.returncode}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return stdout.strip()


def normalize_title(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def title_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def get_existing_titles() -> list[str]:
    stdout = run_command(["php", str(PHP_LIST_TITLES)])
    payload = json.loads(stdout)
    if not isinstance(payload, list):
        raise RuntimeError("wp_get_post_titles.php returned unexpected data.")
    return [str(item).strip() for item in payload if str(item).strip()]


def get_existing_candidates() -> list[str]:
    stdout = run_command(["php", str(PHP_LIST_CANDIDATES)])
    payload = json.loads(stdout)
    if not isinstance(payload, list):
        raise RuntimeError("wp_get_profile_candidates.php returned unexpected data.")
    return [str(item).strip() for item in payload if str(item).strip()]


def normalize_candidate_name(name: str) -> str:
    return normalize_title(name)


def build_prompt(
    topic: str,
    existing_titles: list[str],
    existing_candidates: list[str],
    min_sources: int,
    min_confidence: int,
) -> str:
    today = dt.date.today().isoformat()
    capped_titles = existing_titles[:350]
    title_block = "\n".join(f"- {title}" for title in capped_titles) if capped_titles else "- (none)"
    capped_candidates = existing_candidates[:350]
    candidate_block = "\n".join(f"- {name}" for name in capped_candidates) if capped_candidates else "- (none)"

    return (
        "You are an expert political researcher and editor producing one WordPress-ready candidate profile.\n"
        f"Current date: {today}\n"
        f"Primary topic area: {topic}\n"
        "Target election date: 2026-03-05 (March 5, 2026)\n\n"
        "Hard rules:\n"
        "1) Pick one real candidate relevant to Nepal's upcoming election on 2026-03-05.\n"
        "2) The post must be a candidate profile, not generic election news.\n"
        "3) Do not repeat a candidate already covered in existing candidate profiles.\n"
        "4) Use live web research and gather information from at least "
        f"{min_sources} unique websites (distinct domains).\n"
        "5) Prioritize official party pages, candidate pages, election authority releases, "
        "major national/international reporting, and verified interviews.\n"
        "6) Every factual claim must be supported in key_facts with at least 2 supporting URLs.\n"
        "7) Do not invent names, affiliations, offices, dates, quotes, endorsements, or incidents.\n"
        "8) If you cannot satisfy all rules confidently, return status='skip' with a reason.\n"
        "   For skip responses, still include all required fields with safe empty values "
        "(empty strings/arrays).\n"
        "9) Avoid topics already covered by existing post titles (exact or near-duplicate topics).\n"
        "10) content_html must be valid HTML (no markdown fences), 1200-2200 words, "
        "with headings and concise paragraphs.\n"
        "11) Include profile sections: background, political career timeline, key policy positions, "
        "public controversies/criticisms (if reliably sourced), and electoral outlook.\n"
        "12) Include a 'Sources' heading-ready structure and a short FAQ section (>= 3 Q&A items).\n"
        "13) If a reliable candidate image URL is found, set candidate_profile.profile_image_url and "
        "candidate_profile.profile_image_source_url; otherwise leave those fields empty strings.\n"
        "14) SEO requirements: create seo.focus_keyphrase, seo.meta_title, and seo.meta_description. "
        "Include the focus keyphrase in title, slug, excerpt, first paragraph, and at least one H2.\n"
        "15) Keep claims conservative; when uncertain, omit the claim.\n"
        "16) Set key_facts[*].confidence >= "
        f"{min_confidence} for publishable output.\n\n"
        "Existing WordPress post titles:\n"
        f"{title_block}\n\n"
        "Existing candidate profiles already published/drafted:\n"
        f"{candidate_block}\n\n"
        "Return only JSON that matches the provided schema."
    )


def run_codex(
    prompt: str,
    output_path: Path,
    model: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")

    codex_bin = resolve_codex_binary()
    cmd = [codex_bin]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(
        [
            "--search",
            "exec",
            "--skip-git-repo-check",
            "--output-schema",
            str(SCHEMA_PATH),
            "-o",
            str(output_path),
            "-",
        ]
    )
    run_command(cmd, stdin_text=prompt, env=env, timeout_seconds=timeout_seconds)
    with output_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_codex_binary() -> str:
    explicit = os.environ.get("CODEX_BIN", "").strip()
    if explicit:
        return explicit

    for candidate in ("codex", "codex.cmd", "codex.exe"):
        found = shutil.which(candidate)
        if found:
            return found

    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        fallback = Path(appdata) / "npm" / "codex.cmd"
        if fallback.exists():
            return str(fallback)

    raise RuntimeError(
        "Unable to find Codex CLI. Set CODEX_BIN (for example, C:\\Users\\<you>\\AppData\\Roaming\\npm\\codex.cmd)."
    )


def domain_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = parsed.netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def trim_to_max_chars(text: str, max_chars: int) -> str:
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:-")


def trim_slug(slug: str, max_chars: int = 120) -> str:
    normalized = "-".join(re.findall(r"[a-z0-9]+", normalize_ws(slug).lower()))
    trimmed = trim_to_max_chars(normalized, max_chars).strip("-")
    if trimmed:
        return trimmed
    return "nepal-election-candidate-profile"


def expand_to_min_chars(text: str, min_chars: int, max_chars: int, fallback: str) -> str:
    text = normalize_ws(text)
    fallback = normalize_ws(fallback)
    if len(text) >= min_chars:
        return trim_to_max_chars(text, max_chars)

    if fallback and fallback.lower() not in text.lower():
        sep = " " if text else ""
        text = f"{text}{sep}{fallback}".strip()

    pad = " Stay updated with key risks, practical defenses, and actionable mitigation guidance."
    while len(text) < min_chars:
        remaining = min_chars - len(text)
        chunk = pad[:remaining]
        text = f"{text}{chunk}".strip()

    return trim_to_max_chars(text, max_chars)


def normalize_seo_fields(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "publish":
        return payload

    seo = payload.get("seo")
    if not isinstance(seo, dict):
        seo = {}
    payload["seo"] = seo

    title = normalize_ws(payload.get("title", ""))
    excerpt = normalize_ws(payload.get("excerpt", ""))

    focus_keyphrase = normalize_ws(seo.get("focus_keyphrase", ""))
    if not focus_keyphrase:
        words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2]
        focus_keyphrase = " ".join(words[:4]) or "nepal election candidate profile"
    seo["focus_keyphrase"] = focus_keyphrase

    meta_title = normalize_ws(seo.get("meta_title", "")) or title
    if focus_keyphrase.lower() not in meta_title.lower():
        meta_title = f"{focus_keyphrase.title()}: {meta_title}".strip()
    meta_title = expand_to_min_chars(meta_title, 45, 65, title)
    seo["meta_title"] = meta_title

    meta_description = normalize_ws(seo.get("meta_description", "")) or excerpt
    if focus_keyphrase.lower() not in meta_description.lower():
        meta_description = f"{focus_keyphrase}: {meta_description}".strip(": ")
    meta_description = expand_to_min_chars(meta_description, 130, 170, excerpt or title)
    seo["meta_description"] = meta_description

    seo_slug_hint = normalize_ws(seo.get("seo_slug_hint", ""))
    if not seo_slug_hint:
        seo_slug_hint = "-".join(re.findall(r"[a-z0-9]+", focus_keyphrase.lower()))
    seo["seo_slug_hint"] = trim_slug(seo_slug_hint, 120)

    slug = trim_slug(payload.get("slug", ""), 120)
    focus_slug = "-".join(re.findall(r"[a-z0-9]+", focus_keyphrase.lower()))
    if focus_slug and focus_slug not in slug:
        combined_slug = "-".join(part for part in (focus_slug, slug) if part)
        payload["slug"] = trim_slug(combined_slug, 120)
    else:
        payload["slug"] = slug

    # Keep schema hint aligned with the final canonical slug.
    seo["seo_slug_hint"] = payload["slug"]

    return payload


def near_duplicate_title(new_title: str, existing_titles: list[str]) -> bool:
    normalized_new = normalize_title(new_title)
    new_tokens = title_tokens(new_title)
    for existing in existing_titles:
        if normalized_new == normalize_title(existing):
            return True
        score = jaccard_similarity(new_tokens, title_tokens(existing))
        if score >= 0.72:
            return True
    return False


def validate_payload(
    payload: dict[str, Any],
    *,
    existing_titles: list[str],
    existing_candidates: list[str],
    min_sources: int,
    min_confidence: int,
) -> list[str]:
    errors: list[str] = []
    status = payload.get("status")
    if status not in {"publish", "skip"}:
        errors.append("status must be 'publish' or 'skip'.")
        return errors

    if status == "skip":
        reason = str(payload.get("reason", "")).strip()
        if not reason:
            errors.append("skip payload must include a reason.")
        return errors

    title = str(payload.get("title", "")).strip()
    if not title:
        errors.append("Missing title.")
    elif len(title) < 24:
        errors.append("Title is too short.")
    elif near_duplicate_title(title, existing_titles):
        errors.append("Generated title appears to duplicate an existing topic.")

    slug = str(payload.get("slug", "")).strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        errors.append("Slug must be kebab-case.")

    excerpt = str(payload.get("excerpt", "")).strip()
    if len(excerpt) < 110:
        errors.append("Excerpt is too short.")

    topic_keywords = payload.get("topic_keywords", [])
    if not isinstance(topic_keywords, list) or len(topic_keywords) < 3:
        errors.append("Need at least 3 topic_keywords.")

    content_html = str(payload.get("content_html", "")).strip()
    if len(content_html) < 1800:
        errors.append("content_html is too short for the required depth.")
    content_html_lower = content_html.lower()
    if "faq" not in content_html_lower:
        errors.append("content_html must include an FAQ section for SEO.")
    faq_question_count = len(re.findall(r"<h3[^>]*>.*?\?</h3>", content_html, flags=re.IGNORECASE | re.DOTALL))
    if faq_question_count < 3:
        errors.append("FAQ section should include at least 3 questions in H3 tags.")

    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        errors.append("sources must be a list.")
        return errors
    if len(sources) < min_sources:
        errors.append(f"Need at least {min_sources} sources; found {len(sources)}.")

    source_urls = {
        str(source.get("url", "")).strip()
        for source in sources
        if isinstance(source, dict) and str(source.get("url", "")).strip().startswith("http")
    }

    unique_domains = {
        (str(source.get("domain", "")).strip().lower() or domain_from_url(str(source.get("url", ""))))
        for source in sources
        if isinstance(source, dict)
    }
    unique_domains = {domain for domain in unique_domains if domain}
    if len(unique_domains) < min_sources:
        errors.append(
            f"Need at least {min_sources} unique source domains; found {len(unique_domains)}."
        )

    candidate_profile = payload.get("candidate_profile", {})
    if not isinstance(candidate_profile, dict):
        errors.append("candidate_profile must be an object.")
        candidate_profile = {}

    candidate_name = normalize_ws(candidate_profile.get("candidate_name", ""))
    election_name = normalize_ws(candidate_profile.get("election_name", ""))
    election_date = normalize_ws(candidate_profile.get("election_date", ""))
    party = normalize_ws(candidate_profile.get("party", ""))
    constituency = normalize_ws(candidate_profile.get("constituency", ""))
    current_position = normalize_ws(candidate_profile.get("current_position", ""))
    short_bio = normalize_ws(candidate_profile.get("short_bio", ""))
    profile_source_url = normalize_ws(candidate_profile.get("profile_source_url", ""))
    profile_image_url = normalize_ws(candidate_profile.get("profile_image_url", ""))
    profile_image_source_url = normalize_ws(candidate_profile.get("profile_image_source_url", ""))

    if len(candidate_name) < 4:
        errors.append("candidate_profile.candidate_name is too short.")
    if len(election_name) < 8:
        errors.append("candidate_profile.election_name is too short.")
    if "nepal" not in election_name.lower():
        errors.append("candidate_profile.election_name should reference Nepal.")
    if election_date != "2026-03-05":
        errors.append("candidate_profile.election_date must be 2026-03-05.")
    if len(party) < 2:
        errors.append("candidate_profile.party is too short.")
    if len(constituency) < 2:
        errors.append("candidate_profile.constituency is too short.")
    if len(current_position) < 2:
        errors.append("candidate_profile.current_position is too short.")
    if len(short_bio) < 60:
        errors.append("candidate_profile.short_bio is too short.")
    if not profile_source_url.startswith("http"):
        errors.append("candidate_profile.profile_source_url must be a valid URL.")

    if profile_source_url:
        normalized_source_urls = {url.rstrip("/") for url in source_urls}
        if profile_source_url.rstrip("/") not in normalized_source_urls and domain_from_url(profile_source_url) not in unique_domains:
            errors.append("candidate_profile.profile_source_url must be included in sources.")

    if profile_image_url and not profile_image_url.startswith("http"):
        errors.append("candidate_profile.profile_image_url must be a valid URL when provided.")
    if profile_image_source_url and not profile_image_source_url.startswith("http"):
        errors.append("candidate_profile.profile_image_source_url must be a valid URL when provided.")

    existing_candidate_set = {normalize_candidate_name(name) for name in existing_candidates}
    if candidate_name and normalize_candidate_name(candidate_name) in existing_candidate_set:
        errors.append("Candidate has already been profiled in earlier posts.")

    candidate_tokens = {token for token in title_tokens(candidate_name) if len(token) >= 3}
    if candidate_tokens:
        if len([token for token in candidate_tokens if token in title.lower()]) < 1:
            errors.append("Title should include candidate name.")
        if len([token for token in candidate_tokens if token in excerpt.lower()]) < 1:
            errors.append("Excerpt should include candidate name.")
        if len([token for token in candidate_tokens if token in content_html_lower]) < 2:
            errors.append("content_html should include candidate context clearly.")

    seo = payload.get("seo", {})
    if not isinstance(seo, dict):
        errors.append("seo must be an object.")
        seo = {}
    focus_keyphrase = str(seo.get("focus_keyphrase", "")).strip().lower()
    meta_title = str(seo.get("meta_title", "")).strip()
    meta_description = str(seo.get("meta_description", "")).strip()
    seo_slug_hint = str(seo.get("seo_slug_hint", "")).strip().lower()

    if len(focus_keyphrase) < 8:
        errors.append("seo.focus_keyphrase is too short.")
    if not (45 <= len(meta_title) <= 65):
        errors.append("seo.meta_title should be between 45 and 65 characters.")
    if not (130 <= len(meta_description) <= 170):
        errors.append("seo.meta_description should be between 130 and 170 characters.")

    focus_slug = "-".join(re.findall(r"[a-z0-9]+", focus_keyphrase))
    if focus_keyphrase:
        if focus_keyphrase not in title.lower():
            errors.append("Title should include seo.focus_keyphrase.")
        if focus_keyphrase not in excerpt.lower():
            errors.append("Excerpt should include seo.focus_keyphrase.")
        if focus_keyphrase not in content_html_lower:
            errors.append("content_html should include seo.focus_keyphrase.")
        if focus_keyphrase not in meta_title.lower():
            errors.append("seo.meta_title should include seo.focus_keyphrase.")
        if focus_keyphrase not in meta_description.lower():
            errors.append("seo.meta_description should include seo.focus_keyphrase.")
        if focus_slug and focus_slug not in slug:
            errors.append("Slug should include the focus keyphrase in kebab-case.")

    normalized_hint = "-".join(re.findall(r"[a-z0-9]+", seo_slug_hint))
    if normalized_hint and normalized_hint != slug:
        errors.append("seo.seo_slug_hint should align with the final slug.")

    key_facts = payload.get("key_facts", [])
    if not isinstance(key_facts, list) or not key_facts:
        errors.append("key_facts must be a non-empty list.")
    else:
        for index, fact in enumerate(key_facts, start=1):
            if not isinstance(fact, dict):
                errors.append(f"key_facts[{index}] is not an object.")
                continue
            urls = fact.get("supporting_source_urls", [])
            try:
                confidence = int(fact.get("confidence", -1))
            except (TypeError, ValueError):
                errors.append(f"key_facts[{index}] confidence is not numeric.")
                continue
            if not isinstance(urls, list) or len(urls) < 2:
                errors.append(f"key_facts[{index}] must have at least 2 supporting_source_urls.")
            if confidence < min_confidence:
                errors.append(
                    f"key_facts[{index}] confidence {confidence} is below minimum {min_confidence}."
                )
    return errors


def build_sources_section(sources: list[dict[str, Any]]) -> str:
    items: list[str] = []
    for source in sources:
        url = str(source.get("url", "")).strip()
        if not url.startswith("http"):
            continue
        domain = str(source.get("domain", "")).strip() or domain_from_url(url)
        publisher = str(source.get("publisher", "")).strip() or domain
        label = f"{publisher} ({domain})".strip()
        items.append(
            f'<li><a href="{html.escape(url, quote=True)}" rel="nofollow noopener" '
            f'target="_blank">{html.escape(label)}</a></li>'
        )
    if not items:
        return ""
    return "<h2>Sources</h2>\n<ol>\n" + "\n".join(items) + "\n</ol>"


def build_candidate_media_section(candidate_profile: dict[str, Any]) -> str:
    image_url = normalize_ws(candidate_profile.get("profile_image_url", ""))
    image_source_url = normalize_ws(candidate_profile.get("profile_image_source_url", ""))
    image_credit = normalize_ws(candidate_profile.get("profile_image_credit", ""))
    candidate_name = normalize_ws(candidate_profile.get("candidate_name", ""))

    if not image_url.startswith("http"):
        return ""

    caption_parts = [part for part in (candidate_name, image_credit) if part]
    caption_text = " - ".join(caption_parts) if caption_parts else "Candidate photo"
    if image_source_url.startswith("http"):
        caption_text = f'{caption_text} (source: <a href="{html.escape(image_source_url, quote=True)}" rel="nofollow noopener" target="_blank">link</a>)'

    return (
        "<figure>\n"
        f'  <img src="{html.escape(image_url, quote=True)}" alt="{html.escape(candidate_name or "Candidate", quote=True)}" loading="lazy">\n'
        f"  <figcaption>{caption_text}</figcaption>\n"
        "</figure>"
    )


def insert_post(payload: dict[str, Any], post_status: str) -> dict[str, Any]:
    content_html = str(payload["content_html"]).strip()
    candidate_profile = payload.get("candidate_profile", {})
    if not isinstance(candidate_profile, dict):
        candidate_profile = {}

    media_section = build_candidate_media_section(candidate_profile)
    if media_section and "<figure" not in content_html:
        content_html = f"{media_section}\n\n{content_html}"

    sources_section = build_sources_section(payload.get("sources", []))
    if sources_section and "<h2>Sources</h2>" not in content_html:
        content_html = f"{content_html}\n\n{sources_section}"

    post_payload = {
        "title": str(payload["title"]).strip(),
        "slug": str(payload["slug"]).strip(),
        "excerpt": str(payload["excerpt"]).strip(),
        "content_html": content_html,
        "post_status": post_status,
        "topic_keywords": payload.get("topic_keywords", []),
        "candidate_profile": candidate_profile,
        "seo": payload.get("seo", {}),
        "sources": payload.get("sources", []),
        "category_name": "Nepal Election 2026",
    }
    stdout = run_command(["php", str(PHP_INSERT_POST)], stdin_text=json.dumps(post_payload))
    return json.loads(stdout)


def save_debug_payload(payload: dict[str, Any]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = LOG_DIR / f"last_payload_{stamp}.json"
    with output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return output


def acquire_lock(stale_after_minutes: int) -> None:
    if LOCK_PATH.exists():
        age_seconds = dt.datetime.now().timestamp() - LOCK_PATH.stat().st_mtime
        if age_seconds > stale_after_minutes * 60:
            LOCK_PATH.unlink(missing_ok=True)
        else:
            raise LockHeldError(
                f"Lock file exists at {LOCK_PATH}. Another run may still be active."
            )
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as lock_handle:
        lock_handle.write(f"pid={os.getpid()} started={timestamp()}\n")


def release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and publish Nepal election candidate profiles via Codex CLI.")
    parser.add_argument("--topic", default="Nepal election candidate profile", help="Primary topic area.")
    parser.add_argument("--min-sources", type=int, default=12, help="Minimum distinct source domains.")
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=85,
        help="Minimum confidence required for each fact.",
    )
    parser.add_argument(
        "--post-status",
        default="publish",
        choices=["publish", "draft", "pending", "future"],
        help="WordPress post status for created posts.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CODEX_MODEL", "gpt-5.3-codex"),
        help="Codex model name.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run generation and checks, but do not post.")
    parser.add_argument(
        "--codex-timeout-seconds",
        type=int,
        default=900,
        help="Timeout for the Codex command.",
    )
    parser.add_argument(
        "--stale-lock-minutes",
        type=int,
        default=120,
        help="Consider lock stale after this many minutes.",
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Path for run logs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    log_file = Path(args.log_file)
    lock_acquired = False

    if not SCHEMA_PATH.exists():
        write_log(f"Schema not found: {SCHEMA_PATH}", log_file)
        return 1
    if not PHP_LIST_TITLES.exists() or not PHP_LIST_CANDIDATES.exists() or not PHP_INSERT_POST.exists():
        write_log("PHP helper scripts are missing.", log_file)
        return 1

    try:
        acquire_lock(args.stale_lock_minutes)
        lock_acquired = True
        write_log("Job started.", log_file)

        existing_titles = get_existing_titles()
        write_log(f"Loaded {len(existing_titles)} existing post title(s).", log_file)
        existing_candidates = get_existing_candidates()
        write_log(f"Loaded {len(existing_candidates)} existing candidate profile(s).", log_file)

        prompt = build_prompt(
            topic=args.topic,
            existing_titles=existing_titles,
            existing_candidates=existing_candidates,
            min_sources=args.min_sources,
            min_confidence=args.min_confidence,
        )
        write_log("Starting Codex research step.", log_file)

        with tempfile.TemporaryDirectory(prefix="cyber_autopost_") as temp_dir:
            output_path = Path(temp_dir) / "codex_response.json"
            payload = run_codex(
                prompt,
                output_path,
                args.model,
                timeout_seconds=args.codex_timeout_seconds,
            )
        write_log("Codex research step completed.", log_file)
        payload = normalize_seo_fields(payload)

        debug_file = save_debug_payload(payload)
        write_log(f"Saved AI payload to {debug_file}.", log_file)

        errors = validate_payload(
            payload,
            existing_titles=existing_titles,
            existing_candidates=existing_candidates,
            min_sources=args.min_sources,
            min_confidence=args.min_confidence,
        )
        if errors:
            write_log("Validation failed; skipping publish.", log_file)
            for err in errors:
                write_log(f" - {err}", log_file)
            return 2

        if payload.get("status") == "skip":
            write_log(f"Model returned skip: {payload.get('reason', 'no reason')}", log_file)
            return 0

        if args.dry_run:
            write_log("Dry-run enabled; not publishing post.", log_file)
            return 0

        result = insert_post(payload, post_status=args.post_status)
        write_log(f"Insert result: {json.dumps(result, ensure_ascii=False)}", log_file)
        return 0

    except LockHeldError as exc:
        write_log(f"Skipping run: {exc}", log_file)
        return 0
    except Exception as exc:
        write_log(f"Job failed: {exc}", log_file)
        for line in traceback.format_exc().splitlines():
            write_log(line, log_file)
        return 1
    finally:
        if lock_acquired:
            release_lock()
        write_log("Job finished.", log_file)


if __name__ == "__main__":
    sys.exit(main())
