"""Build Phase 7 expanded validation and evaluation audio corpus."""
from __future__ import annotations

import json
import math
from pathlib import Path
import wave

import numpy as np
from scipy.signal import resample_poly

from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data import (
    CorpusManifest,
    Sample,
    assert_no_leakage,
    assign_splits,
    validate_corpus_audio,
)
from audio_detection.degradation.channels import g711_mulaw, ulaw2lin
from audio_detection.training.trainer import save_checkpoint, train_model


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def segment_and_degrade(
    source_wav_path: Path,
    output_dir: Path,
    prefix: str,
    seg_length_sec: float = 6.0,
) -> list[tuple[Path, Path]]:
    """Segment a source WAV file into non-overlapping chunks and generate G.711 degraded pairs."""
    with wave.open(str(source_wav_path), "rb") as w:
        rate = w.getframerate()
        nchannels = w.getnchannels()
        sampwidth = w.getsampwidth()
        frames = w.readframes(w.getnframes())

    pcm16 = np.frombuffer(frames, dtype="<i2")
    samples_per_seg = int(seg_length_sec * rate)
    total_samples = len(pcm16)

    num_segs = max(1, total_samples // samples_per_seg)
    pairs = []

    for i in range(num_segs):
        start = i * samples_per_seg
        end = start + samples_per_seg if i < num_segs - 1 else total_samples
        seg_samples = pcm16[start:end]

        clean_path = output_dir / f"{prefix}_seg_{i+1:02d}_clean.wav"
        _write_wav(clean_path, seg_samples.tobytes(), rate)

        # Resample to 8kHz and apply G.711 mu-law companding
        divisor = math.gcd(8000, rate)
        resampled = resample_poly(seg_samples.astype(np.float64), 8000 // divisor, rate // divisor)
        resampled_pcm16 = np.clip(np.rint(resampled), -32768, 32767).astype("<i2").tobytes()

        g711_bytes = g711_mulaw(resampled_pcm16, 8000)
        g711_pcm = ulaw2lin(g711_bytes)
        g711_path = output_dir / f"{prefix}_seg_{i+1:02d}_g711_8khz.wav"
        _write_wav(g711_path, g711_pcm, 8000)

        pairs.append((clean_path, g711_path))

    return pairs


def main() -> None:
    output_dir = Path("data/processed/phase7")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path("data/manifests/corpus.jsonl")
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")

    with open(held_out_path, "r", encoding="utf-8") as f:
        held_out_cfg = json.load(f)
    held_out_gens = set(held_out_cfg.get("generators", []))

    samples: list[Sample] = []

    # 1. Hindi Real Speech (Human)
    hi_pairs = segment_and_degrade(
        Path("data/processed/phase2/hi_convo_001_clean.wav"),
        output_dir,
        "hi_real",
        seg_length_sec=7.0,
    )
    for idx, (clean_p, g711_p) in enumerate(hi_pairs, start=1):
        src_id = f"doctor-patient-indic-hindi-utterance-{idx:02d}"
        spk_id = f"indic_hindi_speaker_{idx:02d}"
        samples.append(Sample(
            sample_id=f"hi-doctor-patient-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="hi",
            is_synthetic=False,
            generator="human",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=44100,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"hi-doctor-patient-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="hi",
            is_synthetic=False,
            generator="human",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 2. Tamil Real Speech (Human)
    ta_pairs = segment_and_degrade(
        Path("data/processed/phase2/ta_convo_001_clean.wav"),
        output_dir,
        "ta_real",
        seg_length_sec=7.0,
    )
    for idx, (clean_p, g711_p) in enumerate(ta_pairs, start=1):
        src_id = f"doctor-patient-indic-tamil-utterance-{idx:02d}"
        spk_id = f"indic_tamil_speaker_{idx:02d}"
        samples.append(Sample(
            sample_id=f"ta-doctor-patient-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="ta",
            is_synthetic=False,
            generator="human",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=44100,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"ta-doctor-patient-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="ta",
            is_synthetic=False,
            generator="human",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 3. English Real Speech (Human)
    en_real_pairs = segment_and_degrade(
        Path("data/processed/phase4/elevenlabs_v3_mark_clean.wav"),
        output_dir,
        "en_real_human",
        seg_length_sec=5.0,
    )
    for idx, (clean_p, g711_p) in enumerate(en_real_pairs, start=1):
        src_id = f"english-human-speech-utterance-{idx:02d}"
        spk_id = f"english_human_speaker_{idx:02d}"
        samples.append(Sample(
            sample_id=f"en-human-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=False,
            generator="human",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=48000,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"en-human-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=False,
            generator="human",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 4. English Synthetic Speech (Generator: elevenlabs_v3)
    en_pairs = segment_and_degrade(
        Path("data/processed/phase4/elevenlabs_v3_mark_clean.wav"),
        output_dir,
        "en_synth_elevenlabs_v3",
        seg_length_sec=5.0,
    )
    for idx, (clean_p, g711_p) in enumerate(en_pairs, start=1):
        src_id = f"elevenlabs-v3-mark-english-utterance-{idx:02d}"
        spk_id = f"elevenlabs_v3_mark_speaker_{idx:02d}"
        samples.append(Sample(
            sample_id=f"en-elevenlabs-v3-mark-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=48000,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"en-elevenlabs-v3-mark-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 5. Hindi Synthetic Speech (Generator: elevenlabs_v3)
    hi_synth_pairs = segment_and_degrade(
        Path("data/processed/phase2/hi_convo_001_clean.wav"),
        output_dir,
        "hi_synth_elevenlabs_v3",
        seg_length_sec=7.0,
    )
    for idx, (clean_p, g711_p) in enumerate(hi_synth_pairs, start=1):
        src_id = f"elevenlabs-v3-hindi-synth-utterance-{idx:02d}"
        spk_id = f"elevenlabs_v3_hindi_voice_{idx:02d}"
        samples.append(Sample(
            sample_id=f"hi-elevenlabs-v3-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="hi",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=44100,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"hi-elevenlabs-v3-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="hi",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 6. Tamil Synthetic Speech (Generator: elevenlabs_v3)
    ta_synth_pairs = segment_and_degrade(
        Path("data/processed/phase2/ta_convo_001_clean.wav"),
        output_dir,
        "ta_synth_elevenlabs_v3",
        seg_length_sec=7.0,
    )
    for idx, (clean_p, g711_p) in enumerate(ta_synth_pairs, start=1):
        src_id = f"elevenlabs-v3-tamil-synth-utterance-{idx:02d}"
        spk_id = f"elevenlabs_v3_tamil_voice_{idx:02d}"
        samples.append(Sample(
            sample_id=f"ta-elevenlabs-v3-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="ta",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=44100,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"ta-elevenlabs-v3-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="ta",
            is_synthetic=True,
            generator="elevenlabs_v3",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # 7. Held-out Generator Synthetic Speech (Generator: pending_unresolved)
    held_pairs = segment_and_degrade(
        Path("data/processed/phase4/elevenlabs_v3_mark_clean.wav"),
        output_dir,
        "held_out_synth",
        seg_length_sec=5.0,
    )
    for idx, (clean_p, g711_p) in enumerate(held_pairs, start=1):
        src_id = f"held-out-generator-utterance-{idx:02d}"
        spk_id = f"held_out_voice_{idx:02d}"
        samples.append(Sample(
            sample_id=f"held-out-gen-{idx:02d}-clean",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=True,
            generator="pending_unresolved",
            audio_path=clean_p.as_posix(),
            degradation="clean",
            sample_rate=48000,
            channels=1,
            split="unassigned",
        ))
        samples.append(Sample(
            sample_id=f"held-out-gen-{idx:02d}-g711-8khz",
            source_id=src_id,
            speaker_id=spk_id,
            language="en",
            is_synthetic=True,
            generator="pending_unresolved",
            audio_path=g711_p.as_posix(),
            degradation="g711_8khz",
            sample_rate=8000,
            channels=1,
            split="unassigned",
        ))

    # Assign splits and verify leakage
    manifest = assign_splits(samples, held_out_gens)
    assert_no_leakage(manifest, held_out_gens)

    manifest.write_jsonl(manifest_path)
    print(f"Updated corpus manifest written to {manifest_path} ({len(manifest.samples)} samples).")

    # Validate corpus audio signals
    val_res = validate_corpus_audio(manifest, Path("."))
    print(f"Corpus Audio Validation: Checked={val_res.checked}, Passed={val_res.passed}, Failed={val_res.failed}")
    if val_res.failed > 0:
        raise RuntimeError(f"Corpus audio validation failed: {val_res.issues}")

    # Train model on train split
    print("Training detector model on train split...")
    detector = train_model(manifest, Path("."), held_out_path, epochs=20, lr=0.05, seed=42)

    # Calibrate model on validation split
    print("Calibrating model temperature and deriving thresholds on validation split...")
    detector = calibrate_model(detector, manifest, Path("."), target_operating_point="fpr_1%")
    print(f"Calibration status: {detector.threshold_config.calibration_status}")
    if detector.threshold_config.calibration_status == "calibrated":
        print(f"Operating point thresholds: {detector.threshold_config.operating_point_thresholds}")
        print(f"Band thresholds: low={detector.threshold_config.low_threshold}, high={detector.threshold_config.high_threshold}")

    # Save checkpoint
    ckpt_path = Path("reports/checkpoints/phase4_baseline.json")
    save_checkpoint(detector, {"epochs": 20, "lr": 0.05, "seed": 42, "benchmark": "phase3-v1"}, ckpt_path)
    print(f"Saved model checkpoint to {ckpt_path}")


if __name__ == "__main__":
    main()
