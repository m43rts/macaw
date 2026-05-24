import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from google import genai
from google.genai import types

SAMPLE_RATE = 16000
MODEL = "gemini-2.5-flash"
DICTIONARY_PATH = Path(__file__).parent / "dictionary.txt"


def record_until_enter() -> bytes:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = [
        "arecord",
        "-q",
        "-f", "S16_LE",
        "-r", str(SAMPLE_RATE),
        "-c", "1",
        "-t", "wav",
        tmp.name,
    ]
    print("Recording... press Enter to stop.")
    proc = subprocess.Popen(cmd)
    try:
        input()
    finally:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)

    with open(tmp.name, "rb") as f:
        data = f.read()
    os.unlink(tmp.name)
    return data


def load_dictionary() -> list[str]:
    if not DICTIONARY_PATH.exists():
        sys.exit(f"Dictionary not found at {DICTIONARY_PATH}.")
    words = [line.strip() for line in DICTIONARY_PATH.read_text().splitlines()]
    return [w for w in words if w]


def transcribe(client: genai.Client, wav_bytes: bytes) -> str:
    print(f"Sending {len(wav_bytes) / 1024:.1f} KB to {MODEL} for transcription...")
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            "Transcribe the following audio verbatim. Output only the transcript, no preamble.",
            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
        ],
    )
    return (response.text or "").strip()


def translate(client: genai.Client, transcript: str, dictionary: list[str]) -> str:
    prompt = (
        "Rewrite the message below using ONLY words from the allowed dictionary. "
        "Drop any concept that cannot be expressed with these words. "
        "Do not invent, inflect, or substitute words outside the list. However the input can be composed of Dutch, French, or English versions of the words found in the provided English dictionnary."
        "Output only the rewritten message, no preamble, no explanation.\n\n"
        "Allowed dictionary (one word per line):\n"
        f"{chr(10).join(dictionary)}\n\n"
        "Message:\n"
        f"{transcript}"
    )
    print(f"Translating against {len(dictionary)}-word dictionary...")
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return (response.text or "").strip()


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set.")
    client = genai.Client(api_key=api_key)
    dictionary = load_dictionary()

    wav_bytes = record_until_enter()
    if len(wav_bytes) <= 44:
        sys.exit("No audio captured.")

    transcript = transcribe(client, wav_bytes)
    print("\n--- Transcript ---")
    print(transcript)

    translated = translate(client, transcript, dictionary)
    print("\n--- Translated ---")
    print(translated)


if __name__ == "__main__":
    main()
