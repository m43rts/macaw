import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai

MODEL = "gemini-2.5-pro"
SRC_PATH = Path(__file__).parent / "dictionary.txt"
OUT_PATH = Path(__file__).parent / "dictionary.yaml"


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set.")

    sentences = [line.strip() for line in SRC_PATH.read_text().splitlines() if line.strip()]
    if not sentences:
        sys.exit(f"No sentences in {SRC_PATH}.")

    prompt = (
        "Translate each French sentence below into English and Dutch. "
        "These are short military / observation-report phrases — keep the same terse, neutral register.\n"
        "Return ONLY a JSON array, same length and order as the input, "
        'each item shaped {"en": "...", "nl": "..."}. No prose, no code fences.\n\n'
        "Input (JSON):\n"
        f"{json.dumps(sentences, ensure_ascii=False)}"
    )

    client = genai.Client(api_key=api_key)
    print(f"Translating {len(sentences)} sentences with {MODEL}...")
    response = client.models.generate_content(model=MODEL, contents=prompt)
    raw = (response.text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    translations = json.loads(raw)
    assert len(translations) == len(sentences), f"got {len(translations)} translations for {len(sentences)} inputs"
    for i, t in enumerate(translations):
        assert t.get("en"), f"missing 'en' at index {i}"
        assert t.get("nl"), f"missing 'nl' at index {i}"

    entries = [{"fr": fr, "en": t["en"], "nl": t["nl"]} for fr, t in zip(sentences, translations)]
    OUT_PATH.write_text(yaml.safe_dump(entries, allow_unicode=True, sort_keys=False))
    print(f"Wrote {len(entries)} entries to {OUT_PATH}")


if __name__ == "__main__":
    main()
