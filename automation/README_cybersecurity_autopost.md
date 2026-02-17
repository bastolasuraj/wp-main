# WordPress Nepal Election Candidate Auto-Profile (Codex CLI)

This automation job does the following on each run:

1. Reads existing post titles from the WordPress database.
2. Reads already-profiled candidate names from post meta.
3. Calls `codex --search exec` with a strict JSON schema.
4. Creates a profile on one Nepal election candidate tied to the March 5, 2026 election.
5. Enforces non-repeat by candidate name and near-duplicate title checks.
6. Gathers broad source coverage (default 12 unique domains).
7. Validates SEO fields and auto-normalizes metadata lengths.
8. Adds image link metadata if available and stores candidate profile metadata.
9. Inserts a new WordPress post when validation passes.

## Election Scope

- The generation prompt targets Nepal's upcoming election date: `2026-03-05`.
- Each run should profile one different candidate.
- If a reliable image URL is found, it is included as a linked image block.
- If requirements are not met, the run is skipped safely.

## Important Accuracy Note

No fully automated system can guarantee "100% accuracy" for web content.
This workflow enforces strict checks (multi-source support + confidence floor + duplicate prevention), but you should still review output, especially for politically sensitive claims.

## Files Added / Updated

- `automation/cybersecurity_autopost.py`
- `automation/codex_cybersecurity_schema.json`
- `automation/wp_get_post_titles.php`
- `automation/wp_get_profile_candidates.php`
- `automation/wp_insert_post.php`
- `automation/run_cybersecurity_job.bat`
- `automation/run_cybersecurity_job.sh`

## Prerequisites

- Python 3.10+
- PHP CLI (able to run in this WordPress directory)
- Codex CLI installed and authenticated
  - Login once: `codex login`
  - Optional explicit binary path: set `CODEX_BIN`
  - Scheduler must run under the same OS user used for `codex login`
- WordPress site available at this directory root (`wp-load.php` exists)

## Manual Test (Recommended First)

Run a dry-run first (no post creation):

```powershell
python automation\cybersecurity_autopost.py --dry-run --min-sources 12 --min-confidence 85
```

Create as draft for initial safety:

```powershell
python automation\cybersecurity_autopost.py --post-status draft
```

## Windows Task Scheduler (Every 5 Minutes)

Create the task:

```powershell
schtasks /Create /TN "WP Cybersecurity AutoPost" /SC MINUTE /MO 5 /TR "C:\xampp\htdocs\wp_main\automation\run_cybersecurity_job.bat" /F
```

Run immediately:

```powershell
schtasks /Run /TN "WP Cybersecurity AutoPost"
```

Change to once per day at 9:00 AM:

```powershell
schtasks /Change /TN "WP Cybersecurity AutoPost" /ST 09:00 /RI 1440
```

## Linux Cron (For Final Hosting)

Make shell wrapper executable:

```bash
chmod +x /var/www/html/wp_main/automation/run_cybersecurity_job.sh
```

Edit crontab:

```bash
crontab -e
```

If using API key auth on Linux, define it in crontab first:

```cron
OPENAI_API_KEY=your_key_here
```

Every 5 minutes:

```cron
*/5 * * * * /var/www/html/wp_main/automation/run_cybersecurity_job.sh
```

Once per day at 09:00:

```cron
0 9 * * * /var/www/html/wp_main/automation/run_cybersecurity_job.sh
```

## Tunables

- `--min-sources` (default: `12`)
- `--min-confidence` (default: `85`)
- `--post-status` (`publish`, `draft`, `pending`, `future`)
- `--model` (default: `gpt-5.3-codex`)
- `--topic` (default: `Nepal election candidate profile`)
- `--codex-timeout-seconds` (default: `900`)

## Logs

- Runtime log: `automation/logs/cybersecurity_autopost.log`
- Last model payload snapshots: `automation/logs/last_payload_*.json`

Task Scheduler note:
- The wrapper scripts intentionally do not shell-redirect stdout/stderr into the same log file, because the Python job already writes to `cybersecurity_autopost.log`. Double-writing to the same file can cause Windows lock/permission errors.
