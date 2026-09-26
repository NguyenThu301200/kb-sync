"""Test OptiBot from the terminal via Gemini `generate_content`, grounded on the uploaded files."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google import genai

from src import state
from main import STATE_FILE

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


def main() -> int:
    load_dotenv()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    question = " ".join(sys.argv[1:]) or "How do I add a YouTube video?"
    print(f"\nQ: {question}\n")

    st = state.load(STATE_FILE)
    file_names = [a["file_name"] for a in st["articles"].values() if a.get("file_name")]
    if not file_names:
        print("No uploaded files — run `python main.py` first.")
        return 1

    files = []
    for name in file_names:
        try:
            files.append(client.files.get(name=name))
        except Exception:
            pass

    resp = client.models.generate_content(
        model="gemini-3.8-flash",
        config={"system_instruction": SYSTEM_PROMPT},
        contents=[*files, question],
    )
    print("A:", resp.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
