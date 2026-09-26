"""Sync markdown files to the Gemini File API (the knowledge-base primitive for API-key users)."""
from __future__ import annotations

from pathlib import Path

from google import genai


def upload_file(client: genai.Client, md_path: Path) -> str:
    """Upload one file, return its Gemini resource name (e.g. `files/abc123`)."""
    f = client.files.upload(file=md_path, config={"mime_type": "text/markdown", "display_name": md_path.name})
    return f.name


def remove_file(client: genai.Client, file_name: str) -> None:
    """Delete a file (safe to call even if already expired)."""
    try:
        client.files.delete(name=file_name)
    except Exception:
        pass
