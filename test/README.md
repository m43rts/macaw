# PoC ASR tactique — voix bruitée → message borné → index compact

PoC minimal pour valider **la seule hypothèse risquée** : peut-on sortir de façon
fiable le bon message (vocabulaire borné) d'une voix bruitée ? Tout tourne sur un
laptop, **sans entraînement**.

Pipeline :

```
clip audio → faster-whisper (pré-entraîné) → texte libre
          → fuzzy-match au template le + proche → index (= payload)
```

Le fuzzy-match remplace le décodage par grammaire (compliqué) par un rapprochement
par distance d'édition vers le catalogue de messages valides. Même valeur testée,
zéro ingénierie de FST.

## 1. Installation

```bash
cd poc_asr
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`librosa`/`soundfile` lisent le mp3 de gTTS via libsndfile récent. Si la lecture mp3
échoue sur ta machine, installe `ffmpeg` (apt/brew).

## 2. Générer les données (TTS)

```bash
python generate_data.py --variants 2
```

Crée `data/clean/*.wav` (16 kHz) + `data/manifest.csv`. gTTS nécessite internet.

> ⚠️ L'audio TTS n'est **pas** de la vraie parole → les scores seront *optimistes*.
> Pour la validation finale, remplace par de vrais enregistrements (dépose tes wavs
> dans `data/clean/` + manifest au même format), ou passe à Piper pour du multi-voix
> offline.

## 3. Lancer l'évaluation

```bash
# CPU laptop (défaut)
python run_eval.py

# options utiles
python run_eval.py --model base --snrs clean,20,10,5,0,-5 --noise pink
python run_eval.py --device cuda --compute-type float16        # si GPU
python run_eval.py --noise-dir /chemin/vers/MUSAN/noise        # vrais bruits
```

Sorties dans `results/` :
- `accuracy_vs_snr.png` — courbe précision de classification / SNR
- `details.csv` — par clip : transcription, message matché, score, correct ou non

## 4. Lire les résultats

La métrique qui compte n'est **pas** le WER mais la **précision de classification** :
a-t-on choisi le bon template ? La courbe précision/SNR te dit à partir de quel niveau
de bruit le baseline pré-entraîné s'effondre.

Le `score` de match (colonne `details.csv`) est ton **seuil de confiance / readback** :
sous un seuil choisi, le système demanderait confirmation à l'opérateur au lieu de
transmettre.

## 5. Et après (seulement si nécessaire)

Si le baseline s'effondre à bas SNR :
- Fine-tune **Whisper-small + LoRA** (PEFT) sur ton audio augmenté → tient souvent
  **sous 8 GB de VRAM**.
- Full fine-tune (~10-16 GB) → passe sur GPU cloud : **RunPod / Lambda Labs**
  (instance 24 GB, image PyTorch préinstallée, ~0,4-0,8 $/h), ou AWS **EC2 g5.xlarge**
  (A10G 24 GB) avec l'**AWS Deep Learning AMI**.

## À ne PAS faire dans ce PoC

Streaming, deux passes, Conformer custom, FST de grammaire, quantification,
déploiement on-device. Tout ça vient *après* la validation de la robustesse au bruit.

## Fichiers

| Fichier | Rôle |
|---|---|
| `templates.py` | Catalogue de messages (à remplacer par le tien) |
| `common.py` | IO audio, mixage de bruit à SNR exact, normalisation texte |
| `generate_data.py` | Génère les clips propres via TTS (+ variantes pitch) |
| `run_eval.py` | Mixe bruit, transcrit, matche, trace précision/SNR |
