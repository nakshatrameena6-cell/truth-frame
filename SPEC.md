# PandaMIND Phase 3, Phase 5, Phase 6 & Phase 7 Specification

## Scope
PandaMIND is an offline Python foundation for synthetic-audio detection work. Phase 3 establishes a versioned, deterministic evaluation/benchmark specification (`phase3-v1`). Phase 5 executes baseline evaluation of the trained Phase 4 detector model across defined benchmark slices. Phase 6 implements deterministic calibration and thresholding logic. Phase 7 expands the dataset infrastructure to provide representative validation and evaluation splits.

## 1. Benchmark Specification (`phase3-v1`)
* **Version**: `phase3-v1`
* **Languages**: Hindi (`hi`), Tamil (`ta`), English (`en`), Hinglish (`hinglish`)
* **Classes**: Real (`is_synthetic: False`), Synthetic (`is_synthetic: True`)
* **Generators**: Seen generators (`human`, `elevenlabs_v3`), Held-out generators (`pending_unresolved`)
* **Degradations**: `clean`, `g711_8khz`, `amr_nb`, `whatsapp_opus`
* **Splits**: Train, Validation, Test

## 2. Held-out Generator Rules
Authoritative configuration: `src/audio_detection/config/held_out_generators.json`.
* **Enforcement**:
  * Held-out generators are **forbidden** in train.
  * Held-out generators are **forbidden** in validation.
  * Held-out generators are **allowed** in test.
* Connected source/speaker group isolation across splits is strictly enforced.

## 3. Metrics & Evaluation Slices
Frozen metrics:
* EER (Equal Error Rate)
* TPR @ 0.1% FPR
* TPR @ 1% FPR
* TPR @ 5% FPR
* ECE (Expected Calibration Error for top label)

Defined evaluation slices:
1. **in-domain clean**: Seen generators with `clean` degradation.
2. **cross-generator clean**: Held-out generators with `clean` degradation.
3. **cross-generator telecom**: Held-out generators with telecom degradations (`g711_8khz`, `amr_nb`, `whatsapp_opus`).
4. **language fairness**: Evaluation slices broken down per language (`hi`, `ta`, `en`, `hinglish`).

### PRD Acceptance Targets (Future Targets)
*Note: Targets apply to full production datasets, not baseline evaluation sets.*
* In-domain clean TPR @ 1% FPR: > 95%
* Cross-generator clean TPR @ 1% FPR: > 90%
* Cross-generator telecom TPR @ 1% FPR: > 85%
* ECE: < 0.05
* EER: < 5%

## 4. Benchmark Validity & Slicing Policy
* No train/test or speaker/source leakage.
* Held-out generators remain strictly isolated.
* **If a slice lacks sample coverage or lacks representation of both classes (real & synthetic), it is marked `not_evaluable` with a specific reason string rather than reporting fake or zeroed metrics.**
* Evaluation is fully offline and deterministic.

## 5. Calibration & Thresholding Protocol (Phase 6)
* **Temperature Scaling**: Fits positive temperature $T$ using negative log-likelihood (NLL) grid search on validation logits and labels.
* **Operating Points**: Derived strictly from the **validation set** (never test set):
  * `FPR 0.1%` (0.001)
  * `FPR 1.0%` (0.01)
  * `FPR 5.0%` (0.05)
* **Verdict Bands**:
  * `consistent_with_human` (calibrated probability $p < \theta_{\text{low}}$)
  * `inconclusive` ($\theta_{\text{low}} \le p \le \theta_{\text{high}}$)
  * `likely_synthetic` ($p > \theta_{\text{high}}$)
* **Inconclusive Non-disableability**: The `inconclusive` band cannot be disabled or collapsed; $\theta_{\text{low}} < \theta_{\text{high}}$ is strictly enforced.
* **Insufficient Validation Data Policy**: If validation data is missing, single-class, or has insufficient sample count to estimate operating points, the system explicitly returns `calibration_status="not_calibrated"` with reason `insufficient_validation_data` (or specific sub-reason). Fake or invented thresholds are strictly forbidden.
* **Score & Logit Distinction**: `raw_score` (linear model logit before sigmoid) is explicitly distinct from `calibrated_probability` (temperature-scaled probability).

## 6. Dataset Expansion & Achieved Coverage (Phase 7)
* **Corpus Totals**: 110 total audio samples across 55 connected source/speaker groups.
* **Class Distribution**: 50 Real (human) speech samples, 60 Synthetic speech samples.
* **Split Distribution**:
  * Train: 78 samples (39 Real, 39 Synthetic)
  * Validation: 12 samples (8 Real, 4 Synthetic) — satisfies calibration requirements with both classes present.
  * Test: 20 samples (3 Real, 17 Synthetic) — includes 10 strictly isolated held-out generator samples.
* **Languages Covered**: Hindi (`hi`: 36 samples), Tamil (`ta`: 44 samples), English (`en`: 30 samples).
* **Synthetic Generators**: Seen generators (`human`: 50, `elevenlabs_v3`: 50), Held-out generator (`pending_unresolved`: 10).
* **Degradations Covered**: `clean` (55 samples) and `g711_8khz` telecom profile (55 samples).
* **Slice Evaluation Statuses**:
  * `in-domain clean`: EVALUATED (50 samples)
  * `cross-generator clean`: EVALUATED (30 samples)
  * `cross-generator telecom`: EVALUATED (30 samples)
  * `language fairness (hi)`: EVALUATED (36 samples)
  * `language fairness (ta)`: EVALUATED (44 samples)
  * `language fairness (en)`: EVALUATED (30 samples)
  * `language fairness (hinglish)`: NOT EVALUABLE (`no_samples_for_language_hinglish`)
* **Explicit Limitations**:
  * Hinglish audio remains unavailable in the legitimate corpus and is reported as `not_evaluable`.
  * Advanced telecom degradations `amr_nb` and `whatsapp_opus` require a local `ffmpeg` binary; when unavailable, `g711_8khz` serves as the primary telecom degradation.

## 7. Verification
Run test suite: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`
Build Phase 7 corpus: `$env:PYTHONPATH='src'; python scripts/build_phase7_corpus.py`
Run baseline evaluation: `$env:PYTHONPATH='src'; python scripts/evaluate_phase5_baseline.py`
Evaluation report output: `reports/benchmark/phase5_baseline_eval.json`
