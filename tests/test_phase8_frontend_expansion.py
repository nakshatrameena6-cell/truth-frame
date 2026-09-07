"""Regression tests for Part H: Frontend Fix, Classical Baseline, and Authentic Corpus Expansion."""
from __future__ import annotations

import io
import math
import struct
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from audio_detection.data import CorpusManifest, Sample, assert_no_leakage, assign_splits, validate_corpus_audio
from audio_detection.detector import AudioDetector
from audio_detection.models.frontend import HybridFrontend


def make_wav_bytes(samples: list[int], rate: int = 16000) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return stream.getvalue()


class TestPhase8FrontendAndCorpus(unittest.TestCase):

    def setUp(self):
        self.frontend = HybridFrontend()

    def test_amplitude_normalization_invariance(self):
        """Test that peak scaling does not change extracted feature vectors."""
        rate = 16000
        t = np.linspace(0, 0.5, int(rate * 0.5), endpoint=False)
        signal = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.cos(2 * np.pi * 880 * t)

        feats_1x = self.frontend.embed(signal, rate)
        feats_5x = self.frontend.embed(signal * 3.0, rate)
        feats_01x = self.frontend.embed(signal * 0.1, rate)

        np.testing.assert_allclose(feats_1x, feats_5x, rtol=1e-5, atol=1e-5)
        np.testing.assert_allclose(feats_1x, feats_01x, rtol=1e-5, atol=1e-5)

    def test_deterministic_feature_extraction(self):
        """Test that feature extraction is completely deterministic across repeated calls."""
        rate = 16000
        t = np.linspace(0, 0.5, int(rate * 0.5), endpoint=False)
        signal = np.sin(2 * np.pi * 300 * t)

        f1 = self.frontend.embed(signal, rate)
        f2 = self.frontend.embed(signal, rate)

        self.assertEqual(f1, f2)

    def test_feature_dimensionality(self):
        """Test that feature vector has exact dimension of 10."""
        rate = 16000
        signal = np.random.randn(8000)
        feats = self.frontend.embed(signal, rate)
        self.assertEqual(len(feats), 10)

        detector = AudioDetector()
        self.assertEqual(len(detector.weights), 10)

    def test_source_speaker_grouping(self):
        """Test connected component split isolation for source/speaker groups."""
        samples = [
            Sample("s1", "src1", "spk1", "en", False, "human", "p1.wav", "clean", 16000, 1, "unassigned"),
            Sample("s2", "src1", "spk1", "en", False, "human", "p2.wav", "g711_8khz", 8000, 1, "unassigned"),
            Sample("s3", "src2", "spk2", "en", True, "google_tts", "p3.wav", "clean", 16000, 1, "unassigned"),
            Sample("s4", "src2", "spk2", "en", True, "google_tts", "p4.wav", "g711_8khz", 8000, 1, "unassigned"),
        ]
        manifest = assign_splits(samples, held_out_generators={"edge_tts_neural"})
        
        # Verify src1/spk1 degradations remain in the exact same split
        splits_src1 = {s.split for s in manifest.samples if s.source_id == "src1"}
        self.assertEqual(len(splits_src1), 1)

    def test_duplicate_content_protection(self):
        """Test that identical audio paths are rejected during manifest validation."""
        m = CorpusManifest((
            Sample("s1", "src1", "spk1", "en", False, "human", "audio/a.wav", "clean", 16000, 1, "train"),
            Sample("s2", "src2", "spk2", "en", False, "human", "audio/a.wav", "clean", 16000, 1, "train"),
        ))
        with self.assertRaisesRegex(ValueError, "audio_path"):
            from audio_detection.data.manifest import validate_manifest
            validate_manifest(m)

    def test_held_out_generator_isolation(self):
        """Test that held-out generators are strictly isolated to the test split."""
        samples = [
            Sample("s1", "src_seen", "spk_seen", "en", True, "google_tts", "p1.wav", "clean", 16000, 1, "unassigned"),
            Sample("s2", "src_held", "spk_held", "en", True, "edge_tts_neural", "p2.wav", "clean", 16000, 1, "unassigned"),
        ]
        manifest = assign_splits(samples, held_out_generators={"edge_tts_neural"})
        assert_no_leakage(manifest, {"edge_tts_neural"})

        held_splits = {s.split for s in manifest.samples if s.generator == "edge_tts_neural"}
        self.assertEqual(held_splits, {"test"})


if __name__ == "__main__":
    unittest.main()
