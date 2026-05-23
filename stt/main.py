import os
import signal
import subprocess
import sys
import tempfile

from google import genai
from google.genai import types

SAMPLE_RATE = 16000
MODEL = "gemini-2.5-flash"


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


def transcribe(wav_bytes: bytes) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    print(f"Sending {len(wav_bytes) / 1024:.1f} KB to {MODEL}...")
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            "Transcribe the following audio verbatim. Output only the transcript, no preamble.",
            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
        ],
    )
    return (response.text or "").strip()


def main():
    wav_bytes = record_until_enter()
    if len(wav_bytes) <= 44:
        sys.exit("No audio captured.")
    text = transcribe(wav_bytes)
    print("\n--- Transcript ---")
    print(text)


if __name__ == "__main__":
    main()
