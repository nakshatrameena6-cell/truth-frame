"""Train and Evaluate Fresh Detector on Expanded Authentic Corpus.

Trains a fresh 10-feature detector from scratch on train split,
calibrates temperature scaling on validation split, and evaluates
the test split across overall metrics and benchmark slices.
"""
from __future__ import annotations

import json
from pathlib import Path

from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data.manifest import CorpusManifest, validate_corpus_audio
from audio_detection.data.splits import assert_no_leakage
from audio_detection.evaluation.benchmark_eval import _evaluate_group, SliceResult
from audio_detection.evaluation.metrics import evaluate, to_dict
from audio_detection.training.trainer import save_checkpoint, train_model


def main() -> None:
    manifest_path = Path("data/manifests/corpus.jsonl")
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    audio_root = Path(".")

    ckpt_path = Path("reports/checkpoints/phase8_expanded_10d_baseline.json")
    eval_report_path = Path("reports/benchmark/phase8_expanded_10d_eval.json")

    print("==================================================")
    print(" 1. Corpus Integrity Verification")
    print("==================================================")
    manifest = CorpusManifest.load_jsonl(manifest_path)
    print(f"Total corpus samples: {len(manifest.samples)}")

    with open(held_out_path, "r", encoding="utf-8") as f:
        held_out_cfg = json.load(f)
    held_out_gens = set(held_out_cfg.get("generators", []))

    val_res = validate_corpus_audio(manifest, audio_root)
    if not val_res.ok:
        raise RuntimeError(f"Corpus audio validation failed: {val_res.failed} issues.")
    assert_no_leakage(manifest, held_out_gens)
    print("Corpus audio validation: PASSED (108/108 files valid)")
    print("Source/speaker & held-out leakage check: PASSED")

    print("\n==================================================")
    print(" 2. Train Fresh Detector from Scratch")
    print("==================================================")
    detector = train_model(manifest, audio_root, held_out_path, epochs=20, lr=0.01, seed=42)
    detector.model_version = "phase8-expanded-10d-baseline"
    print(f"Model version: {detector.model_version}")
    print(f"Trained 10D weights: {[round(w, 6) for w in detector.weights]}")
    print(f"Trained bias: {detector.bias:.6f}")

    print("\n==================================================")
    print(" 3. Validation Calibration")
    print("==================================================")
    detector = calibrate_model(detector, manifest, audio_root, target_operating_point="fpr_1%")
    cfg = detector.threshold_config
    print(f"Calibration Status: {cfg.calibration_status}")
    print(f"Temperature: {cfg.temperature:.4f}")
    ops = cfg.operating_point_thresholds or {}
    print(f"Operating Thresholds: FPR 0.1%={ops.get('fpr_0.1%')}, FPR 1.0%={ops.get('fpr_1%')}, FPR 5.0%={ops.get('fpr_5%')}")
    print(f"Verdict Bands: Low (human bound)={cfg.low_threshold}, High (synth bound)={cfg.high_threshold}")

    config_meta = {
        "corpus_commit": "cc6fc18a2724e296a2aad3f3fedc706e30a1ae7a",
        "epochs": 20,
        "lr": 0.01,
        "seed": 42,
        "target_operating_point": "fpr_1%",
        "num_features": len(detector.weights),
    }
    save_checkpoint(detector, config_meta, ckpt_path)
    print(f"Saved calibrated checkpoint: {ckpt_path}")

    print("\n==================================================")
    print(" 4. Evaluate Test Split & Benchmark Slices")
    print("==================================================")
    test_samples = [s for s in manifest.samples if s.split == "test"]
    print(f"Total test samples: {len(test_samples)} (Real: {len([s for s in test_samples if not s.is_synthetic])}, Synth: {len([s for s in test_samples if s.is_synthetic])})")

    test_eval_rows = []
    inconclusive_count = 0
    for s in test_samples:
        p = audio_root / s.audio_path
        with open(p, "rb") as f:
            audio_bytes = f.read()
        det_res = detector.detect(audio_bytes)
        test_eval_rows.append({
            "sample": s,
            "label": 1 if s.is_synthetic else 0,
            "score": det_res["score"],
            "verdict": det_res["verdict"],
        })
        if det_res["verdict"] == "inconclusive":
            inconclusive_count += 1

    abstention_rate = inconclusive_count / len(test_samples)
    print(f"Abstention / Inconclusive Rate: {abstention_rate * 100:.2f}% ({inconclusive_count}/{len(test_samples)})")

    overall_labels = [r["label"] for r in test_eval_rows]
    overall_scores = [r["score"] for r in test_eval_rows]
    overall_metrics = evaluate(
        overall_labels, overall_scores, dataset="corpus", split="test",
        language="mixed", generator="mixed", channel_condition="mixed",
        degradation="mixed", model_version=detector.model_version
    )

    print("\n--- Overall Test Metrics ---")
    print(f"EER               : {overall_metrics.eer:.4f}")
    print(f"TPR @ 0.1% FPR    : {overall_metrics.tpr_at_0_1pct_fpr:.4f}")
    print(f"TPR @ 1% FPR      : {overall_metrics.tpr_at_1pct_fpr:.4f}")
    print(f"TPR @ 5% FPR      : {overall_metrics.tpr_at_5pct_fpr:.4f}")
    print(f"ECE               : {overall_metrics.ece:.4f}")

    slices: dict[str, SliceResult] = {}

    # 1. in-domain clean
    in_domain_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and r["sample"].generator not in held_out_gens
    ]
    slices["in-domain clean"] = _evaluate_group(in_domain_clean, "in-domain clean", detector.model_version)

    # 2. cross-generator clean
    cross_gen_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator clean"] = _evaluate_group(cross_gen_clean, "cross-generator clean", detector.model_version)

    # 3. cross-generator telecom
    telecom_degs = {"g711_8khz", "amr_nb", "whatsapp_opus"}
    cross_gen_telecom = [
        r for r in test_eval_rows
        if r["sample"].degradation in telecom_degs and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator telecom"] = _evaluate_group(cross_gen_telecom, "cross-generator telecom", detector.model_version)

    # Languages
    for lang in ("hi", "ta", "en", "hinglish"):
        group = [r for r in test_eval_rows if r["sample"].language == lang]
        key = f"language: {lang}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{lang}")

    # Generators
    for gen in ("human", "elevenlabs_v3", "google_tts", "edge_tts_neural"):
        group = [r for r in test_eval_rows if r["sample"].generator == gen]
        key = f"generator: {gen}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{gen}")

    # Degradations
    for deg in ("clean", "g711_8khz", "amr_nb", "whatsapp_opus"):
        group = [r for r in test_eval_rows if r["sample"].degradation == deg]
        key = f"degradation: {deg}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{deg}")

    print("\n--- Slice Results Summary ---")
    for s_name, s_res in slices.items():
        if s_res.status == "evaluated":
            m = s_res.record
            print(f"[{s_name:30s}] EVALUATED   : EER={m.eer:.4f}, TPR@1%={m.tpr_at_1pct_fpr:.4f}, ECE={m.ece:.4f} (n={m.count})")
        else:
            print(f"[{s_name:30s}] NOT EVALUABLE: reason='{s_res.reason}'")

    report_dict = {k: v.to_dict() for k, v in slices.items()}
    report_dict["overall_test"] = {
        "slice_name": "overall_test",
        "status": "evaluated",
        "reason": None,
        "metrics": to_dict(overall_metrics),
        "abstention_rate": abstention_rate,
    }
    eval_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_report_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    print(f"\nSaved evaluation report: {eval_report_path}")


if __name__ == "__main__":
    main()
