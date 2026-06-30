"""Génère les clips audio PROPRES (sans bruit) pour chaque template via TTS.

Sortie :
  data/clean/{id:03d}.wav   (16 kHz mono)
  data/manifest.csv         (wav, template_id, texte)

Le bruit n'est PAS ajouté ici : il est mixé à la volée pendant l'éval, à SNR exact.

Notes :
- gTTS nécessite internet et fournit ~une voix par langue. Pour de la diversité
  locuteur, --variants applique des décalages de hauteur (pitch shift).
- Pour de VRAIS enregistrements : dépose tes wavs dans data/clean/ et écris le
  manifest correspondant (même format), puis saute ce script.
- Pour de vraies voix offline multi-locuteurs : remplace synth() par Piper.
"""
import argparse
import csv
import os
import tempfile

import numpy as np
import librosa
from gtts import gTTS

from common import load_audio, save_audio, SAMPLE_RATE
from templates import TEMPLATES


def synth(text, lang="fr", tld="fr"):
    """gTTS -> mp3 -> float32 16 kHz mono."""
    tts = gTTS(text=text, lang=lang, tld=tld)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    tts.save(tmp)
    audio = load_audio(tmp)
    os.remove(tmp)
    return audio


def pitch_variant(audio, n_steps, sr=SAMPLE_RATE):
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--tld", default="fr")
    ap.add_argument("--variants", type=int, default=2,
                    help="Nb de variantes pitch-shift par template (diversité locuteur).")
    args = ap.parse_args()

    clean_dir = os.path.join(args.data_dir, "clean")
    os.makedirs(clean_dir, exist_ok=True)
    manifest_path = os.path.join(args.data_dir, "manifest.csv")

    # pas de hauteur (en demi-tons) pour les variantes, autour de 0
    steps = [0.0]
    for k in range(args.variants):
        steps.append(-2.0 - 1.5 * k if k % 2 == 0 else 2.0 + 1.5 * k)

    rows = []
    wav_id = 0
    for tpl_id, text in enumerate(TEMPLATES):
        print(f"[{tpl_id+1}/{len(TEMPLATES)}] {text}")
        base = synth(text, lang=args.lang, tld=args.tld)
        for s in steps:
            audio = base if s == 0.0 else pitch_variant(base, s)
            fname = f"{wav_id:03d}.wav"
            save_audio(os.path.join(clean_dir, fname), audio)
            rows.append([fname, tpl_id, text])
            wav_id += 1

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["wav", "template_id", "text"])
        w.writerows(rows)

    print(f"\n{wav_id} clips écrits dans {clean_dir}")
    print(f"Manifest : {manifest_path}")


if __name__ == "__main__":
    main()
