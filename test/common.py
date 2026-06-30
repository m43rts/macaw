"""Helpers partagés : IO audio, mixage de bruit à SNR exact, normalisation texte."""
import re
import numpy as np
import soundfile as sf
import librosa

SAMPLE_RATE = 16000


def load_audio(path, sr=SAMPLE_RATE):
    """Charge n'importe quel fichier audio en mono float32 au sample rate cible."""
    audio, _ = librosa.load(path, sr=sr, mono=True)
    return audio.astype(np.float32)


def save_audio(path, audio, sr=SAMPLE_RATE):
    sf.write(path, audio, sr)


def white_noise(n):
    return np.random.randn(n).astype(np.float32)


def pink_noise(n):
    """Bruit rose (1/f) approximé par mise en forme FFT.
    Masque mieux la parole que le bruit blanc (plus proche d'un bruit ambiant)."""
    white = np.random.randn(n)
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1.0
    spectrum = spectrum / np.sqrt(freqs)
    pink = np.fft.irfft(spectrum, n=n)
    peak = np.max(np.abs(pink)) + 1e-12
    return (pink / peak).astype(np.float32)


def mix_at_snr(speech, noise, snr_db):
    """Mixe le bruit dans la parole à un SNR cible exact (dB). float32, anti-clipping."""
    if len(noise) < len(speech):
        reps = int(np.ceil(len(speech) / len(noise)))
        noise = np.tile(noise, reps)
    noise = noise[:len(speech)]
    s_pow = np.mean(speech ** 2) + 1e-12
    n_pow = np.mean(noise ** 2) + 1e-12
    target_n_pow = s_pow / (10 ** (snr_db / 10.0))
    noise = noise * np.sqrt(target_n_pow / n_pow)
    out = speech + noise
    peak = np.max(np.abs(out))
    if peak > 1.0:
        out = out / peak
    return out.astype(np.float32)


_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalize_text(s):
    """Majuscules, suppression ponctuation, espaces normalisés — pour comparer."""
    s = s.upper().strip()
    s = _PUNCT.sub(" ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()
