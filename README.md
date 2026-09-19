# PandaMIND — Audio Scoring API

Content Trust Stack Audio Scoring API foundation and offline synthetic-speech detector.

## Milestone M1: Contract + Stub End-to-End API

Milestone M1 establishes the authoritative API contract specified in `Audio-Scoring-API-PRD.pdf` v1.0, backed by a deterministic, offline stub scoring engine (`m1-stub`).

> **Note on Stub Scorer**: The M1 backend returns deterministic placeholder scores derived via cryptographic SHA-256 hashing of input audio bytes. It is explicitly a stub to freeze the API contract for client integration and testing; it does NOT represent real model detection performance. Real ML inference is scheduled for Milestone M3.

---

### Installation

Install in editable mode with standard runtime dependencies:

```bash
pip install -e .
```

To include testing tools (`pytest`, `httpx`):

```bash
pip install -e ".[test]"
```

---

### Starting the Backend

Start the FastAPI application via Uvicorn:

```bash
python -m uvicorn audio_detection.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI documentation is available at:
* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`

---

### API Contract

#### 1. Submit Audio for Scoring
```http
POST /v1/audio/score
Content-Type: multipart/form-data
```

**Parameters**:
* `file` or `audio` (required): Audio file binary (WAV, FLAC, MP3, OGG, Opus, AMR-NB, up to 50 MB).
* `operating_point` (optional, default `"fpr_1pct"`): Target false-positive rate (`"fpr_0.1pct"`, `"fpr_1pct"`, `"fpr_5pct"`).
* `language` (optional): BCP-47 or dialect hint (e.g. `"hi"`, `"ta"`, `"en"`, `"hi-en_codeswitch"`).

**Response (`HTTP 202 Accepted`)**:
```json
{
  "job_id": "scr_01JQ8F2M4K",
  "status": "complete"
}
```

#### 2. Retrieve Scoring Result and Evidence
```http
GET /v1/audio/score/{job_id}
Accept: application/json
```

**Response (`HTTP 200 OK`)**:
```json
{
  "job_id": "scr_01JQ8F2M4K",
  "status": "complete",
  "verdict": {
    "band": "likely_synthetic",
    "probability": 0.87,
    "operating_point": "fpr_1pct",
    "reason": null
  },
  "segments": [
    { "start_ms": 4120, "end_ms": 6890, "score": 0.94 },
    { "start_ms": 11040, "end_ms": 12300, "score": 0.81 }
  ],
  "conditions": {
    "effective_bandwidth_hz": 3400,
    "estimated_codec_chain": ["amr_nb", "opus"],
    "snr_db": 17.2,
    "speech_duration_ms": 18400,
    "quality_gate": "passed"
  },
  "provenance": {
    "c2pa": "not_present",
    "watermark": "not_present",
    "contributed_to_verdict": false
  },
  "evidence": {
    "signal_contributions": [
      { "signal": "ssl_frontend", "weight": 0.62 },
      { "signal": "waveform_branch", "weight": 0.24 },
      { "signal": "prosody_rhythm", "weight": 0.14 }
    ],
    "language_detected": "hi-en_codeswitch",
    "model_version": "m1-stub",
    "threshold_version": "thr-2026-09-01"
  }
}
```

#### 3. Health Check
```http
GET /health
```
```json
{
  "status": "ok",
  "version": "1.0.0",
  "model_version": "m1-stub"
}
```

---

### Error Responses

Errors conform to a consistent typed schema:

```json
{
  "error_code": "UNSUPPORTED_AUDIO",
  "message": "Unsupported audio format '.txt'. Expected one of: ['.amr', '.flac', '.mp3', '.ogg', '.opus', '.wav'].",
  "details": {
    "supported_formats": [".amr", ".flac", ".mp3", ".ogg", ".opus", ".wav"],
    "received_format": ".txt"
  }
}
```

Common error codes:
* `MISSING_AUDIO` (`400`): Request missing audio file upload.
* `EMPTY_AUDIO` (`400`): Uploaded audio file has 0 bytes.
* `INVALID_REQUEST` (`400`): Malformed form parameters or unsupported operating point.
* `UNSUPPORTED_AUDIO` (`415`): File format not supported by PRD FR-1.
* `FILE_TOO_LARGE` (`413`): Uploaded file exceeds 50 MB limit.
* `JOB_NOT_FOUND` (`404`): Requested `job_id` does not exist.
* `INTERNAL_ERROR` (`500`): Unhandled internal server error (never leaks stack traces).

---

### Deterministic Behavior & Provenance Safety (FR-7)

1. **Determinism**: The stub scorer computes a SHA-256 hash of the audio content to produce identical probabilities, verdicts, and conditions across repeated runs.
2. **Provenance Safety (FR-7)**: Missing provenance credentials (`c2pa: "not_present"`, `watermark: "not_present"`) strictly never contribute to synthetic probabilities or verdicts (`contributed_to_verdict: false`). This is guaranteed by automated build regression tests.

---

### Running Tests and Smoke Test

Run the full M1 API test suite:
```bash
python -m pytest tests/test_m1_api.py -v
```

Run the end-to-end live HTTP smoke test:
```bash
python scripts/smoke_test_m1.py
```
