#!/usr/bin/env python3
"""
scraper/scrape.py

Scrapes https://glint.trade/feed using a headless Playwright browser.
glint.trade is a JavaScript-rendered SPA, so requests/BeautifulSoup cannot
be used — Playwright renders the full page before extracting content.

Strategy:
  1. (Primary)   Intercept XHR/fetch API responses returning JSON from glint.trade
  2. (Fallback)  DOM scraping with generic article/card/feed-item selectors
  3. (Last-ditch) Extract all links with meaningful text

Deduplication: items already present in data/index.json are skipped.
Output:         data/feeds/YYYY-MM-DD/HH-MM-SS.json
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
FEEDS_DIR  = DATA_DIR / "feeds"
INDEX_FILE = DATA_DIR / "index.json"
ERROR_MD   = ROOT / "ERROR.md"

TARGET_URL = "https://glint.trade/feed"

# ---------------------------------------------------------------------------
# Index helpers  (deduplication + run metadata)
# ---------------------------------------------------------------------------

def load_index() -> dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"seen_urls": [], "total_items": 0, "last_run": None}


def save_index(index: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Error logging  → ERROR.md
# ---------------------------------------------------------------------------

_error_counter = 0

def log_error(component: str, error: str, root_cause: str, resolution: str) -> None:
    global _error_counter
    _error_counter += 1

    existing = ERROR_MD.read_text() if ERROR_MD.exists() else ""

    # Increment numeric suffix from file to avoid ID collisions across runs
    import re
    existing_ids = re.findall(r"ERR-(\d+)", existing)
    next_id = max((int(x) for x in existing_ids), default=0) + 1
    err_id = f"ERR-{next_id:03d}"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"""
## [{err_id}] {ts} — {component}
- **Timestamp**: {ts}
- **Component**: {component}
- **Error**: {error}
- **Root Cause**: {root_cause}
- **Resolution**: {resolution}
- **Status**: Ongoing

---
"""
    # Replace the "Active Errors" placeholder on first write
    if "*None yet.*" in existing:
        updated = existing.replace("*None yet.*", entry.strip(), 1)
    else:
        updated = existing + entry

    ERROR_MD.write_text(updated)
    print(f"[ERROR LOG] {err_id}: {error}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

async def scrape() -> list[dict]:
    """
    Navigate to glint.trade/feed, capture all content, return new items.
    """
    index = load_index()
    seen_urls: set[str] = set(index.get("seen_urls", []))

    captured_api: list[dict] = []   # JSON responses intercepted from network
    items: list[dict] = []          # All items found this run

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        # ------------------------------------------------------------------
        # Strategy 1 — Intercept API/JSON responses
        # ------------------------------------------------------------------
        async def on_response(response):
            ct = response.headers.get("content-type", "")
            if "application/json" not in ct:
                return
            # Only capture responses from the same origin
            if "glint.trade" not in response.url:
                return
            try:
                data = await response.json()
                captured_api.append({"url": response.url, "status": response.status, "data": data})
                print(f"[API] captured {response.url}  ({response.status})")
            except Exception:
                pass

        page.on("response", on_response)

        # ------------------------------------------------------------------
        # Load the page
        # ------------------------------------------------------------------
        print(f"[NAV] Loading {TARGET_URL} …")
        try:
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=90_000)
        except Exception as nav_err:
            # networkidle can time-out on highly dynamic pages — continue anyway
            print(f"[WARN] goto raised: {nav_err}  — continuing with partial load")

        # Give lazy-loaded content extra time to settle
        await asyncio.sleep(6)

        scrape_time = datetime.now(timezone.utc).isoformat()
        print(f"[INFO] Page title: {await page.title()}")

        # ------------------------------------------------------------------
        # Parse captured API data
        # ------------------------------------------------------------------
        ITEM_KEYS = ("items", "posts", "articles", "results", "data", "feed", "news", "entries")

        for resp in captured_api:
            payload = resp["data"]
            candidates: list[dict] = []

            if isinstance(payload, list):
                candidates = [x for x in payload if isinstance(x, dict)]
            elif isinstance(payload, dict):
                # Try known wrapper keys
                for key in ITEM_KEYS:
                    if key in payload and isinstance(payload[key], list):
                        candidates = [x for x in payload[key] if isinstance(x, dict)]
                        break
                if not candidates:
                    # Treat the whole object as a single item
                    candidates = [payload]

            for item in candidates:
                item["_scraped_at"] = scrape_time
                item["_source"] = "api"
                item["_source_api_url"] = resp["url"]
                items.append(item)

        print(f"[API] {len(items)} item(s) from intercepted API responses")

        # ------------------------------------------------------------------
        # Strategy 2 — DOM scraping
        # ------------------------------------------------------------------
        dom_items: list[dict] = await page.evaluate("""() => {
            const results = [];
            const seen = new Set();

            // Ordered from most-specific to most-generic
            const selectors = [
                'article',
                '[class*="feed-item"]', '[class*="feedItem"]',
                '[class*="news-item"]', '[class*="newsItem"]',
                '[class*="story"]',
                '[class*="post-card"]', '[class*="postCard"]',
                '[class*="article-card"]',
                '[class*="card"]',
                '[class*="item"]',
                'li'
            ];

            for (const sel of selectors) {
                const els = Array.from(document.querySelectorAll(sel));
                if (els.length < 2) continue;   // skip if too few — probably not the feed

                for (const el of els) {
                    const titleEl = el.querySelector(
                        'h1, h2, h3, h4, h5, [class*="title"], [class*="headline"]'
                    );
                    const bodyEl = el.querySelector(
                        'p, [class*="body"], [class*="content"], [class*="summary"], [class*="description"]'
                    );
                    const timeEl  = el.querySelector('time, [class*="time"], [class*="date"]');
                    const linkEl  = el.querySelector('a[href]');
                    const imgEl   = el.querySelector('img');
                    const tagEls  = Array.from(el.querySelectorAll('[class*="tag"], [class*="label"], [class*="badge"]'));

                    const url   = linkEl ? linkEl.href : window.location.href;
                    const title = titleEl ? titleEl.innerText.trim() : null;
                    const body  = bodyEl  ? bodyEl.innerText.trim()  : null;

                    if ((!title && !body) || seen.has(url)) continue;
                    seen.add(url);

                    results.push({
                        url,
                        title,
                        body,
                        published_at: timeEl
                            ? (timeEl.getAttribute('datetime') || timeEl.innerText.trim())
                            : null,
                        image:  imgEl  ? imgEl.src  : null,
                        tags:   tagEls.map(t => t.innerText.trim()).filter(Boolean),
                        raw_text: el.innerText.trim().slice(0, 800),
                        _selector: sel,
                        _source:   'dom'
                    });
                }
                if (results.length > 0) break;  // stop at first productive selector
            }

            // Last-ditch: meaningful links
            if (results.length === 0) {
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.innerText.trim();
                    if (text.length > 40 && a.href.startsWith('http') && !seen.has(a.href)) {
                        seen.add(a.href);
                        results.push({
                            url: a.href,
                            title: text.slice(0, 300),
                            body:  null,
                            published_at: null,
                            image: null,
                            tags:  [],
                            raw_text: text,
                            _selector: 'fallback-links',
                            _source:   'dom'
                        });
                    }
                });
            }

            return results;
        }""")

        print(f"[DOM] {len(dom_items)} item(s) from DOM scraping")

        # Merge DOM items (avoid URL duplicates already captured via API)
        api_urls = {
            item.get("url") or item.get("link") or item.get("id") or ""
            for item in items
        }
        for di in dom_items:
            di["_scraped_at"] = scrape_time
            if di.get("url") not in api_urls:
                items.append(di)

        # ------------------------------------------------------------------
        # Save a debug screenshot (not committed to git — see .gitignore)
        # ------------------------------------------------------------------
        try:
            ss_dir = DATA_DIR / "screenshots"
            ss_dir.mkdir(parents=True, exist_ok=True)
            ss_path = ss_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(ss_path), full_page=True)
            print(f"[SS]  screenshot saved → {ss_path.name}")
        except Exception as ss_err:
            print(f"[WARN] screenshot failed: {ss_err}")

        await browser.close()

    # ------------------------------------------------------------------
    # Deduplicate against the persistent index
    # ------------------------------------------------------------------
    new_items: list[dict] = []
    for item in items:
        url = item.get("url") or item.get("link") or item.get("id") or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        new_items.append(item)

    print(f"[DEDUP] {len(items)} total → {len(new_items)} new items after deduplication")

    # ------------------------------------------------------------------
    # Persist new items
    # ------------------------------------------------------------------
    if new_items:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ts    = datetime.now(timezone.utc).strftime("%H-%M-%S")
        day_dir = FEEDS_DIR / today
        day_dir.mkdir(parents=True, exist_ok=True)

        out_file = day_dir / f"{ts}.json"
        payload  = {
            "scraped_at":  scrape_time,
            "source_url":  TARGET_URL,
            "item_count":  len(new_items),
            "items":       new_items,
        }
        out_file.write_text(json.dumps(payload, indent=2, default=str))
        print(f"[SAVE] {len(new_items)} new items → {out_file.relative_to(ROOT)}")
    else:
        print("[SAVE] No new items — nothing written.")

    # ------------------------------------------------------------------
    # Update index
    # ------------------------------------------------------------------
    index["seen_urls"]           = sorted(seen_urls)
    index["total_items"]         = index.get("total_items", 0) + len(new_items)
    index["last_run"]            = datetime.now(timezone.utc).isoformat()
    index["last_run_new_items"]  = len(new_items)
    save_index(index)

    return new_items


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        new_items = asyncio.run(scrape())
        print(f"\n[DONE] Scrape complete. {len(new_items)} new item(s) saved.")
        sys.exit(0)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[FATAL] {exc}", file=sys.stderr)
        print(tb, file=sys.stderr)
        log_error(
            component="scraper/scrape.py",
            error=str(exc),
            root_cause=f"Unhandled top-level exception.\n```\n{tb}\n```",
            resolution=(
                "Check stack trace above. Common causes: \n"
                "  • Playwright not installed → run: playwright install chromium\n"
                "  • Network unreachable → check GitHub Actions runner\n"
                "  • Site structure changed → update DOM selectors"
            ),
        )
        sys.exit(1)
