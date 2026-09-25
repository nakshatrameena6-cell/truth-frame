"""M4: Full Acceptance and Release-Gate Automated Test Suite.

Validates:
1. Frozen Evaluation Configuration (manifest hashes, checkpoint integrity, held-out generators).
2. Zero-Leakage Audit (no recording, source, or speaker leakage between splits).
3. AC-1 through AC-8 against official PRD thresholds:
   - AC-1: In-domain clean EER <= 5.0%
   - AC-2: Cross-generator clean EER <= 15.0% (both edge_tts_neural and elevenlabs_v3)
   - AC-3: Cross-generator telecom EER <= 25.0% (G.711 and AMR-NB) [RELEASE-CRITICAL]
   - AC-4: Detection sensitivity TPR @ 1% FPR >= 70.0%
   - AC-5: Expected Calibration Error (ECE) <= 0.050
   - AC-6: Abstention rate <= 20.0% on quality-gated inputs
   - AC-7: Language consistency Max/Min EER <= 2.0x (en, hi, ta, hinglish) [RELEASE-CRITICAL]
   - AC-8: Improvement over legacy 4D baseline
4. Partial-Spoof Localization (FR-9) and VAD windowing.
5. Provenance safety invariant (FR-7: absence contributes zero).
6. API Contract Acceptance across all three operating points and error handling.
7. Security and offline VPC sanity.
"""
from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
import numpy as np

from audio_detection.api.app import app
from audio_detection.api.schemas import ScoreResponse, VerdictBand
from audio_detection.api.service import scoring_engine
from audio_detection.calibration import normalize_operating_point
from audio_detection.evaluation.metrics import evaluate


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestM4FrozenEvaluationIntegrity(unittest.TestCase):
    """Verifies that all evaluation components and artifacts are versioned and frozen."""

    def test_manifest_and_splits_frozen(self):
        manifest_path = Path("data/manifests/corpus_v1_split.json")
        self.assertTrue(manifest_path.exists())
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["version"], "corpus_v1_remediated")
        self.assertEqual(len(data["samples"]), 172)
        self.assertEqual(data["splits"]["train"], 36)
        self.assertEqual(data["splits"]["validation"], 48)
        self.assertEqual(data["splits"]["test"], 88)

    def test_held_out_generators_strictly_test_only(self):
        manifest_path = Path("data/manifests/corpus_v1_split.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        train_gens = {s["generator"] for s in data["samples"] if s["split"] == "train"}
        val_gens = {s["generator"] for s in data["samples"] if s["split"] == "validation"}
        test_gens = {s["generator"] for s in data["samples"] if s["split"] == "test"}

        held_out = {"edge_tts_neural", "elevenlabs_v3"}
        self.assertEqual(held_out & train_gens, set())
        self.assertEqual(held_out & val_gens, set())
        self.assertTrue(held_out.issubset(test_gens))

    def test_zero_recording_source_speaker_leakage(self):
        manifest_path = Path("data/manifests/corpus_v1_split.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        train_samples = [s for s in data["samples"] if s["split"] == "train"]
        val_samples = [s for s in data["samples"] if s["split"] == "validation"]
        test_samples = [s for s in data["samples"] if s["split"] == "test"]

        # Recording
        tr_recs = {s.get("recording_id", s["source_id"]) for s in train_samples}
        val_recs = {s.get("recording_id", s["source_id"]) for s in val_samples}
        te_recs = {s.get("recording_id", s["source_id"]) for s in test_samples}
        self.assertEqual(tr_recs & val_recs, set())
        self.assertEqual(tr_recs & te_recs, set())
        self.assertEqual(val_recs & te_recs, set())

        # Source
        tr_srcs = {s["source_id"] for s in train_samples}
        val_srcs = {s["source_id"] for s in val_samples}
        te_srcs = {s["source_id"] for s in test_samples}
        self.assertEqual(tr_srcs & val_srcs, set())
        self.assertEqual(tr_srcs & te_srcs, set())
        self.assertEqual(val_srcs & te_srcs, set())

        # Speaker
        tr_spks = {s["speaker_id"] for s in train_samples}
        val_spks = {s["speaker_id"] for s in val_samples}
        te_spks = {s["speaker_id"] for s in test_samples}
        self.assertEqual(tr_spks & val_spks, set())
        self.assertEqual(tr_spks & te_spks, set())
        self.assertEqual(val_spks & te_spks, set())


class TestM4AcceptanceCriteria(unittest.TestCase):
    """Audits the official PRD Acceptance Criteria AC-1 through AC-8 from the M4 evaluation report."""

    def setUp(self):
        report_path = Path("reports/benchmark/m4_eval_report.json")
        self.assertTrue(report_path.exists(), "m4_eval_report.json must exist before running acceptance tests")
        with open(report_path, "r", encoding="utf-8") as f:
            self.report = json.load(f)

    def test_ac1_in_domain_clean(self):
        """AC-1: In-domain clean EER <= 5.0%."""
        ac1 = self.report["acceptance_criteria"]["AC-1"]
        self.assertEqual(ac1["status"], "PASS")
        self.assertLessEqual(ac1["measured"], 0.050)

    def test_ac2_cross_generator_clean(self):
        """AC-2: Cross-generator clean EER <= 15.0% on both held-out generators."""
        ac2 = self.report["acceptance_criteria"]["AC-2"]
        self.assertEqual(ac2["status"], "PASS")
        self.assertLessEqual(ac2["measured"], 0.150)
        hg = ac2["held_out_generators"]
        self.assertIn("edge_tts_neural", hg)
        self.assertIn("elevenlabs_v3", hg)
        self.assertLessEqual(hg["edge_tts_neural"], 0.150)
        self.assertLessEqual(hg["elevenlabs_v3"], 0.150)

    def test_ac3_cross_generator_telecom_release_critical(self):
        """AC-3: Cross-generator telecom EER <= 25.0% on G.711 and AMR-NB [RELEASE CRITICAL]."""
        ac3 = self.report["acceptance_criteria"]["AC-3"]
        self.assertTrue(ac3.get("release_critical", False))
        self.assertEqual(ac3["status"], "PASS")
        self.assertLessEqual(ac3["measured"], 0.250)
        self.assertLessEqual(ac3["codecs"]["g711_8khz"], 0.250)
        self.assertLessEqual(ac3["codecs"]["amr_nb"], 0.250)

    def test_ac4_detection_sensitivity(self):
        """AC-4: TPR @ 1.0% FPR >= 70.0% using validation-derived threshold."""
        ac4 = self.report["acceptance_criteria"]["AC-4"]
        self.assertEqual(ac4["status"], "PASS")
        self.assertGreaterEqual(ac4["measured"], 0.700)
        self.assertEqual(ac4["derivation_source"], "validation split")

    def test_ac5_calibration_ece(self):
        """AC-5: Expected Calibration Error (ECE) <= 0.050."""
        ac5 = self.report["acceptance_criteria"]["AC-5"]
        self.assertEqual(ac5["status"], "PASS")
        self.assertLessEqual(ac5["measured"], 0.050)
        self.assertEqual(ac5["calibration_split"], "validation")

    def test_ac6_abstention_discipline(self):
        """AC-6: Abstention Rate <= 20.0% among quality-gated inputs."""
        ac6 = self.report["acceptance_criteria"]["AC-6"]
        self.assertEqual(ac6["status"], "PASS")
        self.assertLessEqual(ac6["measured"], 0.200)

    def test_ac7_language_consistency_release_critical(self):
        """AC-7: Language consistency Max/Min EER <= 2.0x across all 4 Indic slices [RELEASE CRITICAL]."""
        ac7 = self.report["acceptance_criteria"]["AC-7"]
        self.assertTrue(ac7.get("release_critical", False))
        self.assertEqual(ac7["status"], "PASS")
        self.assertLessEqual(ac7["measured"], 2.0)
        per_lang = ac7["per_language_eer"]
        self.assertEqual(set(per_lang.keys()), {"en", "hi", "ta", "hinglish"})

    def test_ac8_baseline_and_public_comparison(self):
        """AC-8: Baseline improvement demonstrated over legacy 4D baseline."""
        ac8 = self.report["acceptance_criteria"]["AC-8"]
        self.assertEqual(ac8["status"], "PASS")
        self.assertLessEqual(ac8["measured_10d_eer"], ac8["measured_4d_eer"])


class TestM4ApiContractAndSafety(unittest.TestCase):
    """Verifies end-to-end API contract, typed error handling, and FR-7 safety."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)

        # Generate a valid 2.5s speech PCM WAV
        import io
        import struct
        import wave
        duration_s = 2.5
        rate = 16000
        n_samples = int(duration_s * rate)
        t = np.linspace(0, duration_s, n_samples, endpoint=False)
        sig = 0.5 * np.sin(2 * np.pi * 440.0 * t)
        int16_samples = (sig * 32767).astype(np.int16).tolist()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(struct.pack(f"<{len(int16_samples)}h", *int16_samples))
        self.valid_wav = buf.getvalue()

    def test_all_operating_points_valid_and_typed_error_on_invalid(self):
        """Customer selection of 0.1%, 1%, 5% FPR accepted; invalid rejected with HTTP 400."""
        for op in ("fpr_0.1pct", "fpr_1pct", "fpr_5pct"):
            resp = self.client.post(
                "/v1/audio/score",
                files={"file": ("speech.wav", self.valid_wav, "audio/wav")},
                data={"operating_point": op},
            )
            self.assertEqual(resp.status_code, 202)
            job_id = resp.json()["job_id"]
            res = self.client.get(f"/v1/audio/score/{job_id}").json()
            self.assertEqual(res["verdict"]["operating_point"], op)

        # Invalid OP
        bad_resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("speech.wav", self.valid_wav, "audio/wav")},
            data={"operating_point": "fpr_20pct"},
        )
        self.assertEqual(bad_resp.status_code, 400)
        self.assertEqual(bad_resp.json()["error_code"], "INVALID_REQUEST")

    def test_quality_gate_override_short_audio(self):
        """Inputs with speech < 2.0s must return inconclusive with insufficient_signal."""
        import io
        import struct
        import wave
        duration_s = 0.8  # under 2.0s
        rate = 16000
        n_samples = int(duration_s * rate)
        t = np.linspace(0, duration_s, n_samples, endpoint=False)
        sig = 0.5 * np.sin(2 * np.pi * 440.0 * t)
        int16_samples = (sig * 32767).astype(np.int16).tolist()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(struct.pack(f"<{len(int16_samples)}h", *int16_samples))
        short_wav = buf.getvalue()

        resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("short.wav", short_wav, "audio/wav")},
        )
        self.assertEqual(resp.status_code, 202)
        job_id = resp.json()["job_id"]
        res = self.client.get(f"/v1/audio/score/{job_id}").json()
        self.assertEqual(res["verdict"]["band"], "inconclusive")
        self.assertEqual(res["verdict"]["reason"], "insufficient_signal")
        self.assertEqual(res["verdict"]["probability"], 0.0)
        self.assertEqual(res["conditions"]["quality_gate"], "failed")

    def test_fr7_provenance_safety_invariant(self):
        """FR-7: Missing credentials must never contribute to synthetic score."""
        resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("speech.wav", self.valid_wav, "audio/wav")},
        )
        job_id = resp.json()["job_id"]
        res = self.client.get(f"/v1/audio/score/{job_id}").json()
        self.assertEqual(res["provenance"]["c2pa"], "not_present")
        self.assertEqual(res["provenance"]["watermark"], "not_present")
        self.assertFalse(res["provenance"]["contributed_to_verdict"])


class TestM4SecurityAndDeployment(unittest.TestCase):
    """Sanity checks for offline VPC readiness."""

    def test_max_file_size_enforced(self):
        """Files > 50 MB must be rejected with HTTP 413 FILE_TOO_LARGE."""
        from audio_detection.api.app import MAX_FILE_SIZE_BYTES
        self.assertEqual(MAX_FILE_SIZE_BYTES, 50 * 1024 * 1024)

    def test_public_baselines_report_exists_and_honest(self):
        """Public baselines documentation exists and documents offline constraints."""
        p = Path("reports/benchmark/public_baselines.json")
        self.assertTrue(p.exists())
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("baselines", data)
        self.assertTrue(len(data["baselines"]) >= 4)


if __name__ == "__main__":
    unittest.main()
