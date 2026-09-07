"""Phase 2: Train, Calibrate, and Evaluate SSL Detector from Cached Features.

Reads 778D features from the cache produced by extract_ssl_features.py,
trains a LogisticRegression classifier on the train split, calibrates
temperature scaling on validation, and evaluates against the test split.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression

from audio_detection.calibration import TemperatureScaler, ThresholdConfig, assign_verdict_band, derive_calibration_thresholds
from audio_detection.data.manifest import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.evaluation.benchmark_eval import _evaluate_group, SliceResult
from audio_detection.evaluation.metrics import evaluate, to_dict
from audio_detection.training.trainer import save_checkpoint


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    manifest_path = Path("data/manifests/corpus.jsonl")
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    cache_path = Path("reports/checkpoints/ssl_feature_cache.json")
    ckpt_path = Path("reports/checkpoints/phase8_ssl_wav2vec2_baseline.json")
    eval_report_path = Path("reports/benchmark/phase8_ssl_wav2vec2_eval.json")

    # Load manifest
    manifest = CorpusManifest.load_jsonl(manifest_path)
    log(f"Total corpus samples: {len(manifest.samples)}")

    with open(held_out_path, "r", encoding="utf-8") as f:
        held_out_cfg = json.load(f)
    held_out_gens = set(held_out_cfg.get("generators", []))

    # Load cached features
    with open(cache_path, "r", encoding="utf-8") as f:
        feat_cache = json.load(f)
    log(f"Loaded cached features for {len(feat_cache)} samples")
    sample_dim = len(next(iter(feat_cache.values()))["features"])
    log(f"Feature dimension: {sample_dim}")

    # Organize by split
    train_samples = [s for s in manifest.samples if s.split == "train"]
    val_samples = [s for s in manifest.samples if s.split == "validation"]
    test_samples = [s for s in manifest.samples if s.split == "test"]

    X_tr = np.array([feat_cache[s.sample_id]["features"] for s in train_samples])
    y_tr = np.array([1 if s.is_synthetic else 0 for s in train_samples])
    X_val = np.array([feat_cache[s.sample_id]["features"] for s in val_samples])
    y_val = np.array([1 if s.is_synthetic else 0 for s in val_samples])
    X_te = np.array([feat_cache[s.sample_id]["features"] for s in test_samples])
    y_te = np.array([1 if s.is_synthetic else 0 for s in test_samples])

    log(f"Train: {X_tr.shape}, Val: {X_val.shape}, Test: {X_te.shape}")

    # ============================================================
    #  Train LogisticRegression
    # ============================================================
    log("\n==================================================")
    log(" 1. Train Logistic Regression Classifier")
    log("==================================================")
    clf = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    clf.fit(X_tr, y_tr)

    weights = tuple(clf.coef_[0])
    bias = float(clf.intercept_[0])

    detector = AudioDetector(
        model_version="phase8-ssl-wav2vec2-base",
        weights=weights,
        bias=bias,
    )

    log(f"Model version: {detector.model_version}")
    log(f"Feature dimension: {len(weights)}")
    log(f"Bias: {bias:.6f}")
    log(f"Train accuracy: {clf.score(X_tr, y_tr):.4f}")
    log(f"Val accuracy: {clf.score(X_val, y_val):.4f}")
    log(f"Test accuracy: {clf.score(X_te, y_te):.4f}")

    # ============================================================
    #  Calibrate on validation split
    # ============================================================
    log("\n==================================================")
    log(" 2. Temperature Calibration on Validation Split")
    log("==================================================")

    def compute_logits(X: np.ndarray) -> list[float]:
        return [float(bias + np.dot(weights, x)) for x in X]

    val_logits = compute_logits(X_val)
    val_labels = y_val.tolist()

    from audio_detection.calibration import PlattScaler
    
    scaler = PlattScaler()
    scaler.fit(val_logits, val_labels)
    detector.calibrator = scaler
    log(f"Fitted Platt Scaler: scale={scaler.scale:.4f}, shift={scaler.shift:.4f}")

    val_probs = scaler.transform(val_logits)
    threshold_config = derive_calibration_thresholds(
        val_probs, val_labels,
        target_operating_point="fpr_1%",
        scale=scaler.scale,
        shift=scaler.shift,
    )
    detector.threshold_config = threshold_config

    cfg = detector.threshold_config
    log(f"Calibration Status: {cfg.calibration_status}")
    ops = cfg.operating_point_thresholds or {}
    log(f"Operating Thresholds: FPR 0.1%={ops.get('fpr_0.1%')}, FPR 1.0%={ops.get('fpr_1%')}, FPR 5.0%={ops.get('fpr_5%')}")
    log(f"Verdict Bands: Low={cfg.low_threshold}, High={cfg.high_threshold}")

    # Save checkpoint
    config_meta = {
        "ssl_model_identifier": "facebook/wav2vec2-base",
        "feature_dimension": len(weights),
        "classifier": "LogisticRegression(C=1.0, penalty=l2)",
        "seed": 42,
        "scale": scaler.scale,
        "shift": scaler.shift,
        "thresholds": ops,
        "corpus_commit": "cc6fc18a2724e296a2aad3f3fedc706e30a1ae7a",
        "target_operating_point": "fpr_1%",
    }
    save_checkpoint(detector, config_meta, ckpt_path)
    log(f"Saved checkpoint: {ckpt_path}")

    # ============================================================
    #  Evaluate test split
    # ============================================================
    log("\n==================================================")
    log(" 3. Evaluate Test Split")
    log("==================================================")

    test_logits = compute_logits(X_te)
    test_probs = scaler.transform(test_logits)

    test_eval_rows = []
    inconclusive_count = 0
    raw_scores_real, raw_scores_synth = [], []
    cal_probs_real, cal_probs_synth = [], []

    for i, s in enumerate(test_samples):
        raw_logit = test_logits[i]
        cal_prob = test_probs[i]
        verdict = assign_verdict_band(cal_prob, threshold_config)
        is_synth = 1 if s.is_synthetic else 0

        if is_synth:
            raw_scores_synth.append(raw_logit)
            cal_probs_synth.append(cal_prob)
        else:
            raw_scores_real.append(raw_logit)
            cal_probs_real.append(cal_prob)

        test_eval_rows.append({
            "sample": s,
            "label": is_synth,
            "score": round(cal_prob, 6),
            "raw_score": round(raw_logit, 6),
            "verdict": verdict,
        })
        if verdict == "inconclusive":
            inconclusive_count += 1

    abstention_rate = inconclusive_count / len(test_samples)

    log("\n--- Raw Score Distribution ---")
    log(f"Real  (n={len(raw_scores_real)}): min={min(raw_scores_real):.4f}, mean={np.mean(raw_scores_real):.4f}, max={max(raw_scores_real):.4f}")
    log(f"Synth (n={len(raw_scores_synth)}): min={min(raw_scores_synth):.4f}, mean={np.mean(raw_scores_synth):.4f}, max={max(raw_scores_synth):.4f}")

    log("\n--- Calibrated Probability Distribution ---")
    log(f"Real  (n={len(cal_probs_real)}): min={min(cal_probs_real):.4f}, mean={np.mean(cal_probs_real):.4f}, max={max(cal_probs_real):.4f}")
    log(f"Synth (n={len(cal_probs_synth)}): min={min(cal_probs_synth):.4f}, mean={np.mean(cal_probs_synth):.4f}, max={max(cal_probs_synth):.4f}")

    overall_labels = [r["label"] for r in test_eval_rows]
    overall_scores = [r["score"] for r in test_eval_rows]
    overall_metrics = evaluate(
        overall_labels, overall_scores, dataset="corpus", split="test",
        language="mixed", generator="mixed", channel_condition="mixed",
        degradation="mixed", model_version=detector.model_version
    )

    log("\n--- Overall SSL Test Metrics ---")
    log(f"EER               : {overall_metrics.eer:.4f}")
    log(f"TPR @ 0.1% FPR    : {overall_metrics.tpr_at_0_1pct_fpr:.4f}")
    log(f"TPR @ 1% FPR      : {overall_metrics.tpr_at_1pct_fpr:.4f}")
    log(f"TPR @ 5% FPR      : {overall_metrics.tpr_at_5pct_fpr:.4f}")
    log(f"ECE               : {overall_metrics.ece:.4f}")
    log(f"Abstention Rate   : {abstention_rate * 100:.2f}% ({inconclusive_count}/{len(test_samples)})")

    # ============================================================
    #  Benchmark Slices
    # ============================================================
    log("\n==================================================")
    log(" 4. Benchmark Slices")
    log("==================================================")
    slices: dict[str, SliceResult] = {}

    in_domain_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and r["sample"].generator not in held_out_gens
    ]
    slices["in-domain clean"] = _evaluate_group(in_domain_clean, "in-domain clean", detector.model_version)

    cross_gen_clean = [
        r for r in test_eval_rows
        if r["sample"].degradation == "clean" and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator clean"] = _evaluate_group(cross_gen_clean, "cross-generator clean", detector.model_version)

    telecom_degs = {"g711_8khz", "amr_nb", "whatsapp_opus"}
    cross_gen_telecom = [
        r for r in test_eval_rows
        if r["sample"].degradation in telecom_degs and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator telecom"] = _evaluate_group(cross_gen_telecom, "cross-generator telecom", detector.model_version)

    for lang in ("hi", "ta", "en", "hinglish"):
        group = [r for r in test_eval_rows if r["sample"].language == lang]
        key = f"language: {lang}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{lang}")

    for gen in ("human", "elevenlabs_v3", "google_tts", "edge_tts_neural"):
        group = [r for r in test_eval_rows if r["sample"].generator == gen]
        key = f"generator: {gen}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{gen}")

    for deg in ("clean", "g711_8khz", "amr_nb", "whatsapp_opus"):
        group = [r for r in test_eval_rows if r["sample"].degradation == deg]
        key = f"degradation: {deg}"
        slices[key] = _evaluate_group(group, key, detector.model_version, empty_reason=f"no_data_{deg}")

    log("\n--- Slice Results Summary ---")
    for s_name, s_res in slices.items():
        if s_res.status == "evaluated":
            m = s_res.record
            log(f"[{s_name:30s}] EVALUATED   : EER={m.eer:.4f}, TPR@1%={m.tpr_at_1pct_fpr:.4f}, ECE={m.ece:.4f} (n={m.count})")
        else:
            log(f"[{s_name:30s}] NOT EVALUABLE: reason='{s_res.reason}'")

    # ============================================================
    #  Side-by-side comparison with 10D baseline
    # ============================================================
    log("\n==================================================")
    log(" 5. Side-by-Side Comparison: 10D Baseline vs SSL 778D")
    log("==================================================")
    baseline_report_path = Path("reports/benchmark/phase8_expanded_10d_eval.json")
    if baseline_report_path.exists():
        with open(baseline_report_path, "r", encoding="utf-8") as f:
            baseline_report = json.load(f)
        if "overall_test" in baseline_report and "metrics" in baseline_report["overall_test"]:
            bm = baseline_report["overall_test"]["metrics"]
            b_abst = baseline_report["overall_test"].get("abstention_rate", "N/A")
            log(f"{'Metric':<25s} {'10D Baseline':>15s} {'778D SSL':>15s}")
            log(f"{'-'*55}")
            log(f"{'EER':<25s} {bm['eer']:>15.4f} {overall_metrics.eer:>15.4f}")
            log(f"{'TPR @ 0.1% FPR':<25s} {bm.get('tpr_at_0_1pct_fpr', 'N/A'):>15} {overall_metrics.tpr_at_0_1pct_fpr:>15.4f}")
            log(f"{'TPR @ 1% FPR':<25s} {bm['tpr_at_1pct_fpr']:>15.4f} {overall_metrics.tpr_at_1pct_fpr:>15.4f}")
            log(f"{'TPR @ 5% FPR':<25s} {bm['tpr_at_5pct_fpr']:>15.4f} {overall_metrics.tpr_at_5pct_fpr:>15.4f}")
            log(f"{'ECE':<25s} {bm['ece']:>15.4f} {overall_metrics.ece:>15.4f}")
            log(f"{'Abstention Rate':<25s} {b_abst:>15} {abstention_rate:>15.4f}")
    else:
        log(f"Baseline report not found at {baseline_report_path}")

    # Save report
    report_dict = {k: v.to_dict() for k, v in slices.items()}
    report_dict["overall_test"] = {
        "slice_name": "overall_test",
        "status": "evaluated",
        "reason": None,
        "metrics": to_dict(overall_metrics),
        "abstention_rate": abstention_rate,
        "raw_scores": {
            "real_mean": float(np.mean(raw_scores_real)),
            "synth_mean": float(np.mean(raw_scores_synth)),
        },
        "calibrated_probabilities": {
            "real_mean": float(np.mean(cal_probs_real)),
            "synth_mean": float(np.mean(cal_probs_synth)),
        },
    }
    eval_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_report_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    log(f"\nSaved SSL evaluation report: {eval_report_path}")


if __name__ == "__main__":
    main()
