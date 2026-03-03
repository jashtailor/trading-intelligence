# Error Log

All errors, failures, and unexpected behaviors are recorded here with root-cause analysis.

---

## Format

Each entry follows this structure:

```
## [ERR-NNN] YYYY-MM-DD — Short description
- **Timestamp**: ISO 8601
- **Component**: Which file/system produced the error
- **Error**: Exact error message or description
- **Root Cause**: Why it happened
- **Resolution**: How it was fixed or worked around
- **Status**: Resolved / Ongoing / Monitoring
```

---

## Active Errors

### [ERR-001] [2026-03-03 02:00 UTC] — .github/workflows/scrape.yml
- **Timestamp**: 2026-03-03 02:00 UTC
- **Component**: `.github/workflows/scrape.yml` — "Install Playwright Chromium + system deps" step
- **Error**: `E: Package 'libasound2' has no installation candidate` / `Failed to install browser dependencies` / exit code 100
- **Root Cause**: `ubuntu-latest` now resolves to Ubuntu 24.04 (Noble), which renamed the `libasound2` package to `libasound2t64`. Playwright 1.44's `install-deps` script still references the old package name, causing apt to fail.
- **Resolution**: Pinned workflow to `ubuntu-22.04` and upgraded Playwright to `1.50.0`. Run #2 succeeded.
- **Status**: Resolved

---

### [ERR-002] [2026-03-03 02:02 UTC] — scraper/scrape.py — Low data quality on first run
- **Timestamp**: 2026-03-03 02:02 UTC
- **Component**: `scraper/scrape.py` — API interception + DOM selector strategies
- **Error**: 3 items captured — 2 from API with no url/title/body fields; 1 from DOM with page URL (`https://glint.trade/feed`) instead of article URL and truncated body text.
- **Root Cause**: (1) API responses intercepted don't match expected data structures (no `url`/`title`/`body` keys). (2) DOM selector fell back to `window.location.href` for the article URL because glint.trade's anchor tags may not be on the article container element. (3) `seen_urls` is storing the page URL rather than per-article URLs, which will reduce deduplication effectiveness on future runs.
- **Resolution**: Monitoring. Will inspect DOM structure via screenshot artifact and refine selectors in next iteration if data quality remains poor.
- **Status**: Monitoring

---

## Resolved Errors

*See Active Errors above — ERR-001 resolved.*

---

*This file is updated automatically by the scraper on failures, and manually after human review.*
