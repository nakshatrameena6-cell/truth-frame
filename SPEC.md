# PandaMIND Full Project Specification

## Scope
PandaMIND is an offline Python foundation for synthetic-audio detection work. Phase 3 establishes a versioned, deterministic evaluation/benchmark specification (`phase3-v1`). Phase 5 executes baseline evaluation of the trained Phase 4 detector model across defined benchmark slices. Phase 6 implements deterministic calibration and thresholding logic. Corpus Integrity Remediation invalidates previous synthetic relabelings and establishes permanent duplicate-content validation guards.

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

## 6. Corpus Integrity Remediation & Result Invalidation
* **Audit Finding**: An independent audit confirmed that previous Phase 7/8 dataset expansion scripts (`build_phase7_corpus.py`) relabeled human audio recordings as synthetic speech and manufactured speaker IDs, contaminating the corpus.
* **Invalidation of Previous Results**: All metrics, benchmark reports, and performance figures from previous Phase 8 evaluation on contaminated data are **INVALIDATED**.
* **Permanent Integrity Guard**: `validate_corpus_audio` in `manifest.py` now enforces byte-content SHA-256 hashing to reject any byte-identical files with conflicting `is_synthetic` or `generator` labels (`conflicting_label_duplicate` and `conflicting_generator_duplicate`).
* **Verified Authentic Corpus**:
  * Total verified samples: 6 (4 Real human speech, 2 Synthetic speech).
  * Hindi (`hi`): 2 Real human speech samples (`hi_convo_001` clean & `g711_8khz`).
  * Tamil (`ta`): 2 Real human speech samples (`ta_convo_001` clean & `g711_8khz`).
  * English (`en`): 2 Synthetic speech samples (`elevenlabs_v3_mark` clean & `g711_8khz`).
  * All 6 verified samples belong to 3 connected source/speaker groups and hash into the `train` split.
* **Current System Status**:
  * Validation split count: 0 samples $\implies$ Calibration status returns `not_calibrated` with reason `insufficient_validation_data`.
  * Slices requiring validation or held-out synthetic data remain explicitly `not_evaluable`.
  * Hinglish, AMR-NB, WhatsApp/Opus, and independent held-out synthetic datasets are unavailable and not fabricated.

## 7. Verification
Run test suite: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`
Run baseline evaluation: `$env:PYTHONPATH='src'; python scripts/evaluate_phase5_baseline.py`
Evaluation report output: `reports/benchmark/phase5_baseline_eval.json`
