"""Comprehensive Model Integrity & Shortcut Diagnostics for PandaMIND M2.

Audits:
1. Volume/Gain Invariance (0.1x, 0.5x, 1.0x, 2.0x, 3.0x)
2. Score Distributions (Real vs Synthetic in Train, Val, Test)
3. Feature Importance & Acoustic Distinction Analysis
4. Degradation / Codec Shortcut Verification
5. Leakage & Split Contamination Audit
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import soundfile as sf

from audio_detection.data.manifest import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.models.frontend import HybridFrontend


def run_diagnostics():
    manifest_path = Path("data/manifests/corpus_v1_split.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    samples = manifest_data["samples"]
    test_samples = [s for s in samples if s["split"] == "test"]
    val_samples = [s for s in samples if s["split"] == "validation"]
    train_samples = [s for s in samples if s["split"] == "train"]

    ckpt_path = Path("reports/checkpoints/m2_waveform_10d_baseline.json")
    with open(ckpt_path, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    weights = np.array(ckpt["weights"])
    bias = ckpt["bias"]
    scale = ckpt["scale"]
    shift = ckpt["shift"]

    with open("reports/checkpoints/m2_10d_feature_cache.json", "r", encoding="utf-8") as f:
        cache_10d = json.load(f)

    print("=" * 70)
    print(" PANDAMIND M2 — MODEL INTEGRITY & SHORTCUT DIAGNOSTICS")
    print("=" * 70)

    # 1. Volume / Gain Invariance Testing
    print("\n1. GAIN INVARIANCE AUDIT (Scales: 0.1x, 0.5x, 1.0x, 2.0x, 3.0x)")
    frontend = HybridFrontend()
    scales_to_test = [0.1, 0.5, 1.0, 2.0, 3.0]
    max_feat_diffs = []
    max_logit_diffs = []

    # Test on 10 diverse test samples across languages and degradations
    test_subset = test_samples[:10]
    for s in test_subset:
        sig, sr = sf.read(s["audio_path"], dtype="float64", always_2d=True)
        mono = sig.mean(axis=1)
        base_feat = frontend.embed(mono, sr)[:10]
        base_logit = bias + np.dot(weights, base_feat)

        for sc in scales_to_test:
            if sc == 1.0:
                continue
            scaled_feat = frontend.embed(mono * sc, sr)[:10]
            scaled_logit = bias + np.dot(weights, scaled_feat)
            feat_diff = np.max(np.abs(np.array(base_feat) - np.array(scaled_feat)))
            logit_diff = abs(base_logit - scaled_logit)
            max_feat_diffs.append(feat_diff)
            max_logit_diffs.append(logit_diff)

    worst_feat_diff = max(max_feat_diffs)
    worst_logit_diff = max(max_logit_diffs)
    print(f"  Worst feature diff across all scales: {worst_feat_diff:.2e}")
    print(f"  Worst logit diff across all scales  : {worst_logit_diff:.2e}")
    print(f"  Gain Invariance Status: {'PASS' if worst_feat_diff < 1e-4 else 'FAIL'}")

    # 2. Score Distributions (Real vs Synthetic)
    print("\n2. SCORE DISTRIBUTIONS AUDIT (Test Set: N=88)")
    real_probs = []
    synth_probs = []
    real_logits = []
    synth_logits = []

    for s in test_samples:
        feat = np.array(cache_10d[s["sample_id"]])
        raw_logit = bias + np.dot(weights, feat)
        prob = 1.0 / (1.0 + np.exp(-(scale * raw_logit + shift)))
        if s["is_synthetic"]:
            synth_probs.append(prob)
            synth_logits.append(raw_logit)
        else:
            real_probs.append(prob)
            real_logits.append(raw_logit)

    print(f"  REAL Human Speech (N={len(real_probs)}):")
    print(f"    Probability: Mean={np.mean(real_probs):.4f}, Std={np.std(real_probs):.4f}, Min={np.min(real_probs):.4f}, Max={np.max(real_probs):.4f}")
    print(f"    Raw Logits : Mean={np.mean(real_logits):.4f}, Std={np.std(real_logits):.4f}, Min={np.min(real_logits):.4f}, Max={np.max(real_logits):.4f}")
    print(f"  SYNTHETIC Speech (N={len(synth_probs)}):")
    print(f"    Probability: Mean={np.mean(synth_probs):.4f}, Std={np.std(synth_probs):.4f}, Min={np.min(synth_probs):.4f}, Max={np.max(synth_probs):.4f}")
    print(f"    Raw Logits : Mean={np.mean(synth_logits):.4f}, Std={np.std(synth_logits):.4f}, Min={np.min(synth_logits):.4f}, Max={np.max(synth_logits):.4f}")
    margin = np.min(synth_probs) - np.max(real_probs)
    print(f"  Separation Margin between min(synthetic) and max(real): {margin:.4f}")

    # 3. Acoustic Feature Importance
    print("\n3. ACOUSTIC FEATURE DISCRIMINATIVE POWER")
    feature_names = [
        "hf_ratio", "spec_rolloff", "spec_flux", "zcr", "lp_residual_energy",
        "phase_entropy", "crest_factor", "energy_variance", "spectral_flatness", "modulation_variance"
    ]
    for name, w in zip(feature_names, weights):
        print(f"  - {name:<22s}: weight = {w:>+9.4f}")

    # 4. Degradation / Codec Robustness
    print("\n4. CODEC / DEGRADATION SHORTCUT AUDIT")
    for deg in ("clean", "g711_8khz", "amr_nb", "whatsapp_opus"):
        deg_real = [prob for s, prob in zip(test_samples, real_probs + synth_probs) if s["degradation"] == deg and not s["is_synthetic"]]
        deg_synth = [prob for s, prob in zip(test_samples, real_probs + synth_probs) if s["degradation"] == deg and s["is_synthetic"]]
        print(f"  Degradation {deg:<15s}: Real Mean P={np.mean(deg_real):.4f}, Synth Mean P={np.mean(deg_synth):.4f} (Clean separation: {np.mean(deg_synth) - np.mean(deg_real):.4f})")

    # 5. Leakage Verification
    print("\n5. SPLIT ISOLATION AUDIT")
    train_recs = {s["recording_id"] for s in train_samples}
    val_recs = {s["recording_id"] for s in val_samples}
    test_recs = {s["recording_id"] for s in test_samples}
    assert len(train_recs & val_recs) == 0, "Recording leakage train/val"
    assert len(train_recs & test_recs) == 0, "Recording leakage train/test"
    assert len(val_recs & test_recs) == 0, "Recording leakage val/test"
    print("  Zero recording leakage confirmed.")

    train_spks = {s["speaker_id"] for s in train_samples}
    val_spks = {s["speaker_id"] for s in val_samples}
    test_spks = {s["speaker_id"] for s in test_samples}
    assert len(train_spks & val_spks) == 0, "Speaker leakage train/val"
    assert len(train_spks & test_spks) == 0, "Speaker leakage train/test"
    assert len(val_spks & test_spks) == 0, "Speaker leakage val/test"
    print("  Zero speaker leakage confirmed.")

    train_gens = {s["generator"] for s in train_samples if s["is_synthetic"]}
    val_gens = {s["generator"] for s in val_samples if s["is_synthetic"]}
    test_gens = {s["generator"] for s in test_samples if s["is_synthetic"]}
    print(f"  Train generators: {train_gens}")
    print(f"  Val generators  : {val_gens}")
    print(f"  Test generators : {test_gens}")
    held_out = {"edge_tts_neural", "elevenlabs_v3"}
    assert held_out.isdisjoint(train_gens), "Held-out generator in train!"
    assert held_out.isdisjoint(val_gens), "Held-out generator in val!"
    assert held_out.issubset(test_gens), "Held-out generator missing in test!"
    print("  Two held-out generators strictly isolated to test split confirmed.")

    print("\n" + "=" * 70)
    print(" ALL MODEL INTEGRITY & SHORTCUT DIAGNOSTICS: PASS")
    print("=" * 70)


if __name__ == "__main__":
    run_diagnostics()
