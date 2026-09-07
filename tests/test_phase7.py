import json
import unittest
from pathlib import Path

from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data import CorpusManifest, assert_no_leakage
from audio_detection.detector import AudioDetector
from audio_detection.evaluation import run_phase5_evaluation
from audio_detection.training.trainer import load_checkpoint, train_model


class Phase7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_path = Path("data/manifests/corpus.jsonl")
        cls.held_out_path = Path("src/audio_detection/config/held_out_generators.json")
        cls.audio_root = Path(".")
        cls.manifest = CorpusManifest.load_jsonl(cls.manifest_path)

        with open(cls.held_out_path, "r", encoding="utf-8") as f:
            held_out_cfg = json.load(f)
        cls.held_out_gens = set(held_out_cfg.get("generators", []))

    def test_corpus_size_and_split_distribution(self):
        self.assertGreaterEqual(len(self.manifest.samples), 50)

        splits = {}
        for s in self.manifest.samples:
            splits[s.split] = splits.get(s.split, 0) + 1

        self.assertIn("train", splits)
        self.assertIn("validation", splits)
        self.assertIn("test", splits)

        self.assertGreater(splits["train"], 0)
        self.assertGreater(splits["validation"], 0)
        self.assertGreater(splits["test"], 0)

    def test_validation_contains_both_real_and_synthetic_classes(self):
        val_samples = [s for s in self.manifest.samples if s.split == "validation"]
        val_labels = {s.is_synthetic for s in val_samples}
        self.assertEqual(val_labels, {False, True})

    def test_held_out_generators_are_strictly_isolated_in_test_split(self):
        held_out_samples = [
            s for s in self.manifest.samples
            if s.is_synthetic and s.generator in self.held_out_gens
        ]
        self.assertTrue(held_out_samples)
        for s in held_out_samples:
            self.assertEqual(s.split, "test")

        non_test_gens = {
            s.generator for s in self.manifest.samples
            if s.split in {"train", "validation"}
        }
        self.assertFalse(non_test_gens & self.held_out_gens)

    def test_no_source_or_speaker_leakage_across_splits(self):
        assert_no_leakage(self.manifest, self.held_out_gens)

    def test_calibration_fits_and_derives_thresholds_on_validation_set(self):
        detector = train_model(self.manifest, self.audio_root, self.held_out_path, epochs=5, seed=42)
        detector = calibrate_model(detector, self.manifest, self.audio_root, target_operating_point="fpr_1%")

        self.assertEqual(detector.threshold_config.calibration_status, "calibrated")
        self.assertIsNone(detector.threshold_config.calibration_reason)
        self.assertIsNotNone(detector.threshold_config.operating_point_thresholds)
        self.assertIsNotNone(detector.threshold_config.low_threshold)
        self.assertIsNotNone(detector.threshold_config.high_threshold)
        self.assertLess(detector.threshold_config.low_threshold, detector.threshold_config.high_threshold)

    def test_evaluation_slice_coverage_and_unsupported_language_behavior(self):
        detector = load_checkpoint(Path("reports/checkpoints/phase4_baseline.json"))
        results = run_phase5_evaluation(detector, self.manifest, self.audio_root, self.held_out_path)

        self.assertEqual(results["in-domain clean"].status, "evaluated")
        self.assertEqual(results["cross-generator clean"].status, "evaluated")
        self.assertEqual(results["cross-generator telecom"].status, "evaluated")
        self.assertEqual(results["language fairness (hi)"].status, "evaluated")
        self.assertEqual(results["language fairness (ta)"].status, "evaluated")
        self.assertEqual(results["language fairness (en)"].status, "evaluated")

        # Hinglish remains explicitly not_evaluable as legitimate Hinglish data is unavailable
        self.assertEqual(results["language fairness (hinglish)"].status, "not_evaluable")
        self.assertEqual(results["language fairness (hinglish)"].reason, "no_samples_for_language_hinglish")
