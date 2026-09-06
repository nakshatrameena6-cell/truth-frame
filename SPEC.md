# PandaMIND Phase 3 Evaluation/Benchmark Specification

## Scope
PandaMIND is an offline Python foundation for future synthetic-audio detection work. Phase 3 establishes a versioned, deterministic evaluation/benchmark specification.

## 1. Benchmark
* **Version**: `phase3-v1`
* **Languages**: Hindi (`hi`), Tamil (`ta`), Hinglish (`hinglish`)
* **Classes**: Real, Synthetic
* **Generators**: Seen generators (train/val), Held-out generators (test)
* **Degradation**: `clean`, `g711_8khz`, `amr_nb`, `whatsapp_opus`
* **Splits**: Train, Validation, Test

## 2. Held-out Generators
One authoritative configuration is defined in `src/audio_detection/config/held_out_generators.json`.
* Currently unavailable held-out generators are marked as `pending_unresolved`.
* **Enforcement**:
  * Held-out generators are **forbidden** in train.
  * Held-out generators are **forbidden** in validation.
  * Held-out generators are **allowed** in test.
* Existing source/speaker leakage protection remains enforced.

## 3. Metrics
The following metrics are frozen:
* EER (Equal Error Rate)
* TPR (True Positive Rate) @ 0.1% FPR
* TPR @ 1% FPR
* TPR @ 5% FPR
* ECE (Expected Calibration Error) for the top label

### Future Evaluation Slices
Future evaluation runs will define the following slices:
* **in-domain clean**: Seen generators, clean degradation.
* **cross-generator clean**: Held-out generators, clean degradation.
* **cross-generator telecom**: Held-out generators, telecom degradations (e.g., g711_8khz, amr_nb, whatsapp_opus).
* **language fairness**: Performance breakdown across Hindi, Tamil, and Hinglish.

### PRD Acceptance Targets (Future Targets)
*These are targets for future trained models, not current phase0-untrained results.*
* In-domain clean TPR @ 1% FPR: > 95%
* Cross-generator clean TPR @ 1% FPR: > 90%
* Cross-generator telecom TPR @ 1% FPR: > 85%
* ECE: < 0.05
* EER: < 5%

## 4. Benchmark Validity
* No train/test leakage of data.
* No speaker/source leakage across splits.
* Held-out generators remain strictly isolated.
* **Unavailable slices are reported as `unavailable`, not zero.**
* **Metrics calculation requires real labeled data** (both positive and negative classes).

## 5. Verification
Run `PYTHONPATH=src python -m unittest discover -s tests -v` from the repository root. Tests are deterministic and use generated in-memory WAV bytes only.
