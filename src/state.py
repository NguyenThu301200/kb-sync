"""JSON-file state for delta tracking."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def article_hash(article: dict) -> str:
    payload = f"{article.get('title','')}\n{article.get('body','')}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"vector_store_id": None, "articles": {}}


def save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True))
