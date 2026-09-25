"""Generate data/manifests/corpus_v1_split.json conforming to M2 Section 2 requirements.

Includes:
- sample_id, recording_id, source_id, speaker_id
- label ('real' or 'synthetic')
- language ('en', 'hi', 'ta', 'hinglish')
- generator ('human', 'google_tts', 'elevenlabs_v3', 'edge_tts_neural')
- degradation ('clean', 'g711_8khz', 'amr_nb', 'whatsapp_opus')
- codec ('pcm_s16le', 'g711_mulaw', 'amr_nb', 'opus')
- sample_rate, duration (seconds)
- audio_path, split ('train', 'validation', 'test')
"""
from __future__ import annotations

import json
from pathlib import Path
import wave


CODEC_MAP = {
    "clean": "pcm_s16le",
    "g711_8khz": "g711_mulaw",
    "amr_nb": "amr_nb",
    "whatsapp_opus": "opus",
}


def build_corpus_v1_manifest(
    input_manifest: Path = Path("data/manifests/corpus.jsonl"),
    output_path: Path = Path("data/manifests/corpus_v1_split.json"),
) -> dict:
    with open(input_manifest, "r", encoding="utf-8") as f:
        raw_samples = [json.loads(line) for line in f if line.strip()]

    samples = []
    recordings_seen = set()
    split_recordings = {"train": set(), "validation": set(), "test": set()}

    for s in raw_samples:
        audio_path = Path(s["audio_path"])
        duration = 0.0
        if audio_path.exists():
            with wave.open(str(audio_path), "rb") as wf:
                duration = round(wf.getnframes() / max(1, wf.getframerate()), 3)

        # Base recording ID (common across all degradations of a single recording)
        degradation = s["degradation"]
        sample_id = s["sample_id"]
        if sample_id.endswith(f"-{degradation}"):
            recording_id = sample_id[:-len(f"-{degradation}")]
        else:
            recording_id = s.get("source_id", sample_id)

        split = s["split"]
        recordings_seen.add(recording_id)
        split_recordings[split].add(recording_id)

        sample_entry = {
            "sample_id": sample_id,
            "recording_id": recording_id,
            "source_id": s["source_id"],
            "speaker_id": s["speaker_id"],
            "label": "synthetic" if s.get("is_synthetic", False) else "real",
            "is_synthetic": s.get("is_synthetic", False),
            "language": s["language"],
            "generator": s["generator"],
            "degradation": degradation,
            "codec": CODEC_MAP.get(degradation, "unknown"),
            "sample_rate": s["sample_rate"],
            "duration": duration,
            "audio_path": s["audio_path"],
            "split": split,
        }
        samples.append(sample_entry)

    # Verify no recording leakage across splits
    train_recs = split_recordings["train"]
    val_recs = split_recordings["validation"]
    test_recs = split_recordings["test"]

    assert len(train_recs & val_recs) == 0, f"Recording leakage train/val: {train_recs & val_recs}"
    assert len(train_recs & test_recs) == 0, f"Recording leakage train/test: {train_recs & test_recs}"
    assert len(val_recs & test_recs) == 0, f"Recording leakage val/test: {val_recs & test_recs}"

    manifest_data = {
        "version": "corpus_v1",
        "description": "PandaMIND M2 Authentic Evaluation Corpus Split Manifest",
        "total_samples": len(samples),
        "total_recordings": len(recordings_seen),
        "held_out_generators": ["edge_tts_neural"],
        "splits": {
            "train": len([s for s in samples if s["split"] == "train"]),
            "validation": len([s for s in samples if s["split"] == "validation"]),
            "test": len([s for s in samples if s["split"] == "test"]),
        },
        "samples": samples,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Saved corpus_v1_split.json with {len(samples)} samples across {len(recordings_seen)} recordings.")
    return manifest_data


if __name__ == "__main__":
    build_corpus_v1_manifest()
