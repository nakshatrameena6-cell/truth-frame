# PandaMIND Full Project Specification (Phases 0–8)

## Scope
PandaMIND is an offline Python foundation for synthetic-audio detection work. Phase 3 establishes a versioned, deterministic evaluation/benchmark specification (`phase3-v1`). Phase 5 executes baseline evaluation of the trained Phase 4 detector model across defined benchmark slices. Phase 6 implements deterministic calibration and thresholding logic. Phase 7 expands the dataset infrastructure to provide representative validation and evaluation splits. Phase 8 completes final acceptance validation and release readiness assessment.

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

### PRD Acceptance Targets
* AC-1: In-domain clean EER <= 5%
* AC-2: Cross-generator clean EER <= 15%
* AC-3: Cross-generator telecom EER <= 25%
* AC-4: TPR @ 1% FPR >= 70%
* AC-5: ECE <= 0.05
* AC-6: Inconclusive/abstention share <= 20%
* AC-7: Language fairness max/min EER ratio <= 2.0x
* AC-8: Beat evaluated public baselines at 1% FPR

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

## 7. Final Acceptance Validation & Release Readiness (Phase 8)
* **Calibration State**: Calibrated on validation split (`temperature=1.0`, `operating_point_thresholds={"fpr_0.1%": 0.386795, "fpr_1%": 0.386795, "fpr_5%": 0.386795}`, `low_threshold=0.320174`, `high_threshold=0.386795`).
* **PRD Acceptance Criteria Assessment**:
  * **AC-1** (In-domain clean EER <= 5%): **FAIL** (Measured EER: 50.0%)
  * **AC-2** (Cross-generator clean EER <= 15%): **FAIL** (Measured EER: 62.0%)
  * **AC-3** (Cross-generator telecom EER <= 25%): **FAIL** (Measured EER: 60.0%)
  * **AC-4** (TPR >= 70% @ 1% FPR): **FAIL** (Measured TPR @ 1% FPR: 0.0%)
  * **AC-5** (ECE <= 0.05): **FAIL** (Measured ECE: 14.1% – 31.5%)
  * **AC-6** (Inconclusive share <= 20%): **FAIL** (Measured Inconclusive Share: 81.82%)
  * **AC-7** (Language fairness max/min EER ratio <= 2.0x): **PASS** (Ratio: 0.50 / 0.50 = 1.0x <= 2.0x)
  * **AC-8** (Beat evaluated public baselines @ 1% FPR): **NOT EVALUABLE** (No evaluated public baseline implementations available)
* **Release-Readiness Conclusion**: **NOT RELEASE-READY**. While software infrastructure, split management, held-out generator protection, calibration, thresholding, and benchmarking are 100% verified and passing all 30 unit tests, baseline model accuracy targets require scaling data and architecture in future work.

## 8. Verification
Run test suite: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`
Build Phase 7 corpus: `$env:PYTHONPATH='src'; python scripts/build_phase7_corpus.py`
Run baseline evaluation: `$env:PYTHONPATH='src'; python scripts/evaluate_phase5_baseline.py`
Evaluation report output: `reports/benchmark/phase5_baseline_eval.json`
