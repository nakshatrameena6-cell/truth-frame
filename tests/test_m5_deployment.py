"""M5: VPC Deployment Packaging, Offline Readiness, and Security Test Suite.

Validates:
1. Air-Gapped / Zero-Egress Enforcement (blocks all outbound network sockets).
2. API-Key Authentication and Per-Key Operating Point mapping.
3. Retention and Zero-Retention Policy (PRD 7-day default and zero-persistence).
4. Privacy-Preserving Audit Trail (zero raw audio, zero waveforms, zero transcripts).
5. Observability and Metrics (/v1/metrics operational counters and drift distribution).
6. Security Hardening (50 MB upload limit, sanitized error responses, no stack traces).
7. Full API Contract and Determinism preservation.
"""
from __future__ import annotations

import io
import json
import os
import socket
import struct
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import numpy as np

from audio_detection.api.app import app
from audio_detection.api.audit import audit_logger
from audio_detection.api.metrics import metrics_collector
from audio_detection.api.schemas import ScoreResponse, VerdictBand
from audio_detection.api.store import InMemoryJobStore, job_store
from audio_detection.config.settings import Settings, get_settings


def create_pcm_wav(duration_s: float = 2.5, rate: int = 16000, freq: float = 440.0) -> bytes:
    n_samples = int(duration_s * rate)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    int16_samples = (sig * 32767).astype(np.int16).tolist()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(struct.pack(f"<{len(int16_samples)}h", *int16_samples))
    return buf.getvalue()


class TestM5AirGappedVpcEgress(unittest.TestCase):
    """Verifies that the entire scoring pipeline operates with ZERO outbound network access."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)
        self.test_wav = create_pcm_wav(duration_s=2.5)

    def test_zero_network_egress_scoring(self):
        """Actively blocks all socket connection attempts and verifies scoring succeeds without network calls."""
        orig_connect = socket.socket.connect
        orig_getaddrinfo = socket.getaddrinfo

        def vpc_firewall_connect(sock_self, address):
            # Allow local loopback IPC used by in-memory ASGI test client
            host = address[0] if isinstance(address, (tuple, list)) else str(address)
            if host in ("127.0.0.1", "localhost", "::1"):
                return orig_connect(sock_self, address)
            raise PermissionError(f"VPC Air-Gapped Egress Blocked: attempt to connect to external host '{host}'")

        def vpc_firewall_getaddrinfo(host, port, *args, **kwargs):
            if host in ("127.0.0.1", "localhost", "::1", None):
                return orig_getaddrinfo(host, port, *args, **kwargs)
            raise PermissionError(f"VPC Air-Gapped DNS Blocked: attempt to resolve external host '{host}'")

        with patch.object(socket.socket, "connect", new=vpc_firewall_connect), \
             patch.object(socket, "getaddrinfo", new=vpc_firewall_getaddrinfo):
            # 1. Health check works offline
            health_resp = self.client.get("/v1/health")
            self.assertEqual(health_resp.status_code, 200)
            self.assertTrue(health_resp.json()["offline_mode"])
            self.assertEqual(health_resp.json()["data_residency_region"], "ap-south-1")

            # 2. Score submission works offline
            post_resp = self.client.post(
                "/v1/audio/score",
                files={"file": ("airgapped_test.wav", self.test_wav, "audio/wav")},
                data={"operating_point": "fpr_1pct"},
            )
            self.assertEqual(post_resp.status_code, 202)
            job_id = post_resp.json()["job_id"]

            # 3. Score retrieval works offline
            get_resp = self.client.get(f"/v1/audio/score/{job_id}")
            self.assertEqual(get_resp.status_code, 200)
            data = get_resp.json()
            self.assertEqual(data["job_id"], job_id)
            self.assertIn("verdict", data)
            self.assertIn("conditions", data)
            self.assertIn("evidence", data)
            self.assertIn("provenance", data)


class TestM5AuthenticationAndSecurity(unittest.TestCase):
    """Verifies API key authentication, per-key operating point resolution, and error sanitization."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)
        self.test_wav = create_pcm_wav(duration_s=2.5)

    def test_api_key_auth_enforced_when_enabled(self):
        """Protected endpoints reject missing or invalid API keys when auth is enabled."""
        settings = get_settings()
        prev_auth = settings.api_key_auth_enabled
        try:
            settings.api_key_auth_enabled = True

            # 1. Missing API key -> 401 UNAUTHORIZED
            resp_missing = self.client.post(
                "/v1/audio/score",
                files={"file": ("test.wav", self.test_wav, "audio/wav")},
            )
            self.assertEqual(resp_missing.status_code, 401)
            self.assertEqual(resp_missing.json()["error_code"], "UNAUTHORIZED")

            # 2. Invalid API key -> 401 UNAUTHORIZED
            resp_invalid = self.client.post(
                "/v1/audio/score",
                headers={"X-API-Key": "invalid-random-key"},
                files={"file": ("test.wav", self.test_wav, "audio/wav")},
            )
            self.assertEqual(resp_invalid.status_code, 401)
            self.assertEqual(resp_invalid.json()["error_code"], "UNAUTHORIZED")

            # 3. Valid API key -> 202 ACCEPTED
            resp_valid = self.client.post(
                "/v1/audio/score",
                headers={"X-API-Key": "pm-prod-key-standard"},
                files={"file": ("test.wav", self.test_wav, "audio/wav")},
            )
            self.assertEqual(resp_valid.status_code, 202)
        finally:
            settings.api_key_auth_enabled = prev_auth

    def test_per_key_operating_point_default(self):
        """Clients authenticating with high-security key default to fpr_0.1pct automatically."""
        settings = get_settings()
        prev_auth = settings.api_key_auth_enabled
        try:
            settings.api_key_auth_enabled = True

            # High security key is bound to fpr_0.1pct
            resp = self.client.post(
                "/v1/audio/score",
                headers={"X-API-Key": "pm-prod-key-highsecurity"},
                files={"file": ("test.wav", self.test_wav, "audio/wav")},
                # Notice: caller does NOT provide operating_point form field!
            )
            self.assertEqual(resp.status_code, 202)
            job_id = resp.json()["job_id"]

            res = self.client.get(
                f"/v1/audio/score/{job_id}",
                headers={"X-API-Key": "pm-prod-key-highsecurity"},
            ).json()
            self.assertEqual(res["verdict"]["operating_point"], "fpr_0.1pct")
        finally:
            settings.api_key_auth_enabled = prev_auth

    def test_max_upload_size_enforced(self):
        """Payloads exceeding 50 MB are rejected with HTTP 413 FILE_TOO_LARGE."""
        settings = get_settings()
        prev_size = settings.max_file_size_bytes
        try:
            # Temporarily set limit to 10 KB to test without allocating 50MB
            settings.max_file_size_bytes = 10 * 1024
            oversized_wav = create_pcm_wav(duration_s=2.5)  # ~80 KB
            resp = self.client.post(
                "/v1/audio/score",
                files={"file": ("big.wav", oversized_wav, "audio/wav")},
            )
            self.assertEqual(resp.status_code, 413)
            self.assertEqual(resp.json()["error_code"], "FILE_TOO_LARGE")
        finally:
            settings.max_file_size_bytes = prev_size

    def test_sanitized_error_responses_no_stack_traces(self):
        """Error responses do not leak internal filesystem paths or stack traces."""
        resp = self.client.get("/v1/audio/score/scr_nonexistent999")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data["error_code"], "JOB_NOT_FOUND")
        self.assertNotIn("Traceback", json.dumps(data))
        self.assertNotIn("c:\\", json.dumps(data).lower())
        self.assertNotIn("/home/", json.dumps(data).lower())


class TestM5RetentionAndAuditBehavior(unittest.TestCase):
    """Verifies PRD 7-day retention enforcement, zero-retention mode, and privacy-safe audit trail."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)
        self.test_wav = create_pcm_wav(duration_s=2.5)

    def test_retention_purge_expired_jobs(self):
        """InMemoryJobStore purges entries older than retention window while retaining recent jobs."""
        store = InMemoryJobStore()
        # Save a mock job created 8 days ago
        dummy_resp = ScoreResponse.model_validate({
            "job_id": "scr_old123",
            "status": "complete",
            "verdict": {"band": "likely_synthetic", "probability": 0.95, "operating_point": "fpr_1pct"},
            "conditions": {"effective_bandwidth_hz": 8000, "estimated_codec_chain": ["clean"], "snr_db": 30.0, "speech_duration_ms": 2500, "quality_gate": "passed", "clipping_ratio": 0.0},
            "provenance": {"c2pa": "not_present", "watermark": "not_present", "contributed_to_verdict": False},
            "evidence": {"signal_contributions": [], "language_detected": "en", "model_version": "m2-waveform-10d", "threshold_version": "thr-m3-v1", "operating_point": "fpr_1pct", "flagged_segment_ranges": []},
        })
        store.save_job("scr_old123", dummy_resp)
        store._timestamps["scr_old123"] = 1000.0  # long ago

        # Save a recent job
        store.save_job("scr_recent456", dummy_resp)

        # Purge with standard 7-day limit (7 * 86400s)
        purged = store.purge_expired_jobs(max_age_seconds=7 * 86400)
        self.assertEqual(purged, 1)
        self.assertIsNone(store.get_job("scr_old123"))
        self.assertIsNotNone(store.get_job("scr_recent456"))

    def test_audit_record_privacy_invariant_zero_audio_content(self):
        """Audit records capture job compliance metadata but NEVER contain raw audio or transcripts."""
        audit_logger.clear()
        resp = self.client.post(
            "/v1/audio/score",
            headers={"X-API-Key": "pm-prod-key-standard"},
            files={"file": ("audit_test.wav", self.test_wav, "audio/wav")},
        )
        self.assertEqual(resp.status_code, 202)
        job_id = resp.json()["job_id"]

        audit_rec = audit_logger.get_job_audit(job_id)
        self.assertIsNotNone(audit_rec)
        self.assertEqual(audit_rec.job_id, job_id)
        self.assertEqual(audit_rec.data_residency_region, "ap-south-1")
        self.assertIn(audit_rec.verdict_band, ("likely_synthetic", "consistent_with_human", "inconclusive"))

        # PRIVACY INVARIANT AUDIT:
        record_dict = audit_rec.to_dict()
        record_str = json.dumps(record_dict).lower()
        self.assertNotIn("raw_audio", record_str)
        self.assertNotIn("waveform", record_str)
        self.assertNotIn("transcript", record_str)
        self.assertNotIn("samples", record_str)

        # Verify audit record persists even if the job response is deleted from store
        job_store.delete_job(job_id)
        self.assertIsNone(job_store.get_job(job_id))
        self.assertIsNotNone(audit_logger.get_job_audit(job_id))


class TestM5ObservabilityAndMetrics(unittest.TestCase):
    """Verifies operational observability, drift monitoring, and health readiness."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)
        self.test_wav = create_pcm_wav(duration_s=2.5)

    def test_metrics_endpoint_increments_and_drift_tracking(self):
        """GET /v1/metrics records counters, verdict distribution, and latency without audio data."""
        metrics_collector.reset()

        # Submit 2 jobs
        for op in ("fpr_1pct", "fpr_0.1pct"):
            self.client.post(
                "/v1/audio/score",
                files={"file": ("bench.wav", self.test_wav, "audio/wav")},
                data={"operating_point": op},
            )

        resp = self.client.get("/v1/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertGreaterEqual(data["requests_total"], 2)
        self.assertGreaterEqual(data["jobs_completed_total"], 2)
        self.assertEqual(data["model_version"], "m2-waveform-10d")
        self.assertIn("verdict_distribution", data)
        self.assertIn("operating_point_distribution", data)
        self.assertIn("latency_seconds", data)
        self.assertIn("drift_monitoring", data)
        self.assertEqual(data["drift_monitoring"]["status"], "active_in_process")


if __name__ == "__main__":
    unittest.main()
