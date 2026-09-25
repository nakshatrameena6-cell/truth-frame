"""Automated contract, schema, and behavior tests for PRD Milestone M1.

Tests cover:
  1. Service startup and health endpoint
  2. POST /v1/audio/score (HTTP 202, job_id, job status)
  3. GET /v1/audio/score/{job_id} (HTTP 200, complete PRD-shaped response)
  4. Typed error handling (missing audio, empty audio, unsupported audio, oversized file, unknown job, invalid OP)
  5. Deterministic scoring behavior across identical inputs (SHA-256 based)
  6. Provenance safety regression test (FR-7 invariant: absence is never synthetic evidence)
  7. Schema validation against PRD models
  8. M1 stub latency measurement
"""
from __future__ import annotations

import io
import os
import struct
import time
import unittest
import wave
from typing import List

from fastapi.testclient import TestClient

from audio_detection.api.app import app
from audio_detection.api.schemas import (
    ApiErrorResponse,
    OperatingPoint,
    ScoreJobResponse,
    ScoreResponse,
    VerdictBand,
)
from audio_detection.api.store import job_store
from audio_detection.api.stub import STUB_MODEL_VERSION, STUB_THRESHOLD_VERSION, compute_stub_score


def generate_test_wav(samples: List[int], rate: int = 16000) -> bytes:
    """Generates valid in-memory PCM WAV bytes for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


class M1BaseTestCase(unittest.TestCase):
    """Base test case ensuring M1 tests run under the M1 stub configuration."""

    def setUp(self):
        super().setUp()
        self._prev_backend = os.environ.get("SCORER_BACKEND")
        os.environ["SCORER_BACKEND"] = "m1-stub"
        self.client = TestClient(app)

    def tearDown(self):
        if self._prev_backend is not None:
            os.environ["SCORER_BACKEND"] = self._prev_backend
        else:
            os.environ.pop("SCORER_BACKEND", None)
        super().tearDown()


class TestM1StartupAndHealth(M1BaseTestCase):
    """Verifies clean backend import, app initialization, and health check."""

    def test_health_endpoint(self):
        """GET /health must return HTTP 200 with status=ok and model_version=m1-stub."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("model_version"), STUB_MODEL_VERSION)

    def test_v1_health_endpoint(self):
        """GET /v1/health must also return HTTP 200."""
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ok")


class TestM1ScoreEndpoints(M1BaseTestCase):
    """Verifies POST /v1/audio/score and GET /v1/audio/score/{job_id} contracts."""

    def setUp(self):
        super().setUp()
        job_store.clear()
        self.sample_wav = generate_test_wav([1000, -1000, 500, -500] * 4000, rate=16000)

    def test_post_valid_audio_returns_202_accepted(self):
        """POST /v1/audio/score with valid WAV returns 202 Accepted and job_id."""
        response = self.client.post(
            "/v1/audio/score",
            files={"file": ("test_speech.wav", self.sample_wav, "audio/wav")},
            data={"operating_point": "fpr_1pct"},
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertTrue(data["job_id"].startswith("scr_"))
        self.assertEqual(data.get("status"), "complete")

        # Validate against Pydantic schema
        job_resp = ScoreJobResponse.model_validate(data)
        self.assertIsNotNone(job_resp.job_id)

    def test_post_with_audio_field_name_returns_202(self):
        """POST /v1/audio/score also accepts 'audio' as the form field name."""
        response = self.client.post(
            "/v1/audio/score",
            files={"audio": ("call_sample.wav", self.sample_wav, "audio/wav")},
            data={"operating_point": "fpr_1pct"},
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn("job_id", data)

    def test_get_completed_job_returns_complete_prd_response(self):
        """GET /v1/audio/score/{job_id} returns complete PRD-shaped verdict and evidence."""
        # 1. Submit audio
        post_resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("test_recording.wav", self.sample_wav, "audio/wav")},
            data={"operating_point": "fpr_1pct", "language": "hi-en_codeswitch"},
        )
        self.assertEqual(post_resp.status_code, 202)
        job_id = post_resp.json()["job_id"]

        # 2. Retrieve job result
        get_resp = self.client.get(f"/v1/audio/score/{job_id}")
        self.assertEqual(get_resp.status_code, 200)
        result = get_resp.json()

        # 3. Validate against Pydantic ScoreResponse
        score_resp = ScoreResponse.model_validate(result)

        # 4. Check PRD Section 05 Top-Level Fields
        self.assertEqual(score_resp.job_id, job_id)
        self.assertEqual(score_resp.status.value, "complete")

        # Verdict checks
        self.assertIn(score_resp.verdict.band, [
            VerdictBand.CONSISTENT_WITH_HUMAN,
            VerdictBand.INCONCLUSIVE,
            VerdictBand.LIKELY_SYNTHETIC,
        ])
        self.assertGreaterEqual(score_resp.verdict.probability, 0.0)
        self.assertLessEqual(score_resp.verdict.probability, 1.0)
        self.assertEqual(score_resp.verdict.operating_point, "fpr_1pct")
        if score_resp.verdict.band == VerdictBand.INCONCLUSIVE:
            self.assertIsNotNone(score_resp.verdict.reason)
        else:
            self.assertIsNone(score_resp.verdict.reason)

        # Conditions checks (FR-2)
        self.assertGreater(score_resp.conditions.effective_bandwidth_hz, 0)
        self.assertIsInstance(score_resp.conditions.estimated_codec_chain, list)
        self.assertGreater(score_resp.conditions.snr_db, 0.0)
        self.assertGreaterEqual(score_resp.conditions.speech_duration_ms, 2000)
        self.assertIn(score_resp.conditions.quality_gate, ["passed", "failed"])

        # Provenance checks (FR-7)
        self.assertEqual(score_resp.provenance.c2pa, "not_present")
        self.assertEqual(score_resp.provenance.watermark, "not_present")
        self.assertFalse(score_resp.provenance.contributed_to_verdict)

        # Evidence checks (FR-15)
        self.assertGreater(len(score_resp.evidence.signal_contributions), 0)
        self.assertEqual(score_resp.evidence.language_detected, "hi-en_codeswitch")
        self.assertEqual(score_resp.evidence.model_version, STUB_MODEL_VERSION)
        self.assertEqual(score_resp.evidence.threshold_version, STUB_THRESHOLD_VERSION)


class TestM1ErrorHandling(M1BaseTestCase):
    """Verifies typed error responses across all failure modes (PRD / Prompt Section 16)."""

    def setUp(self):
        super().setUp()

    def test_missing_audio_returns_400_missing_audio(self):
        """Submitting score request without audio file returns HTTP 400 MISSING_AUDIO."""
        response = self.client.post("/v1/audio/score", data={"operating_point": "fpr_1pct"})
        self.assertEqual(response.status_code, 400)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "MISSING_AUDIO")
        self.assertIn("missing", err.message.lower())

    def test_empty_audio_returns_400_empty_audio(self):
        """Submitting 0-byte audio file returns HTTP 400 EMPTY_AUDIO."""
        response = self.client.post(
            "/v1/audio/score",
            files={"file": ("empty.wav", b"", "audio/wav")},
        )
        self.assertEqual(response.status_code, 400)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "EMPTY_AUDIO")

    def test_unsupported_audio_extension_returns_415_unsupported_audio(self):
        """Submitting an unsupported file type (e.g. .txt, .exe, .py) returns HTTP 415."""
        response = self.client.post(
            "/v1/audio/score",
            files={"file": ("document.txt", b"Hello text content", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "UNSUPPORTED_AUDIO")

    def test_invalid_operating_point_returns_400_invalid_request(self):
        """Submitting invalid operating point returns HTTP 400 INVALID_REQUEST."""
        wav = generate_test_wav([100] * 100)
        response = self.client.post(
            "/v1/audio/score",
            files={"file": ("speech.wav", wav, "audio/wav")},
            data={"operating_point": "fpr_99pct_invalid"},
        )
        self.assertEqual(response.status_code, 400)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "INVALID_REQUEST")

    def test_unknown_job_id_returns_404_job_not_found(self):
        """Querying a nonexistent job_id returns HTTP 404 JOB_NOT_FOUND."""
        response = self.client.get("/v1/audio/score/scr_nonexistent_99999")
        self.assertEqual(response.status_code, 404)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "JOB_NOT_FOUND")

    def test_oversized_audio_returns_413_file_too_large(self):
        """Submitting audio exceeding 50 MB limit returns HTTP 413 FILE_TOO_LARGE."""
        # 50 MB + 1 byte
        large_bytes = b"\x00" * (50 * 1024 * 1024 + 1)
        response = self.client.post(
            "/v1/audio/score",
            files={"file": ("giant.wav", large_bytes, "audio/wav")},
        )
        self.assertEqual(response.status_code, 413)
        err = ApiErrorResponse.model_validate(response.json())
        self.assertEqual(err.error_code, "FILE_TOO_LARGE")


class TestM1Determinism(M1BaseTestCase):
    """Verifies reproducible, deterministic results for identical audio inputs (Section 13)."""

    def setUp(self):
        super().setUp()
        job_store.clear()

    def test_identical_audio_yields_identical_scoring_output(self):
        """Same audio bytes must produce identical probability, verdict band, conditions, and evidence."""
        audio_a = generate_test_wav([123, -456, 789, -101] * 2000, rate=16000)

        # Call twice
        resp1 = self.client.post("/v1/audio/score", files={"file": ("audio_a.wav", audio_a, "audio/wav")})
        resp2 = self.client.post("/v1/audio/score", files={"file": ("audio_a.wav", audio_a, "audio/wav")})

        job_id_1 = resp1.json()["job_id"]
        job_id_2 = resp2.json()["job_id"]

        # Different job IDs generated
        self.assertNotEqual(job_id_1, job_id_2)

        # Fetch results
        data1 = self.client.get(f"/v1/audio/score/{job_id_1}").json()
        data2 = self.client.get(f"/v1/audio/score/{job_id_2}").json()

        # Check determinism of verdict & probability
        self.assertEqual(data1["verdict"]["probability"], data2["verdict"]["probability"])
        self.assertEqual(data1["verdict"]["band"], data2["verdict"]["band"])
        self.assertEqual(data1["verdict"]["reason"], data2["verdict"]["reason"])
        self.assertEqual(data1["verdict"]["operating_point"], data2["verdict"]["operating_point"])

        # Check determinism of conditions
        self.assertEqual(data1["conditions"], data2["conditions"])

        # Check determinism of segments
        self.assertEqual(data1["segments"], data2["segments"])

        # Check determinism of evidence
        self.assertEqual(data1["evidence"]["model_version"], data2["evidence"]["model_version"])
        self.assertEqual(data1["evidence"]["threshold_version"], data2["evidence"]["threshold_version"])
        self.assertEqual(data1["evidence"]["signal_contributions"], data2["evidence"]["signal_contributions"])

    def test_different_audio_yields_different_deterministic_hash(self):
        """Distinct audio content produces distinct hash-derived scores."""
        audio1 = generate_test_wav([1000] * 1000)
        audio2 = generate_test_wav([-2000] * 1000)

        res1 = compute_stub_score(audio1, job_id="scr_1")
        res2 = compute_stub_score(audio2, job_id="scr_2")

        # Hashes and condition metrics differ
        self.assertNotEqual(res1.conditions.snr_db, res2.conditions.snr_db)


class TestM1ProvenanceSafety(M1BaseTestCase):
    """Protects PRD FR-7: Missing or stripped credentials MUST NOT contribute to a synthetic verdict."""

    def test_missing_provenance_never_contributes_to_verdict(self):
        """FR-7 Regression Guard: provenance credentials absence must report not_present and contributed=False."""
        wav = generate_test_wav([300, -300] * 1000)
        result = compute_stub_score(wav, job_id="scr_test_prov")

        self.assertEqual(result.provenance.c2pa, "not_present")
        self.assertEqual(result.provenance.watermark, "not_present")
        self.assertFalse(
            result.provenance.contributed_to_verdict,
            "FR-7 VIOLATION: Missing provenance must never contribute to synthetic verdict!",
        )

        # Confirm evidence signal contributions do NOT include provenance as synthetic evidence
        signals = [s.signal for s in result.evidence.signal_contributions]
        self.assertNotIn("provenance", signals)
        self.assertNotIn("c2pa", signals)
        self.assertNotIn("missing_credentials", signals)


class TestM1LatencyMeasurement(M1BaseTestCase):
    """Measures M1 stub roundtrip latency as an engineering measurement (Section 21)."""

    def setUp(self):
        super().setUp()
        self.sample_wav = generate_test_wav([400] * 16000)

    def test_measure_stub_latency(self):
        """Records POST + GET roundtrip latency for M1 stub."""
        start = time.perf_counter()

        post_resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("perf_test.wav", self.sample_wav, "audio/wav")},
        )
        self.assertEqual(post_resp.status_code, 202)
        job_id = post_resp.json()["job_id"]

        get_resp = self.client.get(f"/v1/audio/score/{job_id}")
        self.assertEqual(get_resp.status_code, 200)

        duration_ms = (time.perf_counter() - start) * 1000.0
        # Engineering measurement assertion: stub responds in under 500ms
        self.assertLess(duration_ms, 500.0, f"Stub latency exceeded 500ms: {duration_ms:.2f}ms")


if __name__ == "__main__":
    unittest.main()
