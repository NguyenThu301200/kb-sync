"""Scrape Zendesk Help Center → sync delta to the Gemini File API. Idempotent, daily-safe.

Gemini's File API has a 48-hour TTL, so the daily job also refreshes any file
older than ~40h even when its content hasn't changed. That keeps the assistant
grounded on a valid file handle every day.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from src import scraper, state, uploader

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "data" / "articles"
STATE_FILE = ROOT / "data" / "state.json"
REFRESH_AFTER_HOURS = 40

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kb-sync")


def _is_stale(uploaded_at: str | None) -> bool:
    if not uploaded_at:
        return True
    ts = datetime.fromisoformat(uploaded_at)
    return datetime.now(timezone.utc) - ts > timedelta(hours=REFRESH_AFTER_HOURS)


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    subdomain = os.getenv("ZENDESK_SUBDOMAIN", "support.optisigns.com")
    limit_env = os.getenv("ARTICLE_LIMIT")
    limit = int(limit_env) if limit_env else None

    if not api_key:
        log.error("Missing GEMINI_API_KEY")
        return 1

    client = genai.Client(api_key=api_key)
    st = state.load(STATE_FILE)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    added = updated = refreshed = skipped = 0

    for article in scraper.fetch_articles(subdomain, limit=limit):
        aid = str(article["id"])
        new_hash = state.article_hash(article)
        prev = st["articles"].get(aid)

        md = scraper.to_markdown(article)
        md_path = ARTICLES_DIR / scraper.filename_for(article)
        md_path.write_text(md, encoding="utf-8")

        content_changed = not prev or prev.get("hash") != new_hash
        file_stale = prev and _is_stale(prev.get("uploaded_at"))

        if not content_changed and not file_stale:
            skipped += 1
            continue

        if prev and prev.get("file_name"):
            uploader.remove_file(client, prev["file_name"])

        file_name = uploader.upload_file(client, md_path)
        st["articles"][aid] = {
            "hash": new_hash,
            "file_name": file_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "url": article["html_url"],
            "updated_at_source": article["updated_at"],
            "filename": md_path.name,
        }

        if not prev:
            added += 1
            log.info("ADDED     %s (%s) -> %s", aid, article["html_url"], file_name)
        elif content_changed:
            updated += 1
            log.info("UPDATED   %s (%s) -> %s", aid, article["html_url"], file_name)
        else:
            refreshed += 1
            log.info("REFRESHED %s (%s) -> %s", aid, article["html_url"], file_name)

    state.save(STATE_FILE, st)
    log.info("Done. added=%d updated=%d refreshed=%d skipped=%d total_tracked=%d",
             added, updated, refreshed, skipped, len(st["articles"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
