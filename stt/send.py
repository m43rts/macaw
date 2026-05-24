import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import types

SAMPLE_RATE = 16000
MODEL_TRANSCRIBE = "gemini-2.5-pro"
MODEL_DECODE = "gemini-2.5-flash"
DICTIONARY_PATH = Path(__file__).parent / "dictionary.yaml"


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
        sys.exit(f"Dictionary not found at {DICTIONARY_PATH}. Run generate_translations.py first.")
    entries = yaml.safe_load(DICTIONARY_PATH.read_text())
    return [e["fr"] for e in entries]


def transcribe(client: genai.Client, wav_bytes: bytes) -> str:
    print(f"Sending {len(wav_bytes) / 1024:.1f} KB to {MODEL_TRANSCRIBE} for transcription...")
    response = client.models.generate_content(
        model=MODEL_TRANSCRIBE,
        contents=[
            "Transcribe the following audio verbatim. Output only the transcript, no preamble.",
            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
        ],
    )
    return (response.text or "").strip()


def decode(client: genai.Client, transcript: str, dictionary: list[str]) -> int:
    prompt = (
        f"""
        The following message is the result of a speech to text process. The original speech contained words
        from French, Dutch, and/or English. The transcript is not perfect and certainly contains mismatches
        of words or even lacking words. Your task is to pick a sentence from the list below that could match
        what the original speech wanted to transmit. Your output will be ONLY the number of the sentence that
        match, 0 otherwise.

        Sentence list:
        {"\n".join([f"{i + 1}. {dictionary[i]}" for i in range(len(dictionary))])}

        Speech transcript:
        {transcript}
        """
    )
    print(f"Decoding against {len(dictionary)} entries dictionary with {MODEL_DECODE}...")
    response = client.models.generate_content(model=MODEL_DECODE, contents=prompt)
    try:
        code = int((response.text or "").strip())
        assert 0 <= code <= len(dictionary)
    except Exception:
        raise RuntimeError(f"LLM did not return a valid index, got: {response.text!r}")
    return code


def main():
    load_dotenv()
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

    decoded = decode(client, transcript, dictionary)
    print("\n--- Decoded ---")
    print(decoded)


if __name__ == "__main__":
    main()
