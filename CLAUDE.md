# CLAUDE.md — Persistent Context

This file is always loaded into Claude's context. Keep it concise and accurate.

---

## Project

**Name**: Glint Feed Scraper + Stock Intelligence System
**Goal**: Continuously scrape https://glint.trade/feed, store articles, then (Phase 2) feed them to a model to produce a world-view and stock recommendations.
**Owner**: Jash
**Started**: 2026-03-02

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Scrape glint.trade/feed on a schedule and store data | **Complete** |
| 2 | Feed stored data to Claude; generate world-view + stock picks | Pending |

---

## Architecture

```
glint.trade/feed  (JS-rendered SPA)
        │
        ▼
scraper/scrape.py   (Playwright headless Chromium)
        │
        ├─ Strategy 1: Intercept XHR/fetch JSON responses
        ├─ Strategy 2: DOM scraping (article/card selectors)
        └─ Strategy 3: Fallback link extraction
        │
        ▼
data/feeds/YYYY-MM-DD/HH-MM-SS.json   ← new items per run
data/index.json                        ← deduplication index
        │
        ▼
.github/workflows/scrape.yml   (cron: every 30 min)
→ commits data back to repo
```

---

## Key Files

| Path | Purpose |
|------|---------|
| `scraper/scrape.py` | Main scraper (Playwright async) |
| `scraper/requirements.txt` | Python deps (`playwright==1.44.0`) |
| `.github/workflows/scrape.yml` | Scheduled GitHub Actions workflow |
| `data/index.json` | Seen URL set + run metadata |
| `data/feeds/` | Scraped JSON output (by date) |
| `.gitignore` | Excludes `data/screenshots/` from git |

---

## Key Decisions

- **Playwright** used instead of requests/BS4 because glint.trade is a JS SPA (confirmed by fetching the URL — only HTML bootstrap returned, no content).
- **GitHub Actions cron** `*/30 * * * *` — minimum supported granularity.
- **JSON files in-repo** for storage — no external DB needed for Phase 1.
- **Deduplication by URL** — `data/index.json` tracks all seen URLs.
- **Screenshots excluded from git** — uploaded as GitHub Actions artifacts (7-day retention) for debugging only.

---

## Rules Summary

All details in `RULES.md`. Key points:
- Timestamps `[YYYY-MM-DD HH:MM UTC]` mandatory on every `.md` entry.
- `LOGGING.md`, `DECISION.md`, `ERROR.md`, `CLAUDE.md`, `README.md` must always exist.
- No hardcoded credentials — use GitHub Secrets.

---

## Running Locally

```bash
pip install -r scraper/requirements.txt
playwright install chromium
python scraper/scrape.py
```

---

*Last updated: [2026-03-02 00:03 UTC]*
