import os
import serial
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import lora_serial as lora
import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import types

MODEL_TTS = "gemini-2.5-flash-preview-tts"
VOICE_NAME = "Kore"
DICTIONARY_PATH = Path(__file__).parent / "dictionary.yaml"
LANGS = ("fr", "en", "nl")
TTS_SAMPLE_RATE = 24000


def usage():
    sys.exit(f"Usage: receive.py <lang> <index> (lang in {{{','.join(LANGS)}}})")


def parse_args(argv: list[str]) -> tuple[str, int | None]:
    if len(argv) > 3 or len(argv) < 2:
        usage()
    
    index = None
    try:
        if len(argv) == 3:
            index = int(argv[2])
    except ValueError:
        usage()
        
    lang = argv[1].lower()
    if lang not in LANGS:
        sys.exit(f"Unknown language {lang!r}. Expected one of: {', '.join(LANGS)}.")
        
    return lang, index


def load_entry(index: int, lang: str) -> str:
    if not DICTIONARY_PATH.exists():
        sys.exit(f"Dictionary not found at {DICTIONARY_PATH}. Run generate_translations.py first.")
    entries = yaml.safe_load(DICTIONARY_PATH.read_text())
    if not (1 <= index <= len(entries)):
        sys.exit(f"Index {index} out of range [1, {len(entries)}].")
    return entries[index - 1][lang]


def wrap_wav(pcm: bytes, sample_rate: int = TTS_SAMPLE_RATE) -> bytes:
    n_channels = 1
    sample_width = 2
    byte_rate = sample_rate * n_channels * sample_width
    block_align = n_channels * sample_width
    data_size = len(pcm)
    return (
        b"RIFF"
        + struct.pack("<I", 36 + data_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, n_channels, sample_rate, byte_rate, block_align, sample_width * 8)
        + b"data"
        + struct.pack("<I", data_size)
        + pcm
    )


def speak(client: genai.Client, text: str) -> None:
    response = client.models.generate_content(
        model=MODEL_TTS,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME),
                ),
            ),
        ),
    )
    pcm = response.candidates[0].content.parts[0].inline_data.data
    wav = wrap_wav(pcm)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav)
        path = tmp.name
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                check=True,
            )
        else:
            subprocess.run(["aplay", "-q", path], check=True)
    finally:
        os.unlink(path)


def main():
    # Parse arguments
    lang, index = parse_args(sys.argv)
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set.")
    serial_path = os.environ.get("SERIAL_PATH")
    if index is None and not serial_path:
        sys.exit("SERIAL_PATH is not set.")

    # Get sentence
    if index is None:
        received = None
        with serial.Serial(serial_path, 115200, timeout=1) as ser:
            looping = True
            while looping:
                try:
                    received = lora.read_lora(ser, timeout=30)
                    print(f"> {received}")
                    if received is not None:
                        looping = False
                except Exception as e:
                    print(e)
                except KeyboardInterrupt as e:
                    print("Exiting!")
                    sys.exit(0)
        
        code = int(received)
        sentence = load_entry(code, lang)
    else:
        sentence = load_entry(index, lang)
    
    # Speak
    try:
        client = genai.Client(api_key=api_key)
        speak(client, sentence)
    except Exception as e:
        print(f"[TTS failed: {e}]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
