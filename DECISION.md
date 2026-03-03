# Decision Log

All architectural and implementation decisions are recorded here with reasoning.

---

## [2026-03-02 00:01 UTC] — Initial Setup

### DEC-001: Use Playwright (headless browser) instead of requests/BeautifulSoup

**Context**: The target URL https://glint.trade/feed was fetched and analyzed. The response returned only raw HTML/CSS bootstrap code with no feed content visible — confirming the site is a JavaScript-rendered Single Page Application (SPA).

**Alternatives considered**:
- `requests` + `BeautifulSoup`: Only parses static HTML; would return empty content for JS-rendered SPAs.
- `Selenium`: Works but is heavier and slower; Playwright is the modern successor.
- Finding a hidden API endpoint: Possible but would require reverse-engineering XHR calls, which is brittle and may violate ToS. Can be revisited if Playwright proves too slow.

**Decision**: Use **Playwright** (Python async API) with a headless Chromium browser. It renders JavaScript fully and is well-supported in GitHub Actions environments.

---

### [2026-03-02 00:01 UTC] DEC-002: Use GitHub Actions with cron for scheduling

**Context**: User explicitly requested GitHub Actions for automation.

**Alternatives considered**:
- AWS Lambda + EventBridge: More robust but requires cloud account and setup overhead.
- Self-hosted cron job: Requires always-on server.
- GitHub Actions: Free for public repos, no additional infrastructure, integrates directly with repository storage.

**Decision**: Use **GitHub Actions** with a `schedule: cron` trigger set to `*/30 * * * *` (every 30 minutes). This is the minimum granularity GitHub Actions supports for cron schedules. GitHub may delay scheduled runs by up to 15 minutes under high load.

---

### [2026-03-02 00:01 UTC] DEC-003: Store data in the repository as JSON files

**Context**: Need persistent, queryable storage for scraped news items.

**Alternatives considered**:
- External database (Supabase, PlanetScale): More scalable but requires external service, credentials, and more complex setup.
- GitHub Releases / Artifacts: Artifacts expire after 90 days; Releases are not designed for this use case.
- SQLite committed to repo: Works but binary diffs are messy; JSON is more readable and diffable.
- Store in-repo JSON files: Simple, version-controlled, human-readable, no external dependencies.

**Decision**: Store scraped data as **JSON files in `data/feeds/`** organized by date (`YYYY-MM-DD/`). Maintain a rolling `data/index.json` with all seen article URLs to enable deduplication across runs. This approach is self-contained and requires no external services for Phase 1.

---

### [2026-03-02 00:01 UTC] DEC-004: Deduplicate by article URL

**Context**: The scraper will run every 30 minutes and will frequently see previously-scraped articles.

**Decision**: Maintain a set of seen URLs in `data/index.json`. On each run, only write articles whose URLs are not already in the index. This prevents duplicate entries without needing a database.

---

### [2026-03-02 00:01 UTC] DEC-005: Use async Playwright with asyncio

**Context**: Playwright's Python library supports both sync and async APIs.

**Decision**: Use the **async API** (`async_playwright`) since it is the recommended pattern for modern Python and is more efficient if we later extend to scraping multiple pages or sources concurrently.

---

### [2026-03-02 00:03 UTC] DEC-006: Exclude screenshots from git, upload as Actions artifacts

**Context**: Playwright screenshots are useful for debugging but would bloat the repository over time (one PNG per 30-minute run ≈ 48 images/day).

**Decision**: Add `data/screenshots/` to `.gitignore`. The GitHub Actions workflow uploads the screenshot folder as an artifact with 7-day retention. This gives visibility during debugging without polluting git history.

---

### [2026-03-02 00:03 UTC] DEC-007: Use `[skip ci]` in data-commit messages

**Decision**: Append `[skip ci]` to all automated data-commit messages to prevent the scrape workflow from re-triggering itself when it pushes new data, avoiding an infinite loop.

---
