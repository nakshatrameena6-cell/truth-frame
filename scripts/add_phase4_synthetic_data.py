"""Download and add legitimate public-domain synthetic audio to PandaMIND corpus and train Phase 4 baseline."""
from __future__ import annotations

import audioop
import json
import math
from pathlib import Path
import urllib.request
import wave

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from audio_detection.data import CorpusManifest, Sample, assign_splits, assert_no_leakage, validate_corpus_audio
from audio_detection.degradation.channels import g711_mulaw
from audio_detection.training.trainer import train_model, save_checkpoint, load_checkpoint

WIKIMEDIA_WAV_URL = "https://upload.wikimedia.org/wikipedia/commons/0/0f/ElevenLabs_v3_Mark_Accents.wav"
SOURCE_ID = "elevenlabs-v3-mark-speech-001"
SPEAKER_ID = "elevenlabs_v3_mark"
GENERATOR_ID = "elevenlabs_v3"
LICENSE = "Public domain (PD-algorithm)"


def _pcm16(samples: np.ndarray) -> bytes:
    return np.clip(np.rint(samples * 32767), -32768, 32767).astype("<i2").tobytes()


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def main() -> None:
    raw_dir = Path("data/raw/wikimedia_commons_elevenlabs_v3")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_audio_path = raw_dir / "ElevenLabs_v3_Mark_Accents.wav"

    if not raw_audio_path.exists():
        print("Downloading legitimate public domain synthetic WAV from Wikimedia Commons...")
        req = urllib.request.Request(WIKIMEDIA_WAV_URL, headers={"User-Agent": "Mozilla/5.0"})
        audio_data = urllib.request.urlopen(req).read()
        raw_audio_path.write_bytes(audio_data)
        print(f"Downloaded {len(audio_data)} bytes to {raw_audio_path}")

    # Read and process audio
    signal, rate = sf.read(raw_audio_path, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)

    processed_dir = Path("data/processed/phase4")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean synthetic sample
    clean_wav_path = processed_dir / "elevenlabs_v3_mark_clean.wav"
    _write_wav(clean_wav_path, _pcm16(mono), rate)

    clean_sample = Sample(
        sample_id="en-elevenlabs-v3-mark-001-clean",
        source_id=SOURCE_ID,
        speaker_id=SPEAKER_ID,
        language="en",
        is_synthetic=True,
        generator=GENERATOR_ID,
        audio_path=clean_wav_path.as_posix(),
        degradation="clean",
        sample_rate=rate,
        channels=1,
        split="unassigned",
    )

    # 2. Telecom g711_8khz degraded synthetic sample
    divisor = math.gcd(8000, rate)
    resampled = resample_poly(mono, 8000 // divisor, rate // divisor)
    g711_pcm = audioop.ulaw2lin(g711_mulaw(_pcm16(resampled), 8000), 2)
    g711_wav_path = processed_dir / "elevenlabs_v3_mark_g711_8khz.wav"
    _write_wav(g711_wav_path, g711_pcm, 8000)

    g711_sample = Sample(
        sample_id="en-elevenlabs-v3-mark-001-g711-8khz",
        source_id=SOURCE_ID,
        speaker_id=SPEAKER_ID,
        language="en",
        is_synthetic=True,
        generator=GENERATOR_ID,
        audio_path=g711_wav_path.as_posix(),
        degradation="g711_8khz",
        sample_rate=8000,
        channels=1,
        split="unassigned",
    )

    # Load existing manifest
    manifest_path = Path("data/manifests/corpus.jsonl")
    existing_manifest = CorpusManifest.load_jsonl(manifest_path)
    base_samples = [s for s in existing_manifest.samples if not s.sample_id.startswith("en-elevenlabs")]
    print(f"Loaded base manifest with {len(base_samples)} samples.")

    # Combine samples
    all_samples = base_samples + [clean_sample, g711_sample]

    # Load held-out generators config
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    with open(held_out_path, "r", encoding="utf-8") as f:
        held_out_cfg = json.load(f)
    held_out_gens = set(held_out_cfg.get("generators", []))

    # Assign splits deterministically & verify no leakage
    updated_manifest = assign_splits(all_samples, held_out_gens)
    assert_no_leakage(updated_manifest, held_out_gens)

    # Write updated manifest
    updated_manifest.write_jsonl(manifest_path)
    print(f"Updated corpus manifest written to {manifest_path} ({len(updated_manifest.samples)} total samples).")

    # Validate corpus audio signals
    validation_result = validate_corpus_audio(updated_manifest, Path("."))
    print(f"Corpus Audio Validation: Checked={validation_result.checked}, Passed={validation_result.passed}, Failed={validation_result.failed}")
    if validation_result.failed > 0:
        raise RuntimeError(f"Corpus audio validation failed with issues: {validation_result.issues}")

    # Train Phase 4 model
    print("Training Phase 4 baseline model...")
    detector = train_model(updated_manifest, Path("."), held_out_path, epochs=20, lr=0.05, seed=42)
    print(f"Trained model version: {detector.model_version}, weights: {detector.weights}, bias: {detector.bias}")

    # Save checkpoint
    ckpt_path = Path("reports/checkpoints/phase4_baseline.json")
    save_checkpoint(detector, {"epochs": 20, "lr": 0.05, "seed": 42, "benchmark": "phase3-v1"}, ckpt_path)
    print(f"Saved model checkpoint to {ckpt_path}")

    # Verify loading and deterministic inference
    loaded_detector = load_checkpoint(ckpt_path)
    with open(clean_wav_path, "rb") as f:
        test_audio_bytes = f.read()

    res1 = detector.detect(test_audio_bytes)
    res2 = loaded_detector.detect(test_audio_bytes)
    assert res1 == res2, "Loaded checkpoint inference is not deterministic!"
    print("Deterministic inference verification successful!")
    print(f"Sample inference result: score={res1['score']:.4f}, confidence={res1['confidence']:.4f}")


if __name__ == "__main__":
    main()
