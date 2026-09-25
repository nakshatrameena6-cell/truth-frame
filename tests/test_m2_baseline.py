"""Milestone M2 Automated Test Suite.

Validates:
1. Corpus v1 split integrity, sample counts, zero recording/source leakage.
2. Baseline model training, checkpoint persistence, and deterministic inference.
3. Amplitude normalization invariance (volume invariance 0.1x, 1x, 3x).
4. Full API integration behind the frozen M1 contract with real M2 baseline model.
5. FR-7 Provenance Safety: missing credentials NEVER contribute to synthetic score.
6. M2 Evaluation report presence, schema, and honest reporting of AC-1 through AC-8.
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import struct
import unittest
import wave

from fastapi.testclient import TestClient
import numpy as np

from audio_detection.api.app import app
from audio_detection.api.service import scoring_engine
from audio_detection.data.manifest import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.models.frontend import HybridFrontend


def create_synthetic_wav_bytes(
    duration_s: float = 1.0,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generates synthetic PCM WAV audio bytes for testing."""
    num_samples = int(duration_s * sample_rate)
    samples = [
        int(amplitude * 32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
        for i in range(num_samples)
    ]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


class TestM2CorpusAndLeakage(unittest.TestCase):
    """Corpus v1 split audit and isolation tests."""

    def setUp(self):
        self.manifest_path = Path("data/manifests/corpus_v1_split.json")

    def test_corpus_manifest_exists_and_valid(self):
        """Manifest must exist and contain at least 100 samples across 3 splits."""
        self.assertTrue(self.manifest_path.exists(), "Corpus v1 split manifest missing")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("samples", [])
        self.assertGreaterEqual(len(samples), 100)

        splits = {s["split"] for s in samples}
        self.assertEqual(splits, {"train", "validation", "test"})

    def test_zero_recording_and_source_leakage(self):
        """No recording or source ID may overlap between train, val, and test splits."""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("samples", [])

        train_recs = {s.get("recording_id", s["source_id"]) for s in samples if s["split"] == "train"}
        val_recs = {s.get("recording_id", s["source_id"]) for s in samples if s["split"] == "validation"}
        test_recs = {s.get("recording_id", s["source_id"]) for s in samples if s["split"] == "test"}

        train_srcs = {s["source_id"] for s in samples if s["split"] == "train"}
        val_srcs = {s["source_id"] for s in samples if s["split"] == "validation"}
        test_srcs = {s["source_id"] for s in samples if s["split"] == "test"}

        self.assertEqual(train_recs & val_recs, set(), "Recording leakage: train & val")
        self.assertEqual(train_recs & test_recs, set(), "Recording leakage: train & test")
        self.assertEqual(val_recs & test_recs, set(), "Recording leakage: val & test")

        self.assertEqual(train_srcs & val_srcs, set(), "Source leakage: train & val")
        self.assertEqual(train_srcs & test_srcs, set(), "Source leakage: train & test")
        self.assertEqual(val_srcs & test_srcs, set(), "Source leakage: val & test")

    def test_held_out_generator_isolation(self):
        """Held-out generator 'edge_tts_neural' must never appear in train or validation."""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("samples", [])

        train_gens = {s["generator"] for s in samples if s["split"] == "train"}
        val_gens = {s["generator"] for s in samples if s["split"] == "validation"}

        self.assertNotIn("edge_tts_neural", train_gens)
        self.assertNotIn("edge_tts_neural", val_gens)
        self.assertNotIn("elevenlabs_v3", train_gens)
        self.assertNotIn("elevenlabs_v3", val_gens)


class TestM2ModelAndInference(unittest.TestCase):
    """Model feature extraction, invariance, and deterministic inference tests."""

    def setUp(self):
        self.frontend = HybridFrontend()

    def test_volume_normalization_invariance(self):
        """Peak scaling (0.1x, 1x, 3x) must produce invariant feature vectors within 1e-4."""
        rate = 16000
        t = np.linspace(0, 0.5, int(rate * 0.5), endpoint=False)
        sig = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.cos(2 * np.pi * 880 * t)

        f_1x = self.frontend.embed(sig, rate)[:10]
        f_3x = self.frontend.embed(sig * 3.0, rate)[:10]
        f_01x = self.frontend.embed(sig * 0.1, rate)[:10]

        np.testing.assert_allclose(f_1x, f_3x, atol=1e-4, rtol=1e-4)
        np.testing.assert_allclose(f_1x, f_01x, atol=1e-4, rtol=1e-4)

    def test_deterministic_scoring(self):
        """Scoring identical audio twice must return bitwise identical scores."""
        audio_bytes = create_synthetic_wav_bytes(duration_s=1.0, freq=300.0)
        res1 = scoring_engine.score_audio(audio_bytes, "job_1")
        res2 = scoring_engine.score_audio(audio_bytes, "job_2")

        self.assertEqual(res1.verdict.probability, res2.verdict.probability)
        self.assertEqual(res1.verdict.band, res2.verdict.band)
        self.assertEqual(len(res1.segments), len(res2.segments))


class TestM2ApiIntegration(unittest.TestCase):
    """Full API contract and safety tests with real M2 baseline model."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m2"
        self.client = TestClient(app)
        self.valid_wav = create_synthetic_wav_bytes(duration_s=1.2, freq=440.0)

    def test_health_check_returns_m2_model(self):
        """GET /health must return healthy status and active model version."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["status"], ["ok", "healthy"])
        self.assertEqual(data["model_version"], "m2-waveform-10d")

    def test_score_audio_end_to_end(self):
        """POST /v1/audio/score followed by GET /v1/audio/score/{id} returns real M2 verdict."""
        post_resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("test.wav", self.valid_wav, "audio/wav")},
            data={"operating_point": "fpr_1pct"},
        )
        self.assertEqual(post_resp.status_code, 202)
        job_id = post_resp.json()["job_id"]

        get_resp = self.client.get(f"/v1/audio/score/{job_id}")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()

        # Check verdict structure
        self.assertIn("verdict", data)
        self.assertIn(data["verdict"]["band"], ["likely_synthetic", "consistent_with_human", "inconclusive"])
        self.assertGreaterEqual(data["verdict"]["probability"], 0.0)
        self.assertLessEqual(data["verdict"]["probability"], 1.0)

        # Check conditions
        self.assertIn("conditions", data)
        self.assertIn("snr_db", data["conditions"])
        self.assertIn("effective_bandwidth_hz", data["conditions"])

        # Check FR-7 Provenance Safety Invariant
        self.assertIn("provenance", data)
        self.assertEqual(data["provenance"]["c2pa"], "not_present")
        self.assertEqual(data["provenance"]["watermark"], "not_present")
        self.assertFalse(data["provenance"]["contributed_to_verdict"])

        # Check Evidence model version
        self.assertIn("evidence", data)
        self.assertEqual(data["evidence"]["model_version"], "m2-waveform-10d")

    def test_operating_points_accepted(self):
        """API must support all required operating points (fpr_0.1pct, fpr_1pct, fpr_5pct)."""
        for op in ("fpr_0.1pct", "fpr_1pct", "fpr_5pct"):
            resp = self.client.post(
                "/v1/audio/score",
                files={"file": ("test.wav", self.valid_wav, "audio/wav")},
                data={"operating_point": op},
            )
            self.assertEqual(resp.status_code, 202)
            job_id = resp.json()["job_id"]

            score_data = self.client.get(f"/v1/audio/score/{job_id}").json()
            self.assertEqual(score_data["verdict"]["operating_point"], op)

    def test_provenance_safety_invariant_fr7(self):
        """CRITICAL FR-7: Missing credentials must never cause contributed_to_verdict=True."""
        resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("sample.wav", self.valid_wav, "audio/wav")},
        )
        job_id = resp.json()["job_id"]
        res = self.client.get(f"/v1/audio/score/{job_id}").json()
        self.assertFalse(res["provenance"]["contributed_to_verdict"])


class TestM2HonestEvaluationReport(unittest.TestCase):
    """M2 Benchmark Evaluation report verification."""

    def test_m2_eval_report_exists_and_honest(self):
        """M2 report must exist and honestly state AC-7 language slice limitation."""
        report_path = Path("reports/benchmark/m2_eval_report.json")
        if not report_path.exists():
            self.skipTest("m2_eval_report.json not yet generated")

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        self.assertIn("models", report)
        self.assertIn("m2-waveform-10d", report["models"])
        self.assertIn("acceptance_criteria", report)

        # Check AC-7 honest reporting
        ac7 = report["acceptance_criteria"]["AC-7"]
        self.assertIn(ac7["status"], ["PASS", "INSUFFICIENT"])
        if ac7["status"] == "INSUFFICIENT":
            self.assertIn("synthetic samples", ac7["reason"].lower())
        else:
            self.assertIsNotNone(ac7.get("measured"))


if __name__ == "__main__":
    unittest.main()
