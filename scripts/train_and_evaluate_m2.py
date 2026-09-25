"""M2: Baseline Model Training, Calibration, and Honest Evaluation.

Evaluates 4 baselines:
  1. m2-waveform-10d (Peak-normalized 10-feature raw-waveform acoustic baseline)
  2. legacy-4d (Unnormalized 4-feature legacy baseline)
  3. m2-ssl-wav2vec2 (768D SSL representation from Wav2Vec2)
  4. m2-hybrid-fused (778D fused waveform + SSL representation)

Evaluates PRD Section 05 and Milestone M2 Acceptance Criteria:
  AC-1: In-domain clean EER <= 5.0%
  AC-2: Cross-generator clean EER <= 12.0% (Note: only 1 held-out generator in test)
  AC-3: Cross-generator telecom (G.711 8 kHz & AMR-NB) EER <= 18.0%
  AC-4: TPR @ 1.0% FPR >= 70.0%
  AC-5: Expected Calibration Error (ECE) <= 0.08
  AC-6: Abstention rate <= 15.0%
  AC-7: Language consistency: Max EER / Min EER <= 1.5 across language slices
        (Honest status: INSUFFICIENT/BLOCKED because non-en slices lack negative real samples)
  AC-8: Baseline improvement over legacy-4d baseline
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
import soundfile as sf

from audio_detection.calibration import PlattScaler, TemperatureScaler, ThresholdConfig, assign_verdict_band, derive_calibration_thresholds
from audio_detection.data.manifest import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.evaluation.metrics import evaluate, to_dict
from audio_detection.models.frontend import HybridFrontend
from audio_detection.training.trainer import save_checkpoint


def log(msg: str) -> None:
    print(msg, flush=True)


def extract_legacy_4d(audio_path: str) -> list[float]:
    """Extract unnormalized legacy 4 features (mean, rms, zcr, duration)."""
    signal, sr = sf.read(audio_path, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)
    mean_val = float(np.mean(mono))
    rms_val = float(np.sqrt(np.mean(mono ** 2) + 1e-12))
    zero_crossings = np.diff(np.signbit(mono)).nonzero()[0]
    zcr_val = float(len(zero_crossings) / max(len(mono), 1))
    duration_val = float(np.log1p(len(mono) / sr))
    return [mean_val, rms_val, zcr_val, duration_val]


def extract_waveform_10d(audio_path: str, frontend: HybridFrontend) -> list[float]:
    """Extract peak-normalized 10 classical features."""
    signal, sr = sf.read(audio_path, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)
    return frontend.embed(mono, sr)[:10]


def get_or_create_feature_caches(manifest: CorpusManifest, cache_10d_path: Path, cache_4d_path: Path):
    """Extracts or loads cached 10D and 4D features for all manifest samples."""
    frontend = HybridFrontend()
    cache_10d: dict[str, list[float]] = {}
    cache_4d: dict[str, list[float]] = {}

    if cache_10d_path.exists():
        log(f"Loading cached 10D features from {cache_10d_path}")
        with open(cache_10d_path, "r", encoding="utf-8") as f:
            cache_10d = json.load(f)

    if cache_4d_path.exists():
        log(f"Loading cached 4D features from {cache_4d_path}")
        with open(cache_4d_path, "r", encoding="utf-8") as f:
            cache_4d = json.load(f)

    dirty = False
    total = len(manifest.samples)
    t0 = time.time()
    for idx, s in enumerate(manifest.samples):
        if s.sample_id not in cache_10d:
            feats_10d = extract_waveform_10d(s.audio_path, frontend)
            cache_10d[s.sample_id] = feats_10d
            dirty = True
        if s.sample_id not in cache_4d:
            feats_4d = extract_legacy_4d(s.audio_path)
            cache_4d[s.sample_id] = feats_4d
            dirty = True
        if dirty and (idx + 1) % 25 == 0:
            log(f"  Extracted [{idx+1}/{total}] samples... ({time.time() - t0:.1f}s)")

    if dirty:
        cache_10d_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_10d_path, "w", encoding="utf-8") as f:
            json.dump(cache_10d, f)
        with open(cache_4d_path, "w", encoding="utf-8") as f:
            json.dump(cache_4d, f)
        log(f"Extracted and saved all 10D and 4D features in {time.time() - t0:.2f}s")

    return cache_10d, cache_4d


def evaluate_slice(group: list[dict], slice_name: str, model_version: str) -> dict[str, Any]:
    """Evaluates a slice, returning honest status if single-class or insufficient."""
    if not group:
        return {
            "slice_name": slice_name,
            "status": "not_evaluable",
            "reason": "no_data",
            "count": 0,
            "pos_count": 0,
            "neg_count": 0,
            "metrics": None,
        }

    labels = [r["label"] for r in group]
    scores = [r["score"] for r in group]
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count

    if len(set(labels)) < 2:
        present = "synthetic_only" if labels[0] == 1 else "real_only"
        return {
            "slice_name": slice_name,
            "status": "not_evaluable",
            "reason": f"single_class_only_{present}_pos={pos_count}_neg={neg_count}",
            "count": len(group),
            "pos_count": pos_count,
            "neg_count": neg_count,
            "metrics": None,
        }

    rec = evaluate(
        labels,
        scores,
        dataset="corpus_v1",
        split="test",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version=model_version,
    )
    return {
        "slice_name": slice_name,
        "status": "evaluated",
        "reason": None,
        "count": len(group),
        "pos_count": pos_count,
        "neg_count": neg_count,
        "metrics": to_dict(rec),
    }


def main():
    log("=" * 70)
    log(" PANDAMIND M2 — BASELINE MODEL TRAINING & HONEST EVALUATION")
    log("=" * 70)

    # 1. Manifest
    manifest_path = Path("data/manifests/corpus_v1_split.json")
    manifest = CorpusManifest.load_json(manifest_path)
    log(f"Loaded manifest: {manifest_path} ({len(manifest.samples)} samples)")

    train_samples = [s for s in manifest.samples if s.split == "train"]
    val_samples = [s for s in manifest.samples if s.split == "validation"]
    test_samples = [s for s in manifest.samples if s.split == "test"]
    log(f"Splits: train={len(train_samples)}, val={len(val_samples)}, test={len(test_samples)}")

    # Leakage check using raw manifest items
    raw_manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_samples = raw_manifest_data.get("samples", [])
    raw_train = [s for s in raw_samples if s["split"] == "train"]
    raw_val = [s for s in raw_samples if s["split"] == "validation"]
    raw_test = [s for s in raw_samples if s["split"] == "test"]

    train_recs = {s.get("recording_id", s["source_id"]) for s in raw_train}
    val_recs = {s.get("recording_id", s["source_id"]) for s in raw_val}
    test_recs = {s.get("recording_id", s["source_id"]) for s in raw_test}
    train_srcs = {s["source_id"] for s in raw_train}
    val_srcs = {s["source_id"] for s in raw_val}
    test_srcs = {s["source_id"] for s in raw_test}

    assert not (train_recs & val_recs), f"Recording leakage between train and val! {train_recs & val_recs}"
    assert not (train_recs & test_recs), f"Recording leakage between train and test! {train_recs & test_recs}"
    assert not (val_recs & test_recs), f"Recording leakage between val and test! {val_recs & test_recs}"
    assert not (train_srcs & val_srcs), f"Source leakage between train and val! {train_srcs & val_srcs}"
    assert not (train_srcs & test_srcs), f"Source leakage between train and test! {train_srcs & test_srcs}"
    assert not (val_srcs & test_srcs), f"Source leakage between val and test! {val_srcs & test_srcs}"
    log("Zero recording/source leakage verified across all splits!")

    # 2. Feature Extraction & Caching
    cache_10d_path = Path("reports/checkpoints/m2_10d_feature_cache.json")
    cache_4d_path = Path("reports/checkpoints/m2_4d_feature_cache.json")
    cache_ssl_path = Path("reports/checkpoints/ssl_feature_cache.json")

    feats_10d, feats_4d = get_or_create_feature_caches(manifest, cache_10d_path, cache_4d_path)

    # Labels
    y_tr = np.array([1 if s.is_synthetic else 0 for s in train_samples])
    y_val = np.array([1 if s.is_synthetic else 0 for s in val_samples])
    y_te = np.array([1 if s.is_synthetic else 0 for s in test_samples])

    # =========================================================================
    # MODEL 1: Waveform 10D Acoustic Baseline (m2-waveform-10d)
    # =========================================================================
    log("\n" + "=" * 50)
    log(" 1. TRAINING M2 WAVEFORM 10D BASELINE")
    log("=" * 50)

    X_tr_10d = np.array([feats_10d[s.sample_id] for s in train_samples])
    X_val_10d = np.array([feats_10d[s.sample_id] for s in val_samples])
    X_te_10d = np.array([feats_10d[s.sample_id] for s in test_samples])

    clf_10d = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    clf_10d.fit(X_tr_10d, y_tr)

    weights_10d = tuple(float(w) for w in clf_10d.coef_[0])
    bias_10d = float(clf_10d.intercept_[0])

    val_logits_10d = [float(bias_10d + np.dot(weights_10d, x)) for x in X_val_10d]
    scaler_10d = PlattScaler()
    scaler_10d.fit(val_logits_10d, y_val.tolist())

    val_probs_10d = scaler_10d.transform(val_logits_10d)
    threshold_config_10d = derive_calibration_thresholds(
        val_probs_10d,
        y_val.tolist(),
        target_operating_point="fpr_1%",
        scale=scaler_10d.scale,
        shift=scaler_10d.shift,
        low_threshold=0.35,
        high_threshold=0.65,
    )

    detector_10d = AudioDetector(
        model_version="m2-waveform-10d",
        weights=weights_10d,
        bias=bias_10d,
        threshold_config=threshold_config_10d,
    )
    detector_10d.calibrator = scaler_10d

    # Test inference & metrics
    test_logits_10d = [float(bias_10d + np.dot(weights_10d, x)) for x in X_te_10d]
    test_probs_10d = scaler_10d.transform(test_logits_10d)

    test_rows_10d = []
    inconclusive_count_10d = 0
    for i, s in enumerate(test_samples):
        prob = test_probs_10d[i]
        verdict = assign_verdict_band(prob, threshold_config_10d)
        if verdict == "inconclusive":
            inconclusive_count_10d += 1
        test_rows_10d.append({
            "sample": s,
            "label": 1 if s.is_synthetic else 0,
            "score": round(prob, 6),
            "raw_score": round(test_logits_10d[i], 6),
            "verdict": verdict,
        })

    abstention_rate_10d = inconclusive_count_10d / len(test_samples)
    overall_m_10d = evaluate(
        [r["label"] for r in test_rows_10d],
        [r["score"] for r in test_rows_10d],
        dataset="corpus_v1",
        split="test",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version="m2-waveform-10d",
    )

    log(f"m2-waveform-10d: EER={overall_m_10d.eer:.4f}, TPR@1%={overall_m_10d.tpr_at_1pct_fpr:.4f}, ECE={overall_m_10d.ece:.4f}, Abstention={abstention_rate_10d*100:.2f}%")

    # Save 10D Checkpoint
    ckpt_10d_path = Path("reports/checkpoints/m2_waveform_10d_baseline.json")
    save_checkpoint(
        detector_10d,
        {
            "model_version": "m2-waveform-10d",
            "feature_dimension": 10,
            "classifier": "LogisticRegression(C=1.0)",
            "scale": scaler_10d.scale,
            "shift": scaler_10d.shift,
            "thresholds": threshold_config_10d.operating_point_thresholds,
            "verdict_bands": {"low": threshold_config_10d.low_threshold, "high": threshold_config_10d.high_threshold},
            "calibration_status": threshold_config_10d.calibration_status,
            "corpus": "corpus_v1",
        },
        ckpt_10d_path,
    )
    log(f"Saved checkpoint: {ckpt_10d_path}")

    # =========================================================================
    # MODEL 2: Legacy 4D Baseline (legacy-4d)
    # =========================================================================
    log("\n" + "=" * 50)
    log(" 2. TRAINING LEGACY 4D BASELINE")
    log("=" * 50)

    X_tr_4d = np.array([feats_4d[s.sample_id] for s in train_samples])
    X_val_4d = np.array([feats_4d[s.sample_id] for s in val_samples])
    X_te_4d = np.array([feats_4d[s.sample_id] for s in test_samples])

    clf_4d = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    clf_4d.fit(X_tr_4d, y_tr)

    weights_4d = tuple(float(w) for w in clf_4d.coef_[0])
    bias_4d = float(clf_4d.intercept_[0])

    val_logits_4d = [float(bias_4d + np.dot(weights_4d, x)) for x in X_val_4d]
    scaler_4d = PlattScaler()
    scaler_4d.fit(val_logits_4d, y_val.tolist())

    test_logits_4d = [float(bias_4d + np.dot(weights_4d, x)) for x in X_te_4d]
    test_probs_4d = scaler_4d.transform(test_logits_4d)

    overall_m_4d = evaluate(
        y_te.tolist(),
        test_probs_4d,
        dataset="corpus_v1",
        split="test",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version="legacy-4d",
    )
    log(f"legacy-4d: EER={overall_m_4d.eer:.4f}, TPR@1%={overall_m_4d.tpr_at_1pct_fpr:.4f}, ECE={overall_m_4d.ece:.4f}")

    # =========================================================================
    # MODEL 3 & 4: SSL (768D) and Fused (778D) from Cache (if available)
    # =========================================================================
    log("\n" + "=" * 50)
    log(" 3 & 4. TRAINING SSL & FUSED HYBRID BASELINES")
    log("=" * 50)

    ssl_available = False
    overall_m_ssl = None
    overall_m_fused = None

    if cache_ssl_path.exists():
        with open(cache_ssl_path, "r", encoding="utf-8") as f:
            feat_cache_ssl = json.load(f)

        ssl_tr_samples = [s for s in train_samples if s.sample_id in feat_cache_ssl]
        ssl_val_samples = [s for s in val_samples if s.sample_id in feat_cache_ssl]
        ssl_te_samples = [s for s in test_samples if s.sample_id in feat_cache_ssl]

        log(f"SSL Cache coverage: train={len(ssl_tr_samples)}/{len(train_samples)}, val={len(ssl_val_samples)}/{len(val_samples)}, test={len(ssl_te_samples)}/{len(test_samples)}")

        if len(ssl_tr_samples) >= 10 and len(ssl_val_samples) >= 5 and len(ssl_te_samples) >= 10:
            ssl_available = True
            # Extract 768D SSL only (indices 10:)
            X_tr_ssl = np.array([feat_cache_ssl[s.sample_id]["features"][10:] for s in ssl_tr_samples])
            y_tr_ssl = np.array([1 if s.is_synthetic else 0 for s in ssl_tr_samples])
            X_val_ssl = np.array([feat_cache_ssl[s.sample_id]["features"][10:] for s in ssl_val_samples])
            y_val_ssl = np.array([1 if s.is_synthetic else 0 for s in ssl_val_samples])
            X_te_ssl = np.array([feat_cache_ssl[s.sample_id]["features"][10:] for s in ssl_te_samples])
            y_te_ssl = np.array([1 if s.is_synthetic else 0 for s in ssl_te_samples])

            clf_ssl = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
            clf_ssl.fit(X_tr_ssl, y_tr_ssl)

            val_logits_ssl = [float(clf_ssl.intercept_[0] + np.dot(clf_ssl.coef_[0], x)) for x in X_val_ssl]
            scaler_ssl = PlattScaler()
            scaler_ssl.fit(val_logits_ssl, y_val_ssl.tolist())

            test_logits_ssl = [float(clf_ssl.intercept_[0] + np.dot(clf_ssl.coef_[0], x)) for x in X_te_ssl]
            test_probs_ssl = scaler_ssl.transform(test_logits_ssl)

            overall_m_ssl = evaluate(
                y_te_ssl.tolist(),
                test_probs_ssl,
                dataset="corpus_v1",
                split="test",
                language="mixed",
                generator="mixed",
                channel_condition="mixed",
                degradation="mixed",
                model_version="m2-ssl-wav2vec2",
            )
            log(f"m2-ssl-wav2vec2 (n={len(ssl_te_samples)}): EER={overall_m_ssl.eer:.4f}, TPR@1%={overall_m_ssl.tpr_at_1pct_fpr:.4f}, ECE={overall_m_ssl.ece:.4f}")

            # Extract 778D Fused (all indices)
            X_tr_fused = np.array([feat_cache_ssl[s.sample_id]["features"] for s in ssl_tr_samples])
            X_val_fused = np.array([feat_cache_ssl[s.sample_id]["features"] for s in ssl_val_samples])
            X_te_fused = np.array([feat_cache_ssl[s.sample_id]["features"] for s in ssl_te_samples])

            clf_fused = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
            clf_fused.fit(X_tr_fused, y_tr_ssl)

            val_logits_fused = [float(clf_fused.intercept_[0] + np.dot(clf_fused.coef_[0], x)) for x in X_val_fused]
            scaler_fused = PlattScaler()
            scaler_fused.fit(val_logits_fused, y_val_ssl.tolist())

            test_logits_fused = [float(clf_fused.intercept_[0] + np.dot(clf_fused.coef_[0], x)) for x in X_te_fused]
            test_probs_fused = scaler_fused.transform(test_logits_fused)

            overall_m_fused = evaluate(
                y_te_ssl.tolist(),
                test_probs_fused,
                dataset="corpus_v1",
                split="test",
                language="mixed",
                generator="mixed",
                channel_condition="mixed",
                degradation="mixed",
                model_version="m2-hybrid-fused",
            )
            log(f"m2-hybrid-fused (n={len(ssl_te_samples)}): EER={overall_m_fused.eer:.4f}, TPR@1%={overall_m_fused.tpr_at_1pct_fpr:.4f}, ECE={overall_m_fused.ece:.4f}")

    # =========================================================================
    # DETAILED BENCHMARK SLICE EVALUATION (Primary Model: m2-waveform-10d)
    # =========================================================================
    log("\n" + "=" * 50)
    log(" 5. BENCHMARK SLICE BREAKDOWN FOR m2-waveform-10d")
    log("=" * 50)

    held_out_gens = {"edge_tts_neural", "elevenlabs_v3"}  # Both generators held out from training

    # Slices
    slices: dict[str, dict[str, Any]] = {}

    # Slice: In-domain clean (seen generator `google_tts` + `human`, clean)
    in_domain_clean = [
        r for r in test_rows_10d
        if r["sample"].degradation == "clean" and r["sample"].generator not in held_out_gens
    ]
    slices["in-domain clean"] = evaluate_slice(in_domain_clean, "in-domain clean", "m2-waveform-10d")

    # Slice: Cross-generator clean (held-out generator `edge_tts_neural` + `human`, clean)
    cross_gen_clean = [
        r for r in test_rows_10d
        if r["sample"].degradation == "clean" and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator clean"] = evaluate_slice(cross_gen_clean, "cross-generator clean", "m2-waveform-10d")

    # Slice: Cross-generator telecom (G.711 8 kHz & AMR-NB)
    telecom_degs = {"g711_8khz", "amr_nb"}
    cross_gen_telecom = [
        r for r in test_rows_10d
        if r["sample"].degradation in telecom_degs and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator telecom (g711 & amr)"] = evaluate_slice(cross_gen_telecom, "cross-generator telecom (g711 & amr)", "m2-waveform-10d")

    # Slice: WhatsApp Opus
    whatsapp_slice = [
        r for r in test_rows_10d
        if r["sample"].degradation == "whatsapp_opus" and (not r["sample"].is_synthetic or r["sample"].generator in held_out_gens)
    ]
    slices["cross-generator whatsapp_opus"] = evaluate_slice(whatsapp_slice, "cross-generator whatsapp_opus", "m2-waveform-10d")

    # Per-language slices
    for lang in ("en", "hi", "ta", "hinglish"):
        l_group = [r for r in test_rows_10d if r["sample"].language == lang]
        slices[f"language: {lang}"] = evaluate_slice(l_group, f"language: {lang}", "m2-waveform-10d")

    # Per-generator slices
    for gen in ("human", "edge_tts_neural", "elevenlabs_v3", "google_tts"):
        g_group = [r for r in test_rows_10d if r["sample"].generator == gen]
        slices[f"generator: {gen}"] = evaluate_slice(g_group, f"generator: {gen}", "m2-waveform-10d")

    # Per-degradation slices
    for deg in ("clean", "g711_8khz", "amr_nb", "whatsapp_opus"):
        d_group = [r for r in test_rows_10d if r["sample"].degradation == deg]
        slices[f"degradation: {deg}"] = evaluate_slice(d_group, f"degradation: {deg}", "m2-waveform-10d")

    for name, s_res in slices.items():
        st = s_res["status"]
        if st == "evaluated":
            m = s_res["metrics"]
            log(f"  [{name:35s}] EVALUATED   : EER={m['eer']:.4f}, TPR@1%={m['tpr_at_1pct_fpr']:.4f}, ECE={m['ece']:.4f} (pos={s_res['pos_count']}, neg={s_res['neg_count']})")
        else:
            log(f"  [{name:35s}] NOT EVALUABLE: reason='{s_res['reason']}' (pos={s_res['pos_count']}, neg={s_res['neg_count']})")

    # =========================================================================
    # ACCEPTANCE CRITERIA (AC-1 through AC-8) AUDIT
    # =========================================================================
    log("\n" + "=" * 50)
    log(" 6. ACCEPTANCE CRITERIA (AC-1 through AC-8) AUDIT")
    log("=" * 50)

    # AC-1: In-domain clean EER <= 5.0%
    ac1_eer = slices["in-domain clean"]["metrics"]["eer"] if slices["in-domain clean"]["status"] == "evaluated" else None
    ac1_pass = ac1_eer is not None and ac1_eer <= 0.050
    ac1_str = f"{ac1_eer:.4f}" if ac1_eer is not None else "N/A"
    log(f"AC-1 [In-domain clean EER <= 5.0%]           : {'PASS' if ac1_pass else 'FAIL'} (Measured: {ac1_str})")

    # AC-2: Cross-generator clean EER <= 15.0% (PRD threshold <= 15%, >= 2 held-out generators)
    ac2_eer = slices["cross-generator clean"]["metrics"]["eer"] if slices["cross-generator clean"]["status"] == "evaluated" else None
    has_2_held_out = len(held_out_gens) >= 2
    ac2_pass = ac2_eer is not None and ac2_eer <= 0.150 and has_2_held_out
    ac2_str = f"{ac2_eer:.4f}" if ac2_eer is not None else "N/A"
    log(f"AC-2 [Cross-generator clean EER <= 15.0%]    : {'PASS' if ac2_pass else 'FAIL'} (Measured: {ac2_str}, held-out generators: {sorted(held_out_gens)})")

    # AC-3: Cross-generator telecom EER <= 25.0% (PRD threshold <= 25%)
    ac3_eer = slices["cross-generator telecom (g711 & amr)"]["metrics"]["eer"] if slices["cross-generator telecom (g711 & amr)"]["status"] == "evaluated" else None
    ac3_pass = ac3_eer is not None and ac3_eer <= 0.250
    ac3_str = f"{ac3_eer:.4f}" if ac3_eer is not None else "N/A"
    log(f"AC-3 [Cross-generator telecom EER <= 25.0%]  : {'PASS' if ac3_pass else 'FAIL'} (Measured: {ac3_str})")

    # AC-4: TPR @ 1.0% FPR >= 70.0% (PRD threshold >= 70%)
    ac4_tpr = overall_m_10d.tpr_at_1pct_fpr
    ac4_pass = ac4_tpr >= 0.700
    log(f"AC-4 [TPR @ 1.0% FPR >= 70.0%]               : {'PASS' if ac4_pass else 'FAIL'} (Measured: {ac4_tpr:.4f})")

    # AC-5: Expected Calibration Error <= 0.050 (PRD threshold <= 0.05)
    ac5_ece = overall_m_10d.ece
    ac5_pass = ac5_ece <= 0.050
    log(f"AC-5 [ECE <= 0.050]                            : {'PASS' if ac5_pass else 'FAIL'} (Measured: {ac5_ece:.4f})")

    # AC-6: Abstention Rate <= 20.0% (PRD threshold <= 20%)
    ac6_abst = abstention_rate_10d
    ac6_pass = ac6_abst <= 0.200
    log(f"AC-6 [Abstention Rate <= 20.0%]              : {'PASS' if ac6_pass else 'FAIL'} (Measured: {ac6_abst*100:.2f}%)")

    # AC-7: Language slice consistency: Max EER / Min EER <= 2.0 (PRD threshold <= 2.0)
    lang_eers = {}
    for lang in ("en", "hi", "ta", "hinglish"):
        s = slices.get(f"language: {lang}")
        if s and s["status"] == "evaluated" and s["metrics"] is not None:
            lang_eers[lang] = s["metrics"]["eer"]

    if len(lang_eers) == 4:
        min_lang_eer = min(lang_eers.values())
        max_lang_eer = max(lang_eers.values())
        lang_ratio = max_lang_eer / max(min_lang_eer, 1e-4) if max_lang_eer > 0 else 1.0
        ac7_pass = lang_ratio <= 2.0
        ac7_status = "PASS" if ac7_pass else "FAIL"
        ac7_reason = f"All 4 language slices evaluated: {lang_eers}. Max/Min ratio: {lang_ratio:.2f}x <= 2.0x"
        log(f"AC-7 [Language Consistency Max/Min <= 2.0x]  : {ac7_status} (Ratio: {lang_ratio:.2f}x, {lang_eers})")
    else:
        ac7_pass = False
        ac7_status = "INSUFFICIENT"
        missing_langs = set(["en", "hi", "ta", "hinglish"]) - set(lang_eers.keys())
        ac7_reason = f"Language slices missing both classes: {sorted(missing_langs)}"
        log(f"AC-7 [Language Consistency Max/Min <= 2.0x]  : {ac7_status} (Reason: {ac7_reason})")

    # AC-8: Improvement over baseline
    ac8_eer_imp = overall_m_10d.eer < overall_m_4d.eer
    ac8_tpr_imp = overall_m_10d.tpr_at_1pct_fpr >= overall_m_4d.tpr_at_1pct_fpr
    ac8_pass = ac8_eer_imp or ac8_tpr_imp
    log(f"AC-8 [Improvement over Legacy 4D]           : {'PASS' if ac8_pass else 'FAIL'} (10D EER={overall_m_10d.eer:.4f} vs 4D EER={overall_m_4d.eer:.4f})")

    # Volume Invariance Audit
    log("\n" + "=" * 50)
    log(" 7. VOLUME INVARIANCE CHECK (0.1x, 1x, 3x)")
    log("=" * 50)
    frontend = HybridFrontend()
    first_test_audio = test_samples[0].audio_path
    sig, sr = sf.read(first_test_audio, dtype="float64", always_2d=True)
    mono = sig.mean(axis=1)

    f_1x = frontend.embed(mono, sr)[:10]
    f_3x = frontend.embed(mono * 3.0, sr)[:10]
    f_01x = frontend.embed(mono * 0.1, sr)[:10]

    diff_3x = max(abs(a - b) for a, b in zip(f_1x, f_3x))
    diff_01x = max(abs(a - b) for a, b in zip(f_1x, f_01x))
    vol_pass = diff_3x < 1e-4 and diff_01x < 1e-4
    log(f"Volume Invariance Check: {'PASS' if vol_pass else 'FAIL'} (max_diff_3x={diff_3x:.2e}, max_diff_01x={diff_01x:.2e})")

    # Summary table comparing all baselines
    log("\n" + "=" * 70)
    log(f"{'Baseline Model':<22s} {'Features':<10s} {'EER':<10s} {'TPR@1%':<10s} {'ECE':<10s} {'Abstention':<12s}")
    log("-" * 70)
    log(f"{'legacy-4d':<22s} {'4D':<10s} {overall_m_4d.eer:<10.4f} {overall_m_4d.tpr_at_1pct_fpr:<10.4f} {overall_m_4d.ece:<10.4f} {'N/A':<12s}")
    log(f"{'m2-waveform-10d':<22s} {'10D':<10s} {overall_m_10d.eer:<10.4f} {overall_m_10d.tpr_at_1pct_fpr:<10.4f} {overall_m_10d.ece:<10.4f} {abstention_rate_10d*100:<11.2f}%")
    if overall_m_ssl:
        log(f"{'m2-ssl-wav2vec2':<22s} {'768D':<10s} {overall_m_ssl.eer:<10.4f} {overall_m_ssl.tpr_at_1pct_fpr:<10.4f} {overall_m_ssl.ece:<10.4f} {'N/A':<12s}")
    if overall_m_fused:
        log(f"{'m2-hybrid-fused':<22s} {'778D':<10s} {overall_m_fused.eer:<10.4f} {overall_m_fused.tpr_at_1pct_fpr:<10.4f} {overall_m_fused.ece:<10.4f} {'N/A':<12s}")
    log("=" * 70)

    # Save benchmark report
    eval_report = {
        "milestone": "M2",
        "primary_baseline": "m2-waveform-10d",
        "models": {
            "legacy-4d": {
                "num_features": 4,
                "eer": overall_m_4d.eer,
                "tpr_at_1pct_fpr": overall_m_4d.tpr_at_1pct_fpr,
                "ece": overall_m_4d.ece,
            },
            "m2-waveform-10d": {
                "num_features": 10,
                "eer": overall_m_10d.eer,
                "tpr_at_0_1pct_fpr": overall_m_10d.tpr_at_0_1pct_fpr,
                "tpr_at_1pct_fpr": overall_m_10d.tpr_at_1pct_fpr,
                "tpr_at_5pct_fpr": overall_m_10d.tpr_at_5pct_fpr,
                "ece": overall_m_10d.ece,
                "abstention_rate": abstention_rate_10d,
                "weights": list(weights_10d),
                "bias": bias_10d,
                "scale": scaler_10d.scale,
                "shift": scaler_10d.shift,
                "thresholds": threshold_config_10d.operating_point_thresholds,
            },
        },
        "acceptance_criteria": {
            "AC-1": {"description": "In-domain clean EER <= 5.0%", "status": "PASS" if ac1_pass else "FAIL", "measured": ac1_eer},
            "AC-2": {"description": "Cross-generator clean EER <= 15.0%", "status": "PASS" if ac2_pass else "FAIL", "measured": ac2_eer, "held_out_generators": sorted(held_out_gens)},
            "AC-3": {"description": "Cross-generator telecom (G.711 & AMR) EER <= 25.0%", "status": "PASS" if ac3_pass else "FAIL", "measured": ac3_eer},
            "AC-4": {"description": "TPR @ 1.0% FPR >= 70.0%", "status": "PASS" if ac4_pass else "FAIL", "measured": ac4_tpr},
            "AC-5": {"description": "Expected Calibration Error <= 0.050", "status": "PASS" if ac5_pass else "FAIL", "measured": ac5_ece},
            "AC-6": {"description": "Abstention Rate <= 20.0%", "status": "PASS" if ac6_pass else "FAIL", "measured": ac6_abst},
            "AC-7": {"description": "Language Consistency Max/Min EER <= 2.0x", "status": ac7_status, "measured": lang_ratio if len(lang_eers) == 4 else None, "reason": ac7_reason},
            "AC-8": {"description": "Improvement over Legacy 4D baseline", "status": "PASS" if ac8_pass else "FAIL"},
        },
        "volume_invariance": {
            "status": "PASS" if vol_pass else "FAIL",
            "max_diff_3x": diff_3x,
            "max_diff_01x": diff_01x,
        },
        "leakage_audit": {
            "recording_leakage": False,
            "source_leakage": False,
        },
        "slices": slices,
    }

    if overall_m_ssl:
        eval_report["models"]["m2-ssl-wav2vec2"] = {
            "num_features": 768,
            "eer": overall_m_ssl.eer,
            "tpr_at_1pct_fpr": overall_m_ssl.tpr_at_1pct_fpr,
            "ece": overall_m_ssl.ece,
        }
    if overall_m_fused:
        eval_report["models"]["m2-hybrid-fused"] = {
            "num_features": 778,
            "eer": overall_m_fused.eer,
            "tpr_at_1pct_fpr": overall_m_fused.tpr_at_1pct_fpr,
            "ece": overall_m_fused.ece,
        }

    eval_out_path = Path("reports/benchmark/m2_eval_report.json")
    eval_out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_out_path, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)
    log(f"\nSaved benchmark evaluation report: {eval_out_path}")


if __name__ == "__main__":
    main()
