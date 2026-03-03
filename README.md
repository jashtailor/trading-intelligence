# Glint Feed Scraper

Automated news-scraping pipeline that continuously collects articles from [glint.trade/feed](https://glint.trade/feed) and stores them as structured JSON — the foundation for a stock-recommendation intelligence system.

---

## Overview

| | |
|---|---|
| **Target** | https://glint.trade/feed |
| **Schedule** | Every 30 minutes (GitHub Actions) |
| **Storage** | JSON files committed to this repository |
| **Phase 1** | Scrape & store ✅ |
| **Phase 2** | World-view + stock recommendations 🔜 |

---

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── scrape.yml        # Scheduled GitHub Actions workflow
├── scraper/
│   ├── scrape.py             # Playwright scraper
│   └── requirements.txt      # Python dependencies
├── data/
│   ├── index.json            # Deduplication index + run metadata
│   └── feeds/
│       └── YYYY-MM-DD/
│           └── HH-MM-SS.json # Scraped items per run
├── RULES.md
├── LOGGING.md
├── DECISION.md
├── ERROR.md
└── CLAUDE.md
```

---

## How It Works

1. **GitHub Actions** triggers the scraper every 30 minutes via cron.
2. **`scraper/scrape.py`** launches a headless Chromium browser (Playwright) because glint.trade is a JavaScript-rendered SPA — static HTTP requests return no content.
3. The scraper uses three fallback strategies to extract articles:
   - **API interception** — captures XHR/fetch JSON responses from the site's backend
   - **DOM scraping** — queries `article`, card, and feed-item elements
   - **Link fallback** — extracts all meaningful anchor links
4. Items already seen (tracked in `data/index.json` by URL) are skipped.
5. New items are written to `data/feeds/YYYY-MM-DD/HH-MM-SS.json`.
6. The workflow commits new data back to the repo (`[skip ci]` to avoid loops).
7. Debug screenshots are uploaded as GitHub Actions artifacts (7-day retention, not committed).

---

## Setup

### 1. Fork / clone this repository

### 2. Enable GitHub Actions
Go to **Settings → Actions → General** and ensure Actions are enabled.

### 3. Grant write permissions (if not already set)
Go to **Settings → Actions → General → Workflow permissions** and select **"Read and write permissions"**.

No additional secrets are required for Phase 1.

### 4. Trigger manually (optional)
Navigate to **Actions → Scrape Glint Feed → Run workflow** to trigger an immediate run.

---

## Running Locally

```bash
# Install dependencies
pip install -r scraper/requirements.txt
playwright install chromium

# Run the scraper
python scraper/scrape.py
```

Output is written to `data/feeds/` and `data/index.json`.

---

## Data Format

Each scrape produces a JSON file:

```json
{
  "scraped_at": "2026-03-02T00:30:00.000000+00:00",
  "source_url": "https://glint.trade/feed",
  "item_count": 12,
  "items": [
    {
      "url": "https://...",
      "title": "Article headline",
      "body": "Summary text...",
      "published_at": "2026-03-02T00:15:00Z",
      "image": "https://...",
      "tags": ["macro", "equities"],
      "_scraped_at": "2026-03-02T00:30:00+00:00",
      "_source": "dom"
    }
  ]
}
```

---

## Logs

| File | Contents |
|------|----------|
| `LOGGING.md` | Every prompt and Claude response |
| `DECISION.md` | Architectural decisions with rationale |
| `ERROR.md` | All errors with root-cause analysis |

---

*Built with Claude Code — Phase 1 complete 2026-03-02*
