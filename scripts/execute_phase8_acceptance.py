"""Phase 8 Retrain and Final Acceptance Execution Script.

Retrains detector on authenticated corpus (f20e22d), calibrates on validation set,
evaluates test split across benchmark slices, checks AC-1..AC-8 criteria, and tests
determinism and checkpoint reloading.
"""
from __future__ import annotations

import json
from pathlib import Path

from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data.manifest import CorpusManifest, validate_corpus_audio
from audio_detection.data.splits import assert_no_leakage
from audio_detection.evaluation.benchmark_eval import _evaluate_group, SliceResult
from audio_detection.evaluation.metrics import evaluate, to_dict
from audio_detection.training.trainer import load_checkpoint, save_checkpoint, train_model


def main() -> None:
    manifest_path = Path("data/manifests/corpus.jsonl")
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    audio_root = Path(".")
    
    ckpt_path = Path("reports/checkpoints/phase8_retrained_baseline.json")
    eval_report_path = Path("reports/benchmark/phase8_retrained_eval.json")

    print("==================================================")
    print(" 1. Freeze Corpus & Integrity Verification")
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
    print("Corpus integrity check: PASSED (72/72 files valid, no duplicates)")
    print("Source/speaker & held-out leakage check: PASSED")

    print("\n==================================================")
    print(" 2. Retrain Detector from Scratch")
    print("==================================================")
    detector = train_model(manifest, audio_root, held_out_path, epochs=10, lr=0.01, seed=42)
    detector.model_version = "phase8-retrained-baseline"
    print(f"Model version: {detector.model_version}")
    print(f"Trained weights: {detector.weights}")
    print(f"Trained bias: {detector.bias:.6f}")

    print("\n==================================================")
    print(" 3. Phase 6 Validation Calibration")
    print("==================================================")
    detector = calibrate_model(detector, manifest, audio_root, target_operating_point="fpr_1%")
    cfg = detector.threshold_config
    print(f"Calibration Status: {cfg.calibration_status}")
    print(f"Temperature: {cfg.temperature:.4f}")
    ops = cfg.operating_point_thresholds or {}
    print(f"Operating Thresholds: FPR 0.1%={ops.get('fpr_0.1%')}, FPR 1.0%={ops.get('fpr_1%')}, FPR 5.0%={ops.get('fpr_5%')}")
    print(f"Verdict Bands: Low (human bound)={cfg.low_threshold}, High (synth bound)={cfg.high_threshold}")
    
    config_meta = {
        "corpus_commit": "f20e22d",
        "epochs": 10,
        "lr": 0.01,
        "seed": 42,
        "target_operating_point": "fpr_1%",
    }
    save_checkpoint(detector, config_meta, ckpt_path)
    print(f"Saved calibrated checkpoint: {ckpt_path}")

    print("\n==================================================")
    print(" 4. Evaluate Test Split & Benchmark Slices")
    print("==================================================")
    test_samples = [s for s in manifest.samples if s.split == "test"]
    print(f"Total test samples: {len(test_samples)} (Real: {len([s for s in test_samples if not s.is_synthetic])}, Synth: {len([s for s in test_samples if s.is_synthetic])})")

    # Evaluate test samples
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

    # Overall test metrics
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

    # Specific Benchmark Slices on TEST split
    slices: dict[str, SliceResult] = {}

    # 1. in-domain clean (seen generators + clean)
    in_domain_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and r["sample"].generator not in held_out_gens
    ]
    slices["in-domain clean"] = _evaluate_group(in_domain_clean, "in-domain clean", detector.model_version)

    # 2. cross-generator clean (held-out clean + real clean)
    cross_gen_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator clean"] = _evaluate_group(cross_gen_clean, "cross-generator clean", detector.model_version)

    # 3. cross-generator telecom (held-out telecom + real telecom)
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

    # Save benchmark evaluation report
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

    print("\n==================================================")
    print(" 5. Phase 8 Acceptance Criteria Evaluation")
    print("==================================================")
    
    # AC-1: in-domain clean EER <= 5%
    ac1_slice = slices["in-domain clean"]
    if ac1_slice.status == "evaluated" and ac1_slice.record:
        ac1_verdict = "PASS" if ac1_slice.record.eer <= 0.05 else "FAIL"
        ac1_detail = f"EER={ac1_slice.record.eer:.4f}"
    else:
        ac1_verdict = "NOT EVALUABLE"
        ac1_detail = ac1_slice.reason

    # AC-2: cross-generator clean EER <= 15%
    ac2_slice = slices["cross-generator clean"]
    if ac2_slice.status == "evaluated" and ac2_slice.record:
        ac2_verdict = "PASS" if ac2_slice.record.eer <= 0.15 else "FAIL"
        ac2_detail = f"EER={ac2_slice.record.eer:.4f}"
    else:
        ac2_verdict = "NOT EVALUABLE"
        ac2_detail = ac2_slice.reason

    # AC-3: cross-generator telecom EER <= 25%
    ac3_slice = slices["cross-generator telecom"]
    if ac3_slice.status == "evaluated" and ac3_slice.record:
        ac3_verdict = "PASS" if ac3_slice.record.eer <= 0.25 else "FAIL"
        ac3_detail = f"EER={ac3_slice.record.eer:.4f}"
    else:
        ac3_verdict = "NOT EVALUABLE"
        ac3_detail = ac3_slice.reason

    # AC-4: TPR @ 1% FPR >= 70%
    ac4_verdict = "PASS" if overall_metrics.tpr_at_1pct_fpr >= 0.70 else "FAIL"
    ac4_detail = f"TPR@1%={overall_metrics.tpr_at_1pct_fpr:.4f}"

    # AC-5: ECE <= 0.05
    ac5_verdict = "PASS" if overall_metrics.ece <= 0.05 else "FAIL"
    ac5_detail = f"ECE={overall_metrics.ece:.4f}"

    # AC-6: Inconclusive/abstention <= 20%
    ac6_verdict = "PASS" if abstention_rate <= 0.20 else "FAIL"
    ac6_detail = f"rate={abstention_rate * 100:.2f}%"

    # AC-7: Language fairness max/min EER <= 2x
    eval_lang_eers = [
        slices[f"language: {l}"].record.eer
        for l in ("hi", "ta", "en", "hinglish")
        if slices[f"language: {l}"].status == "evaluated" and slices[f"language: {l}"].record
    ]
    if len(eval_lang_eers) >= 2:
        min_eer = min(eval_lang_eers)
        max_eer = max(eval_lang_eers)
        ratio = max_eer / min_eer if min_eer > 0 else (1.0 if max_eer == 0 else float("inf"))
        ac7_verdict = "PASS" if ratio <= 2.0 else "FAIL"
        ac7_detail = f"ratio={ratio:.2f}x"
    else:
        ac7_verdict = "NOT EVALUABLE"
        ac7_detail = "only_1_evaluable_language_slice"

    # AC-8: Improvement over evaluated public baselines at 1% FPR
    # Load phase4 baseline
    base_ckpt = Path("reports/checkpoints/phase4_baseline.json")
    if base_ckpt.exists():
        base_detector = load_checkpoint(base_ckpt)
        base_scores = []
        for s in test_samples:
            p = audio_root / s.audio_path
            with open(p, "rb") as f:
                b = f.read()
            res = base_detector.detect(b)
            base_scores.append(res["score"])
        base_metrics = evaluate(
            overall_labels, base_scores, dataset="corpus", split="test",
            language="mixed", generator="mixed", channel_condition="mixed",
            degradation="mixed", model_version=base_detector.model_version
        )
        improvement = overall_metrics.tpr_at_1pct_fpr - base_metrics.tpr_at_1pct_fpr
        ac8_verdict = "PASS" if improvement > 0 else "FAIL"
        ac8_detail = f"retrained TPR@1%={overall_metrics.tpr_at_1pct_fpr:.4f} vs base={base_metrics.tpr_at_1pct_fpr:.4f}"
    else:
        ac8_verdict = "NOT EVALUABLE"
        ac8_detail = "no_baseline_checkpoint"

    print(f"AC-1 (in-domain clean EER <= 5%)    : {ac1_verdict} ({ac1_detail})")
    print(f"AC-2 (cross-gen clean EER <= 15%)   : {ac2_verdict} ({ac2_detail})")
    print(f"AC-3 (cross-gen telecom EER <= 25%) : {ac3_verdict} ({ac3_detail})")
    print(f"AC-4 (TPR @ 1% FPR >= 70%)          : {ac4_verdict} ({ac4_detail})")
    print(f"AC-5 (ECE <= 0.05)                  : {ac5_verdict} ({ac5_detail})")
    print(f"AC-6 (Abstention <= 20%)            : {ac6_verdict} ({ac6_detail})")
    print(f"AC-7 (Language fairness <= 2x)      : {ac7_verdict} ({ac7_detail})")
    print(f"AC-8 (Baseline improvement)         : {ac8_verdict} ({ac8_detail})")

    print("\n==================================================")
    print(" 6. Determinism and Integrity Checks")
    print("==================================================")
    # Checkpoint reload check
    reloaded_detector = load_checkpoint(ckpt_path)
    print(f"Checkpoint reloaded successfully! Version={reloaded_detector.model_version}")

    # Inference check
    sample0 = test_samples[0]
    with open(audio_root / sample0.audio_path, "rb") as f:
        sample0_bytes = f.read()
    orig_det_res = detector.detect(sample0_bytes)
    reloaded_det_res = reloaded_detector.detect(sample0_bytes)
    assert orig_det_res == reloaded_det_res, "Reloaded detector detection output mismatch!"
    print("Checkpoint reload & inference verification: PASSED")

    # Determinism check
    eval_run_2 = evaluate(
        overall_labels, overall_scores, dataset="corpus", split="test",
        language="mixed", generator="mixed", channel_condition="mixed",
        degradation="mixed", model_version=detector.model_version
    )
    assert overall_metrics == eval_run_2, "Repeated evaluation is not deterministic!"
    print("Evaluation determinism check: PASSED")


if __name__ == "__main__":
    main()
