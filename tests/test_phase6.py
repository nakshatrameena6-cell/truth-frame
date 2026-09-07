import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audio_detection.calibration import (
    TemperatureScaler,
    ThresholdConfig,
    assign_verdict_band,
    derive_calibration_thresholds,
)
from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data.manifest import CorpusManifest, Sample
from audio_detection.detector import AudioDetector
from audio_detection.training.trainer import load_checkpoint, save_checkpoint


def make_wav(samples, rate=8000):
    import io
    import struct
    import wave

    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return stream.getvalue()


class Phase6Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def sample(self, ident, is_synthetic=False, split="validation", **overrides):
        values = dict(
            sample_id=ident,
            source_id=f"src_{ident}",
            speaker_id=f"spk_{ident}",
            language="hi",
            is_synthetic=is_synthetic,
            generator="human" if not is_synthetic else "seen",
            audio_path=f"{ident}.wav",
            degradation="clean",
            sample_rate=8000,
            channels=1,
            split=split,
        )
        values.update(overrides)
        return Sample(**values)

    def test_temperature_scaling_fit_and_transform(self):
        scaler = TemperatureScaler(temperature=1.0)
        scores = [-2.0, -1.0, 0.0, 1.0, 2.0]
        labels = [0, 0, 0, 1, 1]

        # Before fit
        probs_before = scaler.transform(scores)
        self.assertEqual(len(probs_before), 5)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in probs_before))

        # Fit temperature
        scaler.fit(scores, labels)
        self.assertGreater(scaler.temperature, 0.0)

        # After fit transform
        probs_after = scaler.transform(scores)
        self.assertEqual(len(probs_after), 5)
        # Verify determinism of fit
        scaler2 = TemperatureScaler(temperature=1.0).fit(scores, labels)
        self.assertEqual(scaler.temperature, scaler2.temperature)

    def test_threshold_derivation_all_three_operating_points(self):
        # 10 human samples (0) and 10 synthetic samples (1)
        scores = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                  0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
        labels = [0] * 10 + [1] * 10

        config = derive_calibration_thresholds(scores, labels, temperature=1.0, target_operating_point="fpr_1%")
        self.assertEqual(config.calibration_status, "calibrated")
        self.assertIsNone(config.calibration_reason)
        self.assertIsNotNone(config.operating_point_thresholds)

        op = config.operating_point_thresholds
        self.assertIn("fpr_0.1%", op)
        self.assertIn("fpr_1%", op)
        self.assertIn("fpr_5%", op)

        # Higher FPR target allows more false positives, so threshold should be lower/equal
        self.assertGreaterEqual(op["fpr_0.1%"], op["fpr_1%"])
        self.assertGreaterEqual(op["fpr_1%"], op["fpr_5%"])

        self.assertIsNotNone(config.low_threshold)
        self.assertIsNotNone(config.high_threshold)
        self.assertLess(config.low_threshold, config.high_threshold)

    def test_verdict_band_assignment(self):
        config = ThresholdConfig(
            temperature=1.0,
            calibration_status="calibrated",
            calibration_reason=None,
            operating_point_thresholds={"fpr_0.1%": 0.8, "fpr_1%": 0.7, "fpr_5%": 0.6},
            low_threshold=0.3,
            high_threshold=0.7,
        )

        self.assertEqual(assign_verdict_band(0.1, config), "consistent_with_human")
        self.assertEqual(assign_verdict_band(0.29, config), "consistent_with_human")
        self.assertEqual(assign_verdict_band(0.3, config), "inconclusive")
        self.assertEqual(assign_verdict_band(0.5, config), "inconclusive")
        self.assertEqual(assign_verdict_band(0.7, config), "inconclusive")
        self.assertEqual(assign_verdict_band(0.71, config), "likely_synthetic")
        self.assertEqual(assign_verdict_band(0.99, config), "likely_synthetic")

    def test_inconclusive_band_is_never_disableable(self):
        # Even if synthetic and human distributions overlap heavily
        scores = [0.6, 0.7, 0.8, 0.9, 0.2, 0.3, 0.4, 0.5]
        labels = [0, 0, 0, 0, 1, 1, 1, 1]

        config = derive_calibration_thresholds(scores, labels)
        self.assertEqual(config.calibration_status, "calibrated")
        self.assertLess(config.low_threshold, config.high_threshold)

        # Midpoint between low and high must fall in inconclusive
        mid = (config.low_threshold + config.high_threshold) / 2
        self.assertEqual(assign_verdict_band(mid, config), "inconclusive")

    def test_insufficient_validation_data_returns_not_calibrated(self):
        # Empty scores
        cfg_empty = derive_calibration_thresholds([], [])
        self.assertEqual(cfg_empty.calibration_status, "not_calibrated")
        self.assertEqual(cfg_empty.calibration_reason, "insufficient_validation_data")
        self.assertEqual(assign_verdict_band(0.5, cfg_empty), "not_calibrated")

        # Single class
        cfg_single = derive_calibration_thresholds([0.1, 0.2], [0, 0])
        self.assertEqual(cfg_single.calibration_status, "not_calibrated")
        self.assertEqual(cfg_single.calibration_reason, "insufficient_validation_data_missing_classes")
        self.assertEqual(assign_verdict_band(0.5, cfg_single), "not_calibrated")

        # Insufficient sample count
        cfg_few = derive_calibration_thresholds([0.1, 0.9], [0, 1])
        self.assertEqual(cfg_few.calibration_status, "not_calibrated")
        self.assertEqual(cfg_few.calibration_reason, "insufficient_validation_sample_count")

    def test_raw_score_distinct_from_calibrated_probability(self):
        detector = AudioDetector(
            weights=(1.0, 2.0, 3.0, 4.0),
            bias=1.5,
            temperature=2.0,
        )
        audio = make_wav([500] * 100)
        res = detector.detect(audio)

        self.assertIn("raw_score", res)
        self.assertIn("calibrated_probability", res)
        self.assertIn("verdict", res)
        self.assertIn("calibration_status", res)

        # raw_score is linear logit, calibrated_probability is sigmoid(raw_score / temperature)
        self.assertNotEqual(res["raw_score"], res["calibrated_probability"])
        self.assertEqual(res["calibration_status"], "not_calibrated")
        self.assertEqual(res["verdict"], "not_calibrated")

    def test_calibrate_model_and_checkpoint_persistence(self):
        # Create audio files
        (self.root / "real_1.wav").write_bytes(make_wav([500] * 100))
        (self.root / "real_2.wav").write_bytes(make_wav([500] * 100))
        (self.root / "synth_1.wav").write_bytes(make_wav([1000] * 100))
        (self.root / "synth_2.wav").write_bytes(make_wav([1000] * 100))

        manifest = CorpusManifest((
            self.sample("real_1", is_synthetic=False, split="validation"),
            self.sample("real_2", is_synthetic=False, split="validation"),
            self.sample("synth_1", is_synthetic=True, split="validation"),
            self.sample("synth_2", is_synthetic=True, split="validation"),
        ))

        detector = AudioDetector(weights=(0.1, 0.2, -0.1, 0.05), bias=0.0)

        # Calibrate model on validation manifest
        calibrated = calibrate_model(detector, manifest, self.root, target_operating_point="fpr_1%")
        self.assertEqual(calibrated.threshold_config.calibration_status, "calibrated")

        audio = make_wav([800] * 100)
        res = calibrated.detect(audio)
        self.assertEqual(res["calibration_status"], "calibrated")
        self.assertIn(res["verdict"], {"consistent_with_human", "inconclusive", "likely_synthetic"})
        self.assertIsNotNone(res["operating_point_thresholds"])
        self.assertIsNotNone(res["thresholds"])

        # Save checkpoint
        ckpt_path = self.root / "calibrated_ckpt.json"
        save_checkpoint(calibrated, {"benchmark": "phase3-v1"}, ckpt_path)

        # Load checkpoint
        loaded = load_checkpoint(ckpt_path)
        self.assertEqual(loaded.threshold_config.calibration_status, "calibrated")

        res_loaded = loaded.detect(audio)
        self.assertEqual(res, res_loaded)
