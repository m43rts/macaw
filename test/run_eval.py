"""Évalue le PoC ASR.

Pour chaque SNR : mixe du bruit dans chaque clip propre, transcrit (faster-whisper),
matche la transcription au template le plus proche (rapidfuzz), et mesure la
PRECISION DE CLASSIFICATION (a-t-on choisi le bon message ?).

Sorties :
  results/accuracy_vs_snr.png   courbe précision / SNR
  results/details.csv           résultat par clip (transcription, match, score, ok)

Exemples :
  python run_eval.py
  python run_eval.py --model base --snrs clean,20,10,5,0,-5 --noise pink
  python run_eval.py --noise-dir /chemin/musan/noise   # vrais bruits
  python run_eval.py --device cuda --compute-type float16
"""
import argparse
import csv
import glob
import os
import random

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm
from rapidfuzz import process, fuzz
from faster_whisper import WhisperModel

from common import (load_audio, white_noise, pink_noise, mix_at_snr,
                    normalize_text)
from templates import TEMPLATES


def parse_snrs(s):
    out = []
    for tok in s.split(","):
        tok = tok.strip().lower()
        out.append(None if tok == "clean" else float(tok))
    return out


def load_manifest(data_dir):
    rows = []
    with open(os.path.join(data_dir, "manifest.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((os.path.join(data_dir, "clean", r["wav"]),
                         int(r["template_id"])))
    return rows


def make_noise(noise_type, noise_pool, n):
    if noise_pool:
        src = random.choice(noise_pool)
        if len(src) < n:
            src = np.tile(src, int(np.ceil(n / len(src))))
        start = random.randint(0, len(src) - n) if len(src) > n else 0
        return src[start:start + n]
    return pink_noise(n) if noise_type == "pink" else white_noise(n)


def transcribe(model, audio, lang):
    segments, _ = model.transcribe(audio, language=lang, beam_size=1)
    return " ".join(seg.text for seg in segments)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="cpu")            # "cuda" si GPU
    ap.add_argument("--compute-type", default="int8")     # "float16" sur GPU
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--snrs", default="clean,20,10,5,0,-5")
    ap.add_argument("--noise", default="pink", choices=["pink", "white"])
    ap.add_argument("--noise-dir", default=None,
                    help="Dossier de wavs de bruit réels (ex. MUSAN). Sinon synthétique.")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    os.makedirs(args.out_dir, exist_ok=True)

    norm_templates = [normalize_text(t) for t in TEMPLATES]
    clips = load_manifest(args.data_dir)
    snrs = parse_snrs(args.snrs)

    noise_pool = None
    if args.noise_dir:
        files = glob.glob(os.path.join(args.noise_dir, "**", "*.wav"), recursive=True)
        noise_pool = [load_audio(f) for f in files[:50]]  # cap pour la RAM
        print(f"{len(noise_pool)} fichiers de bruit chargés.")

    print(f"Chargement Whisper '{args.model}' ({args.device}/{args.compute_type})...")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    details = []
    accuracy = {}
    for snr in snrs:
        correct = 0
        label = "clean" if snr is None else f"{snr:g}dB"
        for wav_path, tpl_id in tqdm(clips, desc=f"SNR={label}"):
            speech = load_audio(wav_path)
            if snr is None:
                audio = speech
            else:
                noise = make_noise(args.noise, noise_pool, len(speech))
                audio = mix_at_snr(speech, noise, snr)

            hyp = transcribe(model, audio, args.lang)
            matched, score, pred_id = process.extractOne(
                normalize_text(hyp), norm_templates, scorer=fuzz.token_sort_ratio)
            ok = int(pred_id == tpl_id)
            correct += ok
            details.append([label, os.path.basename(wav_path), TEMPLATES[tpl_id],
                            hyp.strip(), TEMPLATES[pred_id], f"{score:.0f}", ok])

        acc = correct / len(clips)
        accuracy[label] = acc
        print(f"  -> précision {label}: {acc*100:.1f}%")

    # CSV détaillé
    with open(os.path.join(args.out_dir, "details.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["snr", "wav", "vrai_message", "transcription", "match", "score", "ok"])
        w.writerows(details)

    # Courbe précision / SNR
    numeric = [(s, accuracy[f"{s:g}dB"]) for s in snrs if s is not None]
    numeric.sort()
    if numeric:
        xs, ys = zip(*numeric)
        plt.figure(figsize=(7, 4.5))
        plt.plot(xs, [y * 100 for y in ys], "o-", label="bruité")
        if "clean" in accuracy:
            plt.axhline(accuracy["clean"] * 100, ls="--", color="gray",
                        label=f"clean ({accuracy['clean']*100:.0f}%)")
        plt.xlabel("SNR (dB)")
        plt.ylabel("Précision de classification (%)")
        plt.title(f"PoC ASR — Whisper {args.model} — bruit {args.noise}")
        plt.ylim(0, 101)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        out_png = os.path.join(args.out_dir, "accuracy_vs_snr.png")
        plt.savefig(out_png, dpi=130)
        print(f"\nCourbe : {out_png}")
    print(f"Détails : {os.path.join(args.out_dir, 'details.csv')}")


if __name__ == "__main__":
    main()
