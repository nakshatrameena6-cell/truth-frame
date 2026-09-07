"""Run Part G baseline comparison experiments under a frozen evaluation protocol.

Compares:
  1. Legacy 4-feature baseline (unnormalized mean, rms, zcr, duration)
  2. Amplitude-normalized 4-feature baseline (peak-normalized mean, rms, zcr, duration)
  3. Expanded 10-feature classical baseline (peak-normalized + spectral/temporal statistics)
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.optimize import minimize

from audio_detection.data import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.calibration.temperature import TemperatureScaler
from audio_detection.evaluation.metrics import evaluate
from audio_detection.training.trainer import train_model


def extract_legacy_4features(audio_path: str) -> np.ndarray:
    """Extract unnormalized legacy 4 features (mean, rms, zcr, duration)."""
    signal, sr = sf.read(audio_path, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)
    
    mean_val = float(np.mean(mono))
    rms_val = float(np.sqrt(np.mean(mono ** 2) + 1e-12))
    zero_crossings = np.diff(np.signbit(mono)).nonzero()[0]
    zcr_val = float(len(zero_crossings) / max(len(mono), 1))
    duration_val = float(np.log1p(len(mono) / sr))
    
    return np.array([mean_val, rms_val, zcr_val, duration_val], dtype=np.float64)


def extract_norm_4features(audio_path: str) -> np.ndarray:
    """Extract peak-normalized 4 features (mean, rms, zcr, duration)."""
    signal, sr = sf.read(audio_path, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)
    peak = float(np.max(np.abs(mono)))
    if peak > 1e-6:
        mono = mono / peak
        
    mean_val = float(np.mean(mono))
    rms_val = float(np.sqrt(np.mean(mono ** 2) + 1e-12))
    zero_crossings = np.diff(np.signbit(mono)).nonzero()[0]
    zcr_val = float(len(zero_crossings) / max(len(mono), 1))
    duration_val = float(np.log1p(len(mono) / sr))
    
    return np.array([mean_val, rms_val, zcr_val, duration_val], dtype=np.float64)


def fit_logistic_and_calibrate(X_tr: np.ndarray, y_tr: np.ndarray, X_val: np.ndarray, y_val: np.ndarray, X_te: np.ndarray, y_te: np.ndarray) -> dict:
    """Fit logistic regression model on X_tr, calibrate temperature on X_val, evaluate on X_te."""
    num_features = X_tr.shape[1]

    def loss_func(params):
        w = params[:num_features]
        b = params[num_features]
        logits = X_tr @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
        bce = -np.mean(y_tr * np.log(p + 1e-12) + (1 - y_tr) * np.log(1 - p + 1e-12))
        reg = 1e-4 * np.sum(w ** 2)
        return bce + reg

    init_params = np.zeros(num_features + 1)
    res = minimize(loss_func, init_params, method="L-BFGS-B")
    w_fit = res.x[:num_features]
    b_fit = float(res.x[num_features])

    # Raw logits on val and test
    val_logits = X_val @ w_fit + b_fit
    test_logits = X_te @ w_fit + b_fit

    # Temperature scaling calibration
    scaler = TemperatureScaler()
    scaler.fit(val_logits.tolist(), y_val.astype(int).tolist())
    
    test_probs = scaler.transform(test_logits.tolist())

    eval_m = evaluate(
        labels=y_te.astype(int).tolist(),
        scores=test_probs,
        dataset="corpus",
        split="test",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version="exp",
    )

    return {
        "num_features": num_features,
        "eer": eval_m.eer,
        "tpr_at_1pct_fpr": eval_m.tpr_at_1pct_fpr,
        "ece": eval_m.ece,
        "weights": [round(float(w), 6) for w in w_fit],
        "bias": round(b_fit, 6),
        "temperature": round(float(scaler.temperature), 4),
    }


def main():
    manifest_path = Path("data/manifests/corpus.jsonl")
    manifest = CorpusManifest.load_jsonl(manifest_path)
    audio_root = Path(".")

    train_samples = [s for s in manifest.samples if s.split == "train"]
    val_samples = [s for s in manifest.samples if s.split == "validation"]
    test_samples = [s for s in manifest.samples if s.split == "test"]

    y_tr = np.array([1.0 if s.is_synthetic else 0.0 for s in train_samples])
    y_val = np.array([1.0 if s.is_synthetic else 0.0 for s in val_samples])
    y_te = np.array([1.0 if s.is_synthetic else 0.0 for s in test_samples])

    print("=== PART G: FRONTEND EXPERIMENTAL COMPARISON ===")
    
    # 1. Legacy 4-feature baseline
    X_tr_legacy = np.stack([extract_legacy_4features(s.audio_path) for s in train_samples])
    X_val_legacy = np.stack([extract_legacy_4features(s.audio_path) for s in val_samples])
    X_te_legacy = np.stack([extract_legacy_4features(s.audio_path) for s in test_samples])
    exp1 = fit_logistic_and_calibrate(X_tr_legacy, y_tr, X_val_legacy, y_val, X_te_legacy, y_te)
    print(f"\n1. Legacy 4-Feature Baseline:")
    print(f"   EER: {exp1['eer']:.4f} | TPR@1%FPR: {exp1['tpr_at_1pct_fpr']:.4f} | ECE: {exp1['ece']:.4f}")

    # 2. Amplitude-normalized 4-feature baseline
    X_tr_norm = np.stack([extract_norm_4features(s.audio_path) for s in train_samples])
    X_val_norm = np.stack([extract_norm_4features(s.audio_path) for s in val_samples])
    X_te_norm = np.stack([extract_norm_4features(s.audio_path) for s in test_samples])
    exp2 = fit_logistic_and_calibrate(X_tr_norm, y_tr, X_val_norm, y_val, X_te_norm, y_te)
    print(f"\n2. Amplitude-Normalized 4-Feature Baseline:")
    print(f"   EER: {exp2['eer']:.4f} | TPR@1%FPR: {exp2['tpr_at_1pct_fpr']:.4f} | ECE: {exp2['ece']:.4f}")

    # 3. Expanded 10-feature classical baseline using trainer
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    detector = train_model(manifest, audio_root, held_out_path, epochs=10, lr=0.01, seed=42)
    detector = calibrate_model(detector, manifest, audio_root)

    test_probs = []
    for s in test_samples:
        with open(s.audio_path, "rb") as f:
            b = f.read()
        res = detector.detect(b)
        test_probs.append(res["score"])

    exp3_m = evaluate(
        labels=y_te.astype(int).tolist(),
        scores=test_probs,
        dataset="corpus",
        split="test",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version=detector.model_version,
    )

    exp3 = {
        "num_features": 10,
        "eer": exp3_m.eer,
        "tpr_at_1pct_fpr": exp3_m.tpr_at_1pct_fpr,
        "ece": exp3_m.ece,
        "weights": [round(float(w), 6) for w in detector.weights],
        "bias": round(float(detector.bias), 6),
        "temperature": round(float(detector.threshold_config.temperature), 4),
    }

    print(f"\n3. Expanded 10-Feature Classical Baseline:")
    print(f"   EER: {exp3['eer']:.4f} | TPR@1%FPR: {exp3['tpr_at_1pct_fpr']:.4f} | ECE: {exp3['ece']:.4f}")

    report = {
        "legacy_4feature": exp1,
        "normalized_4feature": exp2,
        "expanded_10feature": exp3,
    }

    out_path = Path("reports/metrics/frontend_experiments.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved experiment results to {out_path}")


if __name__ == "__main__":
    main()
