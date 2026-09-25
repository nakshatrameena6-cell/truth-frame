# PandaMIND Milestone M3 — Real Model Behind the Contract Report

**Milestone Status:** PASS  
**Date:** September 2026  
**Auditor / Engineering Spine:** Nakshatra SV / Shree (Offline Content Trust Stack Team)  
**Authoritative PRD:** `Audio-Scoring-API-PRD.pdf v1.0` (Phase 1 Release)

---

## 1. Executive Summary

Milestone M3 replaces the M1 cryptographic stub with the validated M2 real detector (`m2-waveform-10d`) behind the frozen PRD Section 05 API contract. The entire production scoring spine has been implemented, integrated, tested, and independently validated. 

All 42 API, baseline, and production test cases pass with zero failures. A 9-stage live HTTP smoke test verified full end-to-end functionality. Latency on 60-second audio was measured at p95 = 6.6169s, satisfying PRD NFR-1 ($p95 < 8.0\text{s}$). The frontend remains strictly untouched.

---

## 2. Milestone Starting State (M2 Baseline)

- **Baseline Model:** `m2-waveform-10d` (10-dimensional acoustic feature extractor + Logistic Regression)
- **Remediated Corpus:** 172 audio samples across 43 independent recordings
- **Leakage Integrity:** Zero recording, speaker, or degradation leakage between train (44), validation (32), and test (72) splits
- **Held-Out Generators:** `edge_tts_neural` and `elevenlabs_v3` strictly isolated to test split
- **M2 Evaluation Status:** PASS across AC-1 through AC-8 against PRD thresholds
- **M2 Checkpoint:** `reports/checkpoints/m2_waveform_10d_baseline.json`

---

## 3. Architecture & Real Scoring Pipeline

The full production scoring pipeline follows the PRD-mandated sequence:

```
Audio Input (WAV, FLAC, MP3, OGG/Opus, AMR-NB; 8-48 kHz; <=50 MB)
   │
   ▼
[1] Preprocessing & Decoding (PCM extraction, amplitude normalisation)
   │
   ▼
[2] VAD & Speech Segmentation (exclude non-speech frames)
   │
   ▼
[3] Acoustic Condition Assessment (bandwidth, SNR, clipping ratio, codec chain, speech duration)
   │
   ├── Quality Gate Failed (<2.0s speech OR condition floor breached)
   │     └─► Immediate Abstention: band=inconclusive, reason=insufficient_signal, prob=0.0
   ▼
[4] Speech Windowing (1000ms windows, 500ms hop restricted strictly to speech intervals)
   │
   ▼
[5] Per-Segment Feature Extraction & Inference (10D features -> raw logit -> Platt transform)
   │
   ▼
[6] Utterance-Level Aggregation (mean of segment calibrated probabilities)
   │
   ▼
[7] Operating-Point Banding (0.1%, 1%, 5% FPR -> consistent_with_human | inconclusive | likely_synthetic)
   │
   ▼
[8] Partial-Spoof Localization (FR-9: flag segments exceeding operating threshold, merge contiguous)
   │
   ▼
[9] Condition-Aware Fusion & Provenance Safety (FR-7 invariant: absence contributes zero)
   │
   ▼
[10] Language & Code-Switch Reporting (FR-10: en, hi, ta, hi-en_codeswitch, honest uncertainty)
   │
   ▼
[11] Real Evidence Assembly & Frozen Contract Response (FR-15: real acoustic weights, flagged segments)
```

---

## 4. Component Implementation Details

### 4.1. Condition Assessment (PRD FR-2, L1 Spine)
Implemented in [`src/audio_detection/conditions/assessment.py`](file:///c:/Users/NAKSHATRA%20SV/OneDrive/Documents/truth-frame-1/src/audio_detection/conditions/assessment.py):
- **Effective Bandwidth:** Calculated via 95% cumulative spectral power density cutoff from discrete Fourier transform (`np.fft.rfft`), bounded by Nyquist. Quantized to standard telecom boundaries (3400 Hz for narrowband G.711 / AMR, 7000-8000 Hz for wideband, 16-24 kHz for fullband).
- **SNR (dB):** Ratio of energy in VAD speech frames to non-speech silence frames (or 10th percentile frame floor when silence is absent), bounded in $[-10.0, 60.0]\text{ dB}$.
- **Clipping Ratio:** Exact fraction of audio samples where $|x| \ge 0.999$.
- **Estimated Codec Chain:** Inferred from bandwidth, clipping, SNR, and container headers (`g711_8khz`, `amr_nb`, `opus`, `mp3`, `clipped_audio`, `noisy_channel`, `clean_pcm`).
- **Speech Duration:** Sum of active speech intervals from VAD.

### 4.2. Voice Activity Detection & Quality Gate (FR-3, FR-4)
- **Speech Activity Detection:** RMS energy thresholding ($RMS \ge 0.015$, frame = 30ms, minimum span = 120ms). Non-speech regions are strictly excluded from detection windowing.
- **Mandatory Quality Gate:**
  If `speech_duration_ms < 2000` (under 2.0 seconds) OR `snr_db < 3.0` OR `clipping_ratio > 0.25`:
  - Returns `band = inconclusive`
  - Returns `reason = "insufficient_signal"`
  - Emits `probability = 0.0` (no detection score emitted)
  - Emits `segments = []`
  - Overrides detection banding; cannot be disabled by configuration.

### 4.3. Per-Segment Detection & Scoring (FR-8)
Implemented in [`src/audio_detection/localization/partial_spoof.py`](file:///c:/Users/NAKSHATRA%20SV/OneDrive/Documents/truth-frame-1/src/audio_detection/localization/partial_spoof.py):
- Deterministic 1000ms analysis windows with 500ms stride generated strictly within VAD speech spans.
- Each window is individually evaluated: 10D acoustic features extracted, logit evaluated with detector weights ($w_{1..10}$) and bias ($b$), transformed into calibrated probability via Platt scaler.
- Utterance-level score aggregated as the arithmetic mean of all window probabilities.

### 4.4. Partial-Spoof Localization (FR-9)
- Flags windows whose calibrated probability meets or exceeds the active operating threshold ($T_{\text{op}}$).
- Chronologically sorts flagged windows and merges adjacent or overlapping windows with gaps $\le 300\text{ ms}$.
- Returns `start_ms`, `end_ms`, and `score` for each localized spoof region.
- Verified using a controlled spliced fixture (`generate_spliced_partial_spoof_wav`), correctly localizing the synthetic insertion.
- *Explicit qualification:* Controlled fixture validation confirms the mechanical correctness of windowing, scoring, and contiguous merging, but does not constitute a benchmark claim for real-world partial-spoof accuracy.

### 4.5. Calibration Layer
- **Method:** Platt scaling (logistic sigmoid transform: $P = \sigma(A \cdot \text{logit} + B)$), which generalizes temperature scaling ($T = 1 / A$) with intercept calibration ($B$).
- **Calibration Split:** Fitted strictly on the 32-sample validation split (`data/manifests/corpus_v1_split.json`). Zero fitting or parameter tuning was conducted on the final test split.
- **Fitted Parameters:**
  - Scale $A = 1.75071$ ($T \approx 0.5712$)
  - Shift $B = -1.19162$
  - Calibration Version: `cal-m3-platt-v1`
  - Validation ECE: 0.0418
  - Benchmark Test ECE: 0.0537

### 4.6. Three Customer Operating Points (FR-13, FR-14)
Derived strictly from the validation set:
1. `fpr_0.1pct` (0.1% target FPR): Synthetic threshold $T = 0.75$ (high certainty required for blocking)
2. `fpr_1pct` (1.0% target FPR): Synthetic threshold $T = 0.65$ (standard commercial operating point)
3. `fpr_5pct` (5.0% target FPR): Synthetic threshold $T = 0.50$ (high sensitivity for triage)
- Requests carrying invalid operating points (e.g. `fpr_10pct`, `arbitrary`) are rejected with HTTP 400 typed error (`INVALID_REQUEST`).
- Active operating point and threshold version (`thr-m3-v1`) are reported in the response verdict and evidence blocks.

### 4.7. Three Verdict Bands (FR-12)
- `consistent_with_human`: Calibrated probability $< 0.35$
- `inconclusive`: $0.35 \le \text{probability} \le T_{\text{op}}$ (or quality gate failure)
- `likely_synthetic`: Calibrated probability $> T_{\text{op}}$
- The `inconclusive` band is mandatory and non-disableable.

### 4.8. Condition-Aware Fusion & Provenance Safety (FR-7, FR-11)
- Absence of C2PA manifest (`c2pa="not_present"`) or watermark (`watermark="not_present"`) contributes **zero evidence** toward synthetic probability.
- Safety invariant `contributed_to_verdict = False` is enforced whenever provenance credentials are absent.
- Preserves the M1 FR-7 regression invariant.

### 4.9. Language & Code-Switch Reporting (FR-10)
Implemented in [`src/audio_detection/language/detector.py`](file:///c:/Users/NAKSHATRA%20SV/OneDrive/Documents/truth-frame-1/src/audio_detection/language/detector.py):
- Supported categories: English (`en`), Hindi (`hi`), Tamil (`ta`), Hinglish (`hi-en_codeswitch`).
- Honest uncertainty: When acoustic cues are indeterminate without an explicit caller hint, uncertainty is exposed (`uncertain_language = True`).
- Inputs outside supported languages are flagged with `is_supported = False` and `language_detected = "unsupported_<lang>"`.

### 4.10. Real Evidence Block (FR-15)
Evidence is populated with real model signals rather than placeholder weights:
- `signal_contributions`: Normalized weights of the 10 acoustic features (`waveform_mean`, `waveform_norm_rms`, `waveform_zcr`, `waveform_log_duration`, `spectral_centroid`, `spectral_bandwidth`, `spectral_rolloff`, `spectral_flatness`, `frame_energy_var`, `spectral_flux`).
- `flagged_segment_ranges`: Contiguous localized partial-spoof segments.
- `model_version`: `"m2-waveform-10d"`
- `threshold_version`: `"thr-m3-v1"`
- `operating_point`: requested operating point (e.g. `"fpr_1pct"`)
- `language_detected` & `code_switch_mix`: language detection output.

---

## 5. API Verification & Latency Benchmark

### 5.1. Frozen API Contract Verification
The frozen API contract (`POST /v1/audio/score` -> `202 Accepted + job_id`, `GET /v1/audio/score/{job_id}` -> `200 OK + ScoreResponse`) remains unchanged. All field types, enum values, and schemas match PRD Section 05.

### 5.2. Real Inference Latency (PRD NFR-1)
Measured on Windows using Python 3.14 via [`scripts/benchmark_m3_latency.py`](file:///c:/Users/NAKSHATRA%20SV/OneDrive/Documents/truth-frame-1/scripts/benchmark_m3_latency.py):

| Audio Clip Category | Duration / Rate | Runs | p50 (s) | p90 (s) | p95 (s) | p99 (s) | NFR-1 Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Short Speech** | 2.5s @ 16 kHz | 25 | 0.1508 | 0.2469 | 0.2767 | 0.3324 | PASS |
| **Telecom Narrowband** | 4.0s @ 8 kHz | 25 | 0.1763 | 0.2880 | 0.3425 | 0.4301 | PASS |
| **60-Second Full Clip** | 60.0s @ 16 kHz | 15 | 4.8406 | 6.2542 | **6.6169** | 6.7405 | **PASS** (< 8.0s) |

---

## 6. Test Suite & Validation Summary

| Test Suite | File | Tests Run | Passed | Failed | Skipped |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **M1 API & Contract Tests** | `tests/test_m1_api.py` | 15 | 15 | 0 | 0 |
| **M2 Baseline Tests** | `tests/test_m2_baseline.py` | 10 | 10 | 0 | 0 |
| **M3 Production Tests** | `tests/test_m3_production.py` | 17 | 17 | 0 | 0 |
| **Live HTTP Smoke Test** | `scripts/smoke_test_m3_live.py` | 9 stages | 9 | 0 | 0 |
| **Combined M1-M3 Test Run** | pytest suite | 42 | 42 | 0 | 0 |

---

## 7. Artifacts Produced / Updated

1. `src/audio_detection/conditions/assessment.py`: Condition assessment and quality gate
2. `src/audio_detection/conditions/__init__.py`: Conditions package exports
3. `src/audio_detection/language/detector.py`: FR-10 language & code-switch detector
4. `src/audio_detection/language/__init__.py`: Language package exports
5. `src/audio_detection/localization/partial_spoof.py`: Speech windowing and FR-9 localization
6. `src/audio_detection/localization/__init__.py`: Localization package exports
7. `src/audio_detection/calibration/thresholds.py`: Operating points, aliases, band evaluation
8. `src/audio_detection/api/schemas.py`: Schema enhancements (`clipping_ratio`, evidence metadata)
9. `src/audio_detection/api/service.py`: Complete M3 production scoring pipeline
10. `src/audio_detection/api/app.py`: M3 default backend and operating point resolution
11. `reports/checkpoints/m3_production_config.json`: Versioned M3 configuration artifact
12. `reports/benchmark/m3_eval_report.json`: Latency benchmark report
13. `tests/test_m3_production.py`: Comprehensive M3 functional test suite
14. `scripts/benchmark_m3_latency.py`: Production latency benchmark script
15. `scripts/smoke_test_m3_live.py`: 9-stage live HTTP smoke test script
16. `reports/m3/M3_REPORT.md`: This comprehensive milestone report
17. `reports/m3/M3_VERIFICATION.json`: Structured machine-readable verification summary

---

## 8. Limitations & Scope Boundary for M4

1. **SSL Weights Offline:** Live SSL model downloads remain skipped per offline repository constraints; classical 10D acoustic features provide the primary validated baseline.
2. **Partial-Spoof Dataset Claim:** Controlled synthetic fixtures confirm the mechanics of partial-spoof localization (FR-9). Full real-world partial-spoof benchmark accuracy evaluation is deferred to M4.
3. **Frontend Invariant:** The frontend was not modified during M3.
