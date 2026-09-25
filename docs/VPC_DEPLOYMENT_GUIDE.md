# PandaMIND Audio Scoring API — Customer VPC Deployment Guide

**Version:** 1.0.0-RC1 (PRD Milestone M5)  
**Target Environment:** Customer Virtual Private Cloud (AWS VPC, Azure VNet, GCP VPC, or on-premise Kubernetes/Docker)  
**Egress Policy:** Strictly Air-Gapped / Zero Outbound Internet Access  
**Data Residency Compliance:** India Region (`ap-south-1`)

---

## 1. Architecture Overview

PandaMIND is architected as a self-contained, air-gapped synthetic speech detection microservice designed to operate entirely within an isolated customer Virtual Private Cloud (VPC) with zero external network connectivity.

```
                    Customer VPC Boundary (Air-Gapped / No Internet Gateway)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │                                                                               │
 │   Client Application (Call Verification / Fraud Screening / KYC / WhatsApp)   │
 │                                   │                                           │
 │                  POST /v1/audio/score (with X-API-Key)                        │
 │                  GET  /v1/audio/score/{job_id}                                │
 │                                   │                                           │
 │                                   ▼                                           │
 │   ┌───────────────────────────────────────────────────────────────────────┐   │
 │   │                   PandaMIND Audio Scoring Service                     │   │
 │   │                         (Port 8000 / Non-root)                        │   │
 │   ├───────────────────────────────────────────────────────────────────────┤   │
 │   │  [Security Layer]                                                     │   │
 │   │    • API-Key Authentication (`X-API-Key` / Bearer token)              │   │
 │   │    • Per-Key Operating Point Resolution (0.1%, 1%, 5% FPR)            │   │
 │   │    • Max Upload Size Guard (50 MB limit, HTTP 413)                    │   │
 │   │    • Sanitized Error Responses (Zero stack traces / path leaks)       │   │
 │   ├───────────────────────────────────────────────────────────────────────┤   │
 │   │  [In-Memory Processing Spine]                                         │   │
 │   │    • 10D Acoustic Feature Extraction (Vectorized NumPy)               │   │
 │   │    • Voice Activity Detection (RMS Energy thresholding)               │   │
 │   │    • Acoustic Condition Assessment (Bandwidth, SNR, Clipping)         │   │
 │   │    • Quality Gate Guard (<2.0s speech -> Inconclusive Override)       │   │
 │   │    • Offline Checkpoint (`m2-waveform-10d` local weights & bias)      │   │
 │   │    • Offline Platt Calibration (`cal-m3-platt-v1`)                    │   │
 │   │    • Partial-Spoof Windowing & Localization (FR-9)                    │   │
 │   │    • Provenance Safety Invariant (FR-7: Missing creds contribute 0)   │   │
 │   ├───────────────────────────────────────────────────────────────────────┤   │
 │   │  [Compliance & Observability]                                         │   │
 │   │    • Configurable Retention (PRD 7-Day Default or Zero-Retention)     │   │
 │   │    • Audio-Independent Audit Trail (No raw audio / transcripts)       │   │
 │   │    • Metrics Observability Endpoint (`GET /v1/metrics`)               │   │
 │   │    • Health & Liveness Checks (`GET /v1/health`)                      │   │
 │   └───────────────────────────────────────────────────────────────────────┘   │
 │                                                                               │
 └───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Resource Requirements & Sizing

| Component | Minimum | Recommended Production |
| :--- | :--- | :--- |
| **CPU** | 1 vCPU (x86_64 or ARM64) | 2 to 4 vCPUs |
| **Memory (RAM)** | 1 GB | 2 to 4 GB |
| **Disk Storage** | 2 GB (Container image + artifacts) | 10 GB (Local audit logs) |
| **Network** | Isolated VPC subnet (0 outbound egress) | Isolated VPC subnet (0 outbound egress) |
| **OS / Runtime** | Docker 20.10+ / Podman / Linux kernel 5.4+ | Ubuntu 22.04 LTS / Amazon Linux 2023 |

---

## 3. Quick Start: Containerized Deployment

### 3.1. Build the Production Container
In an environment with repository access, build the production image:

```bash
docker build -t pandamind-audio-scorer:1.0.0-rc1 .
```

### 3.2. Air-Gapped Image Transfer
To transfer the image into an air-gapped VPC:

```bash
# Export container image to tar archive
docker save pandamind-audio-scorer:1.0.0-rc1 -o pandamind-audio-scorer-1.0.0-rc1.tar

# Copy archive to VPC host (via scp, bastion, or private registry)
# Load on target VPC host:
docker load -i pandamind-audio-scorer-1.0.0-rc1.tar
```

### 3.3. Launch via Docker Compose
Start the service in an isolated, internal Docker network:

```bash
docker compose up -d
```

Verify service readiness:
```bash
curl -f http://localhost:8000/v1/health
```

Expected output:
```json
{
  "status": "ok",
  "service": "pandamind-audio-scoring",
  "version": "1.0.0",
  "model_version": "m2-waveform-10d",
  "offline_mode": true,
  "data_residency_region": "ap-south-1",
  "retention_policy": "7_days",
  "auth_enabled": false
}
```

---

## 4. Configuration Reference

All settings are configured via standard environment variables:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `HOST` | `0.0.0.0` | Bind IP address inside container |
| `PORT` | `8000` | Service listening port |
| `WORKERS` / `WEB_CONCURRENCY` | `1` | Number of Uvicorn worker processes |
| `SCORER_BACKEND` | `m3` | Active scoring pipeline backend (`m3` real model, `m1-stub` stub) |
| `OFFLINE_MODE` | `true` | Enforces zero outbound network egress |
| `DATA_RESIDENCY_REGION` | `ap-south-1` | Data residency compliance region (India / Mumbai) |
| `RETENTION_DAYS` | `7` | PRD retention window for job metadata |
| `ZERO_RETENTION_MODE` | `false` | When `true`, prevents persistent audio storage on disk |
| `API_KEY_AUTH_ENABLED` | `false` | When `true`, requires valid `X-API-Key` or Bearer token |
| `API_KEYS` | (Pre-configured) | JSON or comma-separated API keys with default operating points |
| `MAX_FILE_SIZE_BYTES` | `52428800` | Maximum upload size in bytes (50 MB) |
| `LOG_LEVEL` | `INFO` | Application logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 5. Security & Privacy Hardening

### 5.1. API-Key Authentication
To enable API-key authentication in production:

```bash
export API_KEY_AUTH_ENABLED=true
export API_KEYS='{"key-prod-fintech":"fpr_0.1pct","key-prod-general":"fpr_1pct","key-prod-triage":"fpr_5pct"}'
```

Protected endpoints require:
```bash
curl -X POST http://localhost:8000/v1/audio/score \
  -H "X-API-Key: key-prod-fintech" \
  -F "file=@call_recording.wav"
```

Requests with missing or invalid keys return `HTTP 401 Unauthorized`:
```json
{
  "error_code": "UNAUTHORIZED",
  "message": "Valid API key required. Provide 'X-API-Key' or 'Authorization: Bearer <key>'."
}
```

### 5.2. Per-Key Default Operating Point
Clients using `key-prod-fintech` automatically default to `fpr_0.1pct` (high-stakes blocking threshold $\tau=0.75$) if no `operating_point` is explicitly specified in the request.

### 5.3. Zero-Retention Mode
For strict compliance regimes (e.g. European GDPR, Indian DPDP Act, financial KYC), set:
```bash
export ZERO_RETENTION_MODE=true
```
- Audio is decoded in RAM and never written to persistent disk storage.
- Temporary buffers are unlinked immediately after scoring completes.
- Only privacy-safe audit metadata persists.

### 5.4. Privacy-Preserving Audit Trail
Audit records are recorded in `reports/audit/scoring_audit_trail.jsonl`:
- Record format:
  ```json
  {
    "audit_id": "aud_7a9c8b12f34e",
    "job_id": "scr_4e1a0b38c1",
    "timestamp": "2026-09-25T18:00:00Z",
    "client_key_prefix": "key-pr***",
    "operating_point": "fpr_1pct",
    "verdict_band": "likely_synthetic",
    "calibrated_probability": 0.9421,
    "speech_duration_ms": 3500,
    "quality_gate": "passed",
    "processing_time_ms": 42.5,
    "data_residency_region": "ap-south-1",
    "zero_retention_applied": true
  }
  ```
- **Guaranteed Privacy Invariant:** Audit records contain **NO raw audio, NO waveforms, and NO speech transcriptions**.

---

## 6. Observability & Monitoring

### 6.1. Metrics Endpoint (`GET /v1/metrics`)
Retrieve Prometheus-compatible operational counters and drift metrics:

```bash
curl http://localhost:8000/v1/metrics
```

Output:
```json
{
  "service": "pandamind-audio-scoring",
  "model_version": "m2-waveform-10d",
  "uptime_seconds": 3600.5,
  "requests_total": 1420,
  "jobs_completed_total": 1418,
  "jobs_failed_total": 2,
  "validation_errors_total": 5,
  "inconclusive_results_total": 12,
  "verdict_distribution": {
    "likely_synthetic": 412,
    "consistent_with_human": 994,
    "inconclusive": 12
  },
  "operating_point_distribution": {
    "fpr_0.1pct": 210,
    "fpr_1pct": 1150,
    "fpr_5pct": 58
  },
  "latency_seconds": {
    "last": 0.042,
    "mean": 0.048,
    "p50": 0.022,
    "p95": 0.057,
    "p99": 0.066
  },
  "drift_monitoring": {
    "status": "active_in_process",
    "synthetic_ratio": 0.2905,
    "inconclusive_ratio": 0.0085
  }
}
```

---

## 7. Troubleshooting & Rollback

### Healthcheck Failure
- Verify container ports: `docker ps`
- Inspect container logs: `docker logs pandamind-audio-scorer`
- Check checkpoint path: `reports/checkpoints/m2_waveform_10d_baseline.json`

### Rollback Procedure
If a deployment must be rolled back:
```bash
docker stop pandamind-audio-scorer
docker run -d --name pandamind-audio-scorer -p 8000:8000 pandamind-audio-scorer:previous-version
```
No database migration is required; the scoring engine is stateless and self-contained.
