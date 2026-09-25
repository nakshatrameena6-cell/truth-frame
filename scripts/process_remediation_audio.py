"""Process authentic Indic human speech resources into standardized degraded WAVs.

Generates clean (16 kHz), G.711 mu-law (8 kHz), AMR-NB (8 kHz), and Opus (16 kHz)
audio files for authentic Wikimedia Commons recordings in Hindi, Tamil, and Hinglish.
"""
from __future__ import annotations

import math
from pathlib import Path
import wave

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf

from audio_detection.degradation.channels import g711_mulaw, ulaw2lin, ffmpeg_reencode


def _pcm16(samples: np.ndarray) -> bytes:
    return np.clip(np.rint(samples * 32767.0), -32768, 32767).astype("<i2").tobytes()


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def _resample(mono: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    if orig_rate == target_rate:
        return mono
    divisor = math.gcd(target_rate, orig_rate)
    return resample_poly(mono, target_rate // divisor, orig_rate // divisor)


def generate_degradations(mono: np.ndarray, rate: int, base_name: str, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean WAV (16 kHz)
    mono_16k = _resample(mono, rate, 16000)
    clean_path = output_dir / f"{base_name}_clean.wav"
    _write_wav(clean_path, _pcm16(mono_16k), 16000)

    # 2. G.711 8 kHz
    mono_8k = _resample(mono, rate, 8000)
    g711_pcm = ulaw2lin(g711_mulaw(_pcm16(mono_8k), 8000))
    g711_path = output_dir / f"{base_name}_g711_8khz.wav"
    _write_wav(g711_path, g711_pcm, 8000)

    # 3. AMR-NB 8 kHz
    amr_path = output_dir / f"{base_name}_amr_nb.wav"
    ffmpeg_reencode(str(clean_path), str(amr_path), "amr_nb")

    # 4. WhatsApp / Opus 16 kHz
    opus_path = output_dir / f"{base_name}_whatsapp_opus.wav"
    ffmpeg_reencode(str(clean_path), str(opus_path), "opus")

    return {
        "clean": clean_path,
        "g711_8khz": g711_path,
        "amr_nb": amr_path,
        "whatsapp_opus": opus_path,
    }


INDIC_SOURCES = [
    {
        "file": "hindi_kashmir.ogg",
        "base_name": "real_hindi_kashmir",
        "speaker_id": "spk_wikimedia_hi_kashmir",
        "source_id": "src_wikimedia_hi_kashmir_spoken_wikipedia",
        "language": "hi",
        "license": "CC-BY-SA-3.0",
        "provenance": "Wikimedia Commons - Hindi Spoken Wikipedia Kashmir Article",
    },
    {
        "file": "hindi_dengue.ogg",
        "base_name": "real_hindi_dengue",
        "speaker_id": "spk_wikimedia_hi_dengue",
        "source_id": "src_wikimedia_hi_dengue_guide",
        "language": "hi",
        "license": "CC-BY-SA-4.0",
        "provenance": "Wikimedia Commons - Hindi Dengue Public Health Spoken Guide",
    },
    {
        "file": "tamil_india.ogg",
        "base_name": "real_tamil_india",
        "speaker_id": "spk_wikimedia_ta_india",
        "source_id": "src_wikimedia_ta_india_spoken_wikipedia",
        "language": "ta",
        "license": "CC-BY-SA-3.0",
        "provenance": "Wikimedia Commons - Tamil Spoken Wikipedia India Article",
    },
    {
        "file": "tamil_anthem.ogg",
        "base_name": "real_tamil_anthem",
        "speaker_id": "spk_wikimedia_ta_anthem",
        "source_id": "src_wikimedia_ta_anthem_spoken_wikipedia",
        "language": "ta",
        "license": "CC-BY-SA-3.0",
        "provenance": "Wikimedia Commons - Tamil Spoken Wikipedia Anthem Article",
    },
    {
        "file": "hinglish_nehru.ogg",
        "base_name": "real_hinglish_nehru",
        "speaker_id": "spk_jawaharlal_nehru",
        "source_id": "src_wikimedia_nehru_tryst_with_destiny_1947",
        "language": "hinglish",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Jawaharlal Nehru Tryst with Destiny (1947)",
    },
    {
        "file": "hinglish_gandhi.ogg",
        "base_name": "real_hinglish_gandhi",
        "speaker_id": "spk_mahatma_gandhi",
        "source_id": "src_wikimedia_gandhi_speech_1931",
        "language": "hinglish",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Mahatma Gandhi Speech (1931)",
    },
]


def main() -> None:
    raw_dir = Path("data/raw/wikimedia_indic")
    processed_dir = Path("data/processed/authentic")
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("Processing authentic Indic recordings into standard degradation suite...")
    for src in INDIC_SOURCES:
        ogg_path = raw_dir / src["file"]
        if not ogg_path.exists():
            print(f"ERROR: {ogg_path} not found!")
            continue

        signal, rate = sf.read(str(ogg_path), dtype="float64", always_2d=True)
        mono = signal.mean(axis=1)

        # Standard 30-second window (clip or take clean active speech)
        max_samples = rate * 30
        if len(mono) > max_samples:
            mono = mono[:max_samples]

        print(f"Generating degradations for {src['base_name']} ({src['language']})...")
        deg_map = generate_degradations(mono, rate, src["base_name"], processed_dir)
        for deg, p in deg_map.items():
            print(f"  -> {deg}: {p} (size={p.stat().st_size} bytes)")

    print("\nAll Indic degradation suites generated successfully.")


if __name__ == "__main__":
    main()
