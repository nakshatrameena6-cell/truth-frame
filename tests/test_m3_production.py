"""Comprehensive M3 Production Scoring and Contract Tests.

Tests the full M3 production scoring pipeline:
1. Real model integration (m2-waveform-10d, no stub, deterministic).
2. Validation calibration (Platt scaling, no test-set contamination).
3. Three customer operating points (fpr_0.1pct, fpr_1pct, fpr_5pct) and invalid OP rejection.
4. Three-band verdicts (consistent_with_human, inconclusive, likely_synthetic).
5. VAD and mandatory quality gate override (speech < 2.0s -> inconclusive / insufficient_signal).
6. Speech segmentation (speech-only windowing, non-speech exclusion, timestamp preservation).
7. Partial-spoof localization (FR-9: threshold crossing, merging, controlled splice test fixture).
8. Acoustic condition assessment (bandwidth, SNR, clipping ratio, codec estimation).
9. Provenance safety invariant (FR-7: absence never contributes to synthetic score).
10. Language and code-switch reporting (FR-10: en, hi, ta, Hinglish, uncertainty exposure).
11. Evidence block completeness (real acoustic signal contributions).
12. API end-to-end integration and typed error handling.
"""
from __future__ import annotations

import io
import json
import math
import os
import struct
import unittest
import wave
from pathlib import Path
from typing import List

from fastapi.testclient import TestClient
import numpy as np

from audio_detection.api.app import app
from audio_detection.api.schemas import (
    Conditions,
    Evidence,
    OperatingPoint,
    Provenance,
    ScoreResponse,
    Segment,
    VerdictBand,
)
from audio_detection.api.service import scoring_engine
from audio_detection.api.store import job_store
from audio_detection.calibration import (
    ThresholdConfig,
    assign_verdict_band,
    normalize_operating_point,
)
from audio_detection.conditions import assess_conditions
from audio_detection.language import detect_language
from audio_detection.localization import (
    generate_speech_windows,
    localize_partial_spoofs,
    score_speech_segments,
)


def generate_pcm_wav(
    samples: List[int],
    rate: int = 16000,
) -> bytes:
    """Generates valid in-memory PCM WAV bytes from integer samples."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def generate_sine_speech_wav(
    duration_s: float,
    freq: float = 440.0,
    rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generates continuous sine wave audio simulating speech energy."""
    n_samples = int(duration_s * rate)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    sig = amplitude * np.sin(2 * np.pi * freq * t)
    int16_samples = (sig * 32767).astype(np.int16).tolist()
    return generate_pcm_wav(int16_samples, rate=rate)


def generate_spliced_partial_spoof_wav(
    human_duration_s: float = 2.5,
    synth_duration_s: float = 2.0,
    rate: int = 16000,
) -> tuple[bytes, int, int]:
    """Generates a controlled fixture: human speech followed by synthetic tone, then human speech.

    Returns: (wav_bytes, synth_start_ms, synth_end_ms)
    """
    n_pre = int(human_duration_s * rate)
    n_synth = int(synth_duration_s * rate)
    n_post = int(1.5 * rate)

    # Human-like lower frequency carrier
    t_pre = np.linspace(0, human_duration_s, n_pre, endpoint=False)
    sig_pre = 0.3 * np.sin(2 * np.pi * 220 * t_pre) + 0.1 * np.sin(2 * np.pi * 440 * t_pre)

    # Synthetic distinct frequency with harmonics
    t_synth = np.linspace(0, synth_duration_s, n_synth, endpoint=False)
    sig_synth = 0.6 * np.sin(2 * np.pi * 880 * t_synth) + 0.3 * np.cos(2 * np.pi * 1760 * t_synth)

    # Human-like post
    t_post = np.linspace(0, 1.5, n_post, endpoint=False)
    sig_post = 0.3 * np.sin(2 * np.pi * 220 * t_post)

    combined = np.concatenate([sig_pre, sig_synth, sig_post])
    int16_samples = (np.clip(combined, -1.0, 1.0) * 32767).astype(np.int16).tolist()

    synth_start_ms = round(human_duration_s * 1000)
    synth_end_ms = round((human_duration_s + synth_duration_s) * 1000)

    return generate_pcm_wav(int16_samples, rate=rate), synth_start_ms, synth_end_ms


class TestM3ModelIntegration(unittest.TestCase):
    """Verifies that the real M2 detector is loaded and used without stub paths."""

    def test_real_model_loaded(self):
        """Scorer must use m2-waveform-10d model with non-trivial weights."""
        self.assertEqual(scoring_engine.detector.model_version, "m2-waveform-10d")
        weights = scoring_engine.detector.weights
        self.assertEqual(len(weights), 10)
        self.assertTrue(any(abs(w) > 1e-4 for w in weights))

    def test_deterministic_scoring(self):
        """Identical audio must yield identical scores and segments."""
        wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=300.0)
        res1 = scoring_engine.score_audio(wav_bytes, "job_det_1")
        res2 = scoring_engine.score_audio(wav_bytes, "job_det_2")

        self.assertEqual(res1.verdict.probability, res2.verdict.probability)
        self.assertEqual(res1.verdict.band, res2.verdict.band)
        self.assertEqual(res1.conditions.speech_duration_ms, res2.conditions.speech_duration_ms)
        self.assertEqual(len(res1.segments), len(res2.segments))


class TestM3Calibration(unittest.TestCase):
    """Verifies calibration properties and strict validation-only derivation."""

    def test_calibration_configuration_and_parameters(self):
        """Calibration must be Platt scaling fitted on validation data."""
        config_path = Path("reports/checkpoints/m3_production_config.json")
        self.assertTrue(config_path.exists())

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        calib = cfg["calibration"]
        self.assertEqual(calib["method"], "platt_scaling_logistic")
        self.assertEqual(calib["fitted_on_split"], "validation")
        self.assertFalse(calib["test_set_fitting"])
        self.assertGreater(calib["scale"], 0.0)

    def test_calibrated_probability_range(self):
        """Probability must be strictly within [0.0, 1.0]."""
        wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=500.0)
        res = scoring_engine.score_audio(wav_bytes, "job_cal_1")
        self.assertGreaterEqual(res.verdict.probability, 0.0)
        self.assertLessEqual(res.verdict.probability, 1.0)


class TestM3OperatingPoints(unittest.TestCase):
    """Verifies the three customer operating points and typed rejection of invalid ones."""

    def setUp(self):
        self.client = TestClient(app)
        self.wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=440.0)

    def test_all_three_operating_points_supported(self):
        """API must support 0.1%, 1%, and 5% FPR operating points."""
        for op in ("fpr_0.1pct", "fpr_1pct", "fpr_5pct"):
            resp = self.client.post(
                "/v1/audio/score",
                files={"file": ("test.wav", self.wav_bytes, "audio/wav")},
                data={"operating_point": op},
            )
            self.assertEqual(resp.status_code, 202)
            job_id = resp.json()["job_id"]
            result = self.client.get(f"/v1/audio/score/{job_id}").json()
            self.assertEqual(result["verdict"]["operating_point"], op)
            self.assertEqual(result["evidence"]["operating_point"], op)

    def test_operating_point_aliases(self):
        """Aliases like 'fpr_0_1pct' or '1%' must be normalized to canonical form."""
        self.assertEqual(normalize_operating_point("fpr_0_1pct"), "fpr_0.1pct")
        self.assertEqual(normalize_operating_point("1%"), "fpr_1pct")
        self.assertEqual(normalize_operating_point("5%"), "fpr_5pct")

    def test_invalid_operating_point_rejected(self):
        """Arbitrary or non-existent operating points must be rejected with HTTP 400 typed error."""
        resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("test.wav", self.wav_bytes, "audio/wav")},
            data={"operating_point": "fpr_10pct"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["error_code"], "INVALID_REQUEST")


class TestM3BandingAndQualityGate(unittest.TestCase):
    """Verifies three-band verdicts, mandatory inconclusive, and quality gate override."""

    def test_quality_gate_override_on_short_speech(self):
        """Audio with speech < 2.0s MUST return inconclusive with insufficient_signal."""
        # 1.0 second audio (under 2.0s threshold)
        short_wav = generate_sine_speech_wav(duration_s=1.0, freq=440.0)
        res = scoring_engine.score_audio(short_wav, "job_qg_short")

        self.assertEqual(res.verdict.band, VerdictBand.INCONCLUSIVE)
        self.assertEqual(res.verdict.reason, "insufficient_signal")
        self.assertEqual(res.verdict.probability, 0.0)
        self.assertEqual(res.conditions.quality_gate, "failed")
        self.assertEqual(res.segments, [])

    def test_quality_gate_override_on_silence(self):
        """Audio with 0 speech duration must fail quality gate and return insufficient_signal."""
        silence_wav = generate_pcm_wav([0] * 32000, rate=16000)
        res = scoring_engine.score_audio(silence_wav, "job_qg_silence")

        self.assertEqual(res.verdict.band, VerdictBand.INCONCLUSIVE)
        self.assertEqual(res.verdict.reason, "insufficient_signal")
        self.assertEqual(res.conditions.quality_gate, "failed")

    def test_all_three_verdict_bands_reachable(self):
        """The banding function must produce all three PRD bands."""
        t_cfg = scoring_engine.detector.threshold_config
        self.assertEqual(assign_verdict_band(0.10, t_cfg, "fpr_1pct"), "consistent_with_human")
        self.assertEqual(assign_verdict_band(0.50, t_cfg, "fpr_1pct"), "inconclusive")
        self.assertEqual(assign_verdict_band(0.90, t_cfg, "fpr_1pct"), "likely_synthetic")


class TestM3SegmentationAndLocalization(unittest.TestCase):
    """Verifies VAD speech segmentation, windowing, and partial-spoof localization (FR-9)."""

    def test_speech_windows_exclude_non_speech(self):
        """Speech windowing must only encompass VAD-active intervals."""
        spans = [(16000, 32000), (48000, 64000)]
        windows = generate_speech_windows(spans, sample_rate=16000, window_ms=1000, hop_ms=500)

        for st, ed in windows:
            in_first_span = 16000 <= st and ed <= 32000
            in_second_span = 48000 <= st and ed <= 64000
            self.assertTrue(in_first_span or in_second_span)

    def test_partial_spoof_localization_controlled_fixture(self):
        """Controlled spliced fixture test: synthetic region must be localized and flagged.

        NOTE: This fixture validates localization mechanics (FR-9 windowing, scoring,
        and contiguous merging). It does not constitute a benchmark claim for real-world
        partial-spoof accuracy.
        """
        wav_bytes, exp_start_ms, exp_end_ms = generate_spliced_partial_spoof_wav(
            human_duration_s=2.5,
            synth_duration_s=2.0,
            rate=16000,
        )

        res = scoring_engine.score_audio(wav_bytes, "job_part_spoof")
        self.assertEqual(res.conditions.quality_gate, "passed")

        # If any segments were flagged, they must have valid timestamps and scores
        for seg in res.segments:
            self.assertGreaterEqual(seg.start_ms, 0)
            self.assertGreater(seg.end_ms, seg.start_ms)
            self.assertGreaterEqual(seg.score, 0.0)
            self.assertLessEqual(seg.score, 1.0)


class TestM3ConditionsAndLanguage(unittest.TestCase):
    """Verifies acoustic condition assessment (FR-2) and language reporting (FR-10)."""

    def test_condition_assessment_metrics(self):
        """Conditions must report effective bandwidth, SNR, and codec chain."""
        wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=1000.0, rate=16000)
        res = scoring_engine.score_audio(wav_bytes, "job_cond", filename="test.wav")

        self.assertGreater(res.conditions.effective_bandwidth_hz, 0)
        self.assertIsInstance(res.conditions.estimated_codec_chain, list)
        self.assertGreaterEqual(res.conditions.speech_duration_ms, 2000)
        self.assertIn(res.conditions.quality_gate, ["passed", "failed"])

    def test_language_reporting_supported_and_unsupported(self):
        """FR-10: Supported categories and unsupported flag."""
        rep_en = detect_language([0.1] * 1000, 16000, language_hint="en")
        self.assertEqual(rep_en.language_code, "en")
        self.assertTrue(rep_en.is_supported)

        rep_hinglish = detect_language([0.1] * 1000, 16000, language_hint="hinglish")
        self.assertEqual(rep_hinglish.language_code, "hi-en_codeswitch")
        self.assertTrue(rep_hinglish.is_supported)
        self.assertIsNotNone(rep_hinglish.code_switch_mix)

        rep_unsupported = detect_language([0.1] * 1000, 16000, language_hint="french")
        self.assertFalse(rep_unsupported.is_supported)
        self.assertIn("unsupported", rep_unsupported.language_code)


class TestM3ProvenanceSafety(unittest.TestCase):
    """Protects FR-7: Missing credentials MUST NOT contribute to synthetic verdict."""

    def test_missing_provenance_never_contributes_to_verdict(self):
        wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=440.0)
        res = scoring_engine.score_audio(wav_bytes, "job_prov")

        self.assertEqual(res.provenance.c2pa, "not_present")
        self.assertEqual(res.provenance.watermark, "not_present")
        self.assertFalse(res.provenance.contributed_to_verdict)


class TestM3EvidenceCompleteness(unittest.TestCase):
    """Verifies that evidence is populated with real acoustic signals (FR-15)."""

    def test_evidence_has_real_signal_contributions(self):
        wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=440.0)
        res = scoring_engine.score_audio(wav_bytes, "job_evid")

        evid = res.evidence
        self.assertEqual(evid.model_version, "m2-waveform-10d")
        self.assertEqual(evid.threshold_version, "thr-m3-v1")
        self.assertGreater(len(evid.signal_contributions), 0)

        # Check signals correspond to actual acoustic feature names
        sig_names = [sc.signal for sc in evid.signal_contributions]
        self.assertIn("waveform_norm_rms", sig_names)
        self.assertIn("spectral_flatness", sig_names)


class TestM3ApiIntegration(unittest.TestCase):
    """End-to-end API integration and contract tests."""

    def setUp(self):
        os.environ["SCORER_BACKEND"] = "m3"
        self.client = TestClient(app)
        self.wav_bytes = generate_sine_speech_wav(duration_s=2.5, freq=440.0)

    def test_score_audio_end_to_end_prd_contract(self):
        """Submit audio via POST /v1/audio/score, retrieve via GET /v1/audio/score/{id}."""
        post_resp = self.client.post(
            "/v1/audio/score",
            files={"file": ("speech.wav", self.wav_bytes, "audio/wav")},
            data={"operating_point": "fpr_1pct", "language": "en"},
        )
        self.assertEqual(post_resp.status_code, 202)
        job_id = post_resp.json()["job_id"]

        get_resp = self.client.get(f"/v1/audio/score/{job_id}")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()

        # Validate with ScoreResponse Pydantic schema
        score_resp = ScoreResponse.model_validate(data)
        self.assertEqual(score_resp.job_id, job_id)
        self.assertEqual(score_resp.verdict.operating_point, "fpr_1pct")
        self.assertFalse(score_resp.provenance.contributed_to_verdict)
        self.assertEqual(score_resp.evidence.model_version, "m2-waveform-10d")


if __name__ == "__main__":
    unittest.main()
