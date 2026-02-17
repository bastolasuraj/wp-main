# WordPress Nepal Election Candidate Auto-Profile (Gemini API)

This automation uses Google's Gemini API to research and publish candidate profiles for the 2026 Nepal Election.

## Key Features
- **Live Research:** Uses Gemini's built-in Google Search grounding to find real-time data.
- **Duplicate Protection:** Checks existing WordPress posts to ensure unique candidate selection.
- **SEO Optimized:** Auto-generates meta titles, descriptions, and slugs.
- **Strict Schema:** Enforces a JSON structure for reliability.

## Prerequisites
1.  **Python 3.10+**
2.  **Google Generative AI Library:**
    ```bash
    pip install google-generativeai
    ```
3.  **Gemini API Key:**
    - Get a key from [Google AI Studio](https://aistudio.google.com/).
    - Set it as an environment variable: `GEMINI_API_KEY`.

## Setup

1.  Place `gemini_autopost.py`, `codex_cybersecurity_schema.json`, and the PHP helper scripts in `wp-content/automation/` (or your preferred structure).
2.  Ensure `wp-load.php` is accessible in the parent directory.

## Usage

**Dry Run (Test without posting):**
```bash
python automation/gemini_autopost.py --dry-run --api-key "YOUR_KEY"