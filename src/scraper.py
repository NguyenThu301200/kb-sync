"""Fetch Help Center articles from a Zendesk subdomain."""
from __future__ import annotations

import re
from typing import Iterator

import requests
from markdownify import markdownify

UA = {"User-Agent": "kb-sync/1.0"}


def _slugify(title: str, article_id: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "article"
    return f"{article_id}-{s}"


def fetch_articles(subdomain: str, limit: int | None = None) -> Iterator[dict]:
    """Yield published articles from `https://<subdomain>/api/v2/help_center/en-us/articles.json`."""
    url = f"https://{subdomain}/api/v2/help_center/en-us/articles.json?per_page=100&sort_by=updated_at&sort_order=desc"
    yielded = 0
    while url:
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        data = r.json()
        for a in data.get("articles", []):
            if a.get("draft") or not a.get("body"):
                continue
            yield a
            yielded += 1
            if limit and yielded >= limit:
                return
        url = data.get("next_page")


def to_markdown(article: dict) -> str:
    """Render one Zendesk article as clean Markdown with front-matter."""
    title = article.get("title", "").strip()
    body_md = markdownify(article.get("body") or "", heading_style="ATX", strip=["script", "style"])
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    return (
        f"---\n"
        f"id: {article['id']}\n"
        f"title: {title!r}\n"
        f"url: {article['html_url']}\n"
        f"updated_at: {article['updated_at']}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"Article URL: {article['html_url']}\n\n"
        f"{body_md}\n"
    )


def filename_for(article: dict) -> str:
    return _slugify(article.get("title", ""), article["id"]) + ".md"
