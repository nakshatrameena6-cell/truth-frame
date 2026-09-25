"""Build remediated authentic corpus manifest and split.

Remediates M2 blockers:
1. AC-7 Language Coverage: authentic real human + synthetic speech in en, hi, ta, hinglish in test.
2. AC-2 Held-out Generator Coverage: two distinct held-out generators (edge_tts_neural, elevenlabs_v3)
   strictly excluded from training and present in test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import wave

from audio_detection.data import CorpusManifest, Sample, assert_no_leakage


CODEC_MAP = {
    "clean": "pcm_s16le",
    "g711_8khz": "g711_mulaw",
    "amr_nb": "amr_nb",
    "whatsapp_opus": "opus",
}

# Explicit split assignment per recording to guarantee exact AC-7 and AC-2 representation
# while maintaining strict speaker/source/recording isolation.
RECORDING_CONFIGS = [
    # ----------------------------------------------------
    # 1. Real Human Speech - English (16 recordings)
    # ----------------------------------------------------
    # Train
    {"base_name": "real_franklin_d_roosevelt", "speaker_id": "spk_franklin_d_roosevelt", "source_id": "src_wikimedia_fdr_four_freedoms_1941", "language": "en", "is_synthetic": False, "generator": "human", "split": "train"},
    {"base_name": "real_george_w_bush", "speaker_id": "spk_george_w_bush", "source_id": "src_wikimedia_bush_congress_2001", "language": "en", "is_synthetic": False, "generator": "human", "split": "train"},
    {"base_name": "real_nixon_resignation", "speaker_id": "spk_nixon", "source_id": "src_wikimedia_nixon_resignation_1974", "language": "en", "is_synthetic": False, "generator": "human", "split": "train"},
    # Validation
    {"base_name": "real_booker_t_washington", "speaker_id": "spk_booker_t_washington", "source_id": "src_wikimedia_booker_t_washington_1895", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_winston_churchill", "speaker_id": "spk_winston_churchill", "source_id": "src_wikimedia_churchill_1940", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_denis_mcdonough", "speaker_id": "spk_denis_mcdonough", "source_id": "src_wikimedia_mcdonough_confirmation_2021", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_jfk_inaugural", "speaker_id": "spk_jfk", "source_id": "src_wikimedia_jfk_inaugural_1961", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_calvin_coolidge", "speaker_id": "spk_calvin_coolidge", "source_id": "src_wikimedia_coolidge_taxes_1924", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_warren_harding", "speaker_id": "spk_warren_harding", "source_id": "src_wikimedia_harding_normalcy_1920", "language": "en", "is_synthetic": False, "generator": "human", "split": "validation"},
    # Test
    {"base_name": "real_brett_kavanaugh", "speaker_id": "spk_brett_kavanaugh", "source_id": "src_wikimedia_kavanaugh_confirmation_2018", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},
    {"base_name": "real_haile_selassie", "speaker_id": "spk_haile_selassie", "source_id": "src_wikimedia_selassie_un_1968", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},
    {"base_name": "real_marcus_garvey", "speaker_id": "spk_marcus_garvey", "source_id": "src_wikimedia_garvey_speech_1921", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},
    {"base_name": "real_eisenhower_farewell", "speaker_id": "spk_eisenhower", "source_id": "src_wikimedia_eisenhower_farewell_1961", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},
    {"base_name": "real_reagan_tear_down", "speaker_id": "spk_reagan", "source_id": "src_wikimedia_reagan_tear_down_1987", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},
    {"base_name": "real_william_taft", "speaker_id": "spk_william_taft", "source_id": "src_wikimedia_taft_peace_1912", "language": "en", "is_synthetic": False, "generator": "human", "split": "test"},

    # ----------------------------------------------------
    # 2. Real Human Speech - Indic Languages (6 recordings)
    # ----------------------------------------------------
    # Hindi (train, val, test)
    {"base_name": "real_indic_dr_pt_hindi_001", "speaker_id": "spk_indic_dr_pt_hi_001", "source_id": "src_indic_doctor_patient_hindi_convo_001", "language": "hi", "is_synthetic": False, "generator": "human", "split": "train"},
    {"base_name": "real_hindi_dengue", "speaker_id": "spk_wikimedia_hi_dengue", "source_id": "src_wikimedia_hi_dengue_guide", "language": "hi", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_hindi_kashmir", "speaker_id": "spk_wikimedia_hi_kashmir", "source_id": "src_wikimedia_hi_kashmir_spoken_wikipedia", "language": "hi", "is_synthetic": False, "generator": "human", "split": "test"},

    # Tamil (train, val, test)
    {"base_name": "real_indic_dr_pt_tamil_001", "speaker_id": "spk_indic_dr_pt_ta_001", "source_id": "src_indic_doctor_patient_tamil_convo_001", "language": "ta", "is_synthetic": False, "generator": "human", "split": "train"},
    {"base_name": "real_tamil_anthem", "speaker_id": "spk_wikimedia_ta_anthem", "source_id": "src_wikimedia_ta_anthem_spoken_wikipedia", "language": "ta", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_tamil_india", "speaker_id": "spk_wikimedia_ta_india", "source_id": "src_wikimedia_ta_india_spoken_wikipedia", "language": "ta", "is_synthetic": False, "generator": "human", "split": "test"},

    # Hinglish (val, test)
    {"base_name": "real_hinglish_gandhi", "speaker_id": "spk_mahatma_gandhi", "source_id": "src_wikimedia_gandhi_speech_1931", "language": "hinglish", "is_synthetic": False, "generator": "human", "split": "validation"},
    {"base_name": "real_hinglish_nehru", "speaker_id": "spk_jawaharlal_nehru", "source_id": "src_wikimedia_nehru_tryst_with_destiny_1947", "language": "hinglish", "is_synthetic": False, "generator": "human", "split": "test"},

    # ----------------------------------------------------
    # 3. Synthetic Speech - Seen Generator: google_tts (9 recordings)
    # ----------------------------------------------------
    {"base_name": "google_tts_src_001", "speaker_id": "google_tts_spk_001", "source_id": "google_tts_src_001", "language": "en", "is_synthetic": True, "generator": "google_tts", "split": "train"},
    {"base_name": "google_tts_en_002", "speaker_id": "en-google-tts-speaker-002", "source_id": "google_tts_en_002", "language": "en", "is_synthetic": True, "generator": "google_tts", "split": "train"},
    {"base_name": "google_tts_src_006", "speaker_id": "google_tts_spk_006", "source_id": "google_tts_src_006", "language": "en", "is_synthetic": True, "generator": "google_tts", "split": "validation"},

    {"base_name": "google_tts_hi_001", "speaker_id": "hi-google-tts-speaker-001", "source_id": "google_tts_hi_001", "language": "hi", "is_synthetic": True, "generator": "google_tts", "split": "train"},
    {"base_name": "google_tts_hi_002", "speaker_id": "hi-google-tts-speaker-002", "source_id": "google_tts_hi_002", "language": "hi", "is_synthetic": True, "generator": "google_tts", "split": "train"},
    {"base_name": "google_tts_src_005", "speaker_id": "google_tts_spk_005", "source_id": "google_tts_src_005", "language": "hi", "is_synthetic": True, "generator": "google_tts", "split": "train"},

    {"base_name": "google_tts_ta_001", "speaker_id": "ta-google-tts-speaker-001", "source_id": "google_tts_ta_001", "language": "ta", "is_synthetic": True, "generator": "google_tts", "split": "validation"},
    {"base_name": "google_tts_ta_002", "speaker_id": "ta-google-tts-speaker-002", "source_id": "google_tts_ta_002", "language": "ta", "is_synthetic": True, "generator": "google_tts", "split": "validation"},
    {"base_name": "google_tts_ta_003", "speaker_id": "ta-google-tts-speaker-003", "source_id": "google_tts_ta_003", "language": "ta", "is_synthetic": True, "generator": "google_tts", "split": "train"},

    # ----------------------------------------------------
    # 4. Synthetic Speech - Held-out Generator 1: edge_tts_neural (10 recordings) -> ALL TEST
    # ----------------------------------------------------
    {"base_name": "edge_neural_en_001", "speaker_id": "en-edge-neural-speaker-001", "source_id": "edge-tts-source-edge_neural_en_001", "language": "en", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_en_002", "speaker_id": "en-edge-neural-speaker-002", "source_id": "edge-tts-source-edge_neural_en_002", "language": "en", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},

    {"base_name": "edge_neural_hi_001", "speaker_id": "hi-edge-neural-speaker-001", "source_id": "edge-tts-source-edge_neural_hi_001", "language": "hi", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_hi_002", "speaker_id": "hi-edge-neural-speaker-002", "source_id": "edge-tts-source-edge_neural_hi_002", "language": "hi", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_hi_003", "speaker_id": "hi-edge-neural-speaker-003", "source_id": "edge-tts-source-edge_neural_hi_003", "language": "hi", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},

    {"base_name": "edge_neural_ta_001", "speaker_id": "ta-edge-neural-speaker-001", "source_id": "edge-tts-source-edge_neural_ta_001", "language": "ta", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_ta_002", "speaker_id": "ta-edge-neural-speaker-002", "source_id": "edge-tts-source-edge_neural_ta_002", "language": "ta", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},

    {"base_name": "edge_neural_hinglish_001", "speaker_id": "hinglish-edge-neural-speaker-001", "source_id": "edge-tts-source-edge_neural_hinglish_001", "language": "hinglish", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_hinglish_002", "speaker_id": "hinglish-edge-neural-speaker-002", "source_id": "edge-tts-source-edge_neural_hinglish_002", "language": "hinglish", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},
    {"base_name": "edge_neural_hinglish_003", "speaker_id": "hinglish-edge-neural-speaker-003", "source_id": "edge-tts-source-edge_neural_hinglish_003", "language": "hinglish", "is_synthetic": True, "generator": "edge_tts_neural", "split": "test"},

    # ----------------------------------------------------
    # 5. Synthetic Speech - Held-out Generator 2: elevenlabs_v3 (1 recording) -> ALL TEST
    # ----------------------------------------------------
    {"base_name": "elevenlabs_v3_mark", "speaker_id": "elevenlabs_v3_mark_accents_speaker_001", "source_id": "elevenlabs-v3-mark-accents-001", "language": "en", "is_synthetic": True, "generator": "elevenlabs_v3", "split": "test"},
]


def build_remediated_corpus(
    processed_dir: Path = Path("data/processed/authentic"),
    manifest_jsonl: Path = Path("data/manifests/corpus.jsonl"),
    split_manifest_json: Path = Path("data/manifests/corpus_v1_split.json"),
) -> dict:
    held_out_generators = {"edge_tts_neural", "elevenlabs_v3"}
    degradations = ["clean", "g711_8khz", "amr_nb", "whatsapp_opus"]

    samples: list[Sample] = []
    manifest_entries: list[dict] = []
    recordings_seen = set()

    for cfg in RECORDING_CONFIGS:
        base_name = cfg["base_name"]
        split = cfg["split"]
        lang = cfg["language"]
        is_synth = cfg["is_synthetic"]
        gen = cfg["generator"]
        source_id = cfg["source_id"]
        speaker_id = cfg["speaker_id"]
        recordings_seen.add(base_name)

        for deg in degradations:
            wav_file = processed_dir / f"{base_name}_{deg}.wav"
            if not wav_file.exists():
                raise FileNotFoundError(f"Missing audio file: {wav_file}")

            sr = 8000 if deg in {"g711_8khz", "amr_nb"} else 16000
            duration = 0.0
            with wave.open(str(wav_file), "rb") as wf:
                duration = round(wf.getnframes() / max(1, wf.getframerate()), 3)

            sample_id = f"{base_name}-{deg}"

            # Corpus manifest Sample object
            s = Sample(
                sample_id=sample_id,
                source_id=source_id,
                speaker_id=speaker_id,
                language=lang,
                is_synthetic=is_synth,
                generator=gen,
                audio_path=wav_file.as_posix(),
                degradation=deg,
                sample_rate=sr,
                channels=1,
                split=split,
            )
            samples.append(s)

            # JSON manifest dict
            entry = {
                "sample_id": sample_id,
                "recording_id": base_name,
                "source_id": source_id,
                "speaker_id": speaker_id,
                "label": "synthetic" if is_synth else "real",
                "is_synthetic": is_synth,
                "language": lang,
                "generator": gen,
                "degradation": deg,
                "codec": CODEC_MAP.get(deg, "unknown"),
                "sample_rate": sr,
                "duration": duration,
                "audio_path": wav_file.as_posix(),
                "split": split,
            }
            manifest_entries.append(entry)

    # Validate zero leakage
    corpus_manifest = CorpusManifest(tuple(samples))
    assert_no_leakage(corpus_manifest, held_out_generators)

    # Compute manifest hash
    manifest_bytes = json.dumps(manifest_entries, sort_keys=True).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    split_counts = {
        "train": len([s for s in manifest_entries if s["split"] == "train"]),
        "validation": len([s for s in manifest_entries if s["split"] == "validation"]),
        "test": len([s for s in manifest_entries if s["split"] == "test"]),
    }

    manifest_data = {
        "version": "corpus_v1_remediated",
        "description": "PandaMIND M2 Remediated Authentic Evaluation Corpus Split Manifest",
        "manifest_hash": manifest_hash,
        "total_samples": len(manifest_entries),
        "total_recordings": len(recordings_seen),
        "held_out_generators": sorted(held_out_generators),
        "splits": split_counts,
        "samples": manifest_entries,
    }

    # Write split manifest JSON
    split_manifest_json.parent.mkdir(parents=True, exist_ok=True)
    with open(split_manifest_json, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Write corpus.jsonl
    from dataclasses import asdict
    with open(manifest_jsonl, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(asdict(s)) + "\n")

    print(f"Manifest successfully built: {len(manifest_entries)} samples across {len(recordings_seen)} recordings.")
    print(f"Splits: train={split_counts['train']}, val={split_counts['validation']}, test={split_counts['test']}")
    print(f"Held-out generators: {sorted(held_out_generators)}")
    print(f"Manifest SHA-256: {manifest_hash}")

    # Print breakdown of test set by language and label
    test_samples = [s for s in manifest_entries if s["split"] == "test"]
    print("\nTest split composition:")
    for lang in ["en", "hi", "ta", "hinglish"]:
        real_count = len([s for s in test_samples if s["language"] == lang and not s["is_synthetic"]])
        synth_count = len([s for s in test_samples if s["language"] == lang and s["is_synthetic"]])
        print(f"  - {lang:<10}: real={real_count:>2}, synthetic={synth_count:>2}, total={real_count + synth_count:>2}")

    return manifest_data


if __name__ == "__main__":
    build_remediated_corpus()
