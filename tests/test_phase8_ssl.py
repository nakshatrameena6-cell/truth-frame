"""Regression tests for Phase 8 SSL wav2vec2-base experiment."""
from __future__ import annotations

import io
import math
import struct
import unittest
import wave
from pathlib import Path

import numpy as np


def make_wav_bytes(samples: list[int], rate: int = 16000) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return stream.getvalue()


class TestSSLEmbedder(unittest.TestCase):
    """Test Wav2Vec2SSLEmbedder produces deterministic, correctly shaped embeddings."""

    @classmethod
    def setUpClass(cls):
        from audio_detection.models.ssl import Wav2Vec2SSLEmbedder
        cls.embedder = Wav2Vec2SSLEmbedder("facebook/wav2vec2-base")

    def test_embedding_dimension(self):
        """SSL embedder must produce exactly 768 dimensions."""
        rate = 16000
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1.0, rate)).tolist()
        emb = self.embedder(signal, rate)
        self.assertEqual(len(emb), 768)

    def test_deterministic_embedding(self):
        """SSL embedder must produce identical results on repeated calls."""
        rate = 16000
        signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
        emb1 = self.embedder(signal, rate)
        emb2 = self.embedder(signal, rate)
        self.assertEqual(emb1, emb2)

    def test_empty_input_returns_zeros(self):
        """SSL embedder must return 768 zeros for empty input."""
        emb = self.embedder([], 16000)
        self.assertEqual(len(emb), 768)
        self.assertTrue(all(v == 0.0 for v in emb))

    def test_resampling_8khz_to_16khz(self):
        """SSL embedder must handle 8kHz audio by resampling to 16kHz."""
        rate = 8000
        signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
        emb = self.embedder(signal, rate)
        self.assertEqual(len(emb), 768)
        # Should not be all zeros
        self.assertGreater(max(abs(v) for v in emb), 0.01)

    def test_peak_normalization(self):
        """SSL embedder should be invariant to input amplitude scaling."""
        rate = 16000
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, rate // 2))
        emb_1x = self.embedder(signal, rate)
        emb_5x = self.embedder(signal * 5.0, rate)
        np.testing.assert_allclose(emb_1x, emb_5x, rtol=1e-4, atol=1e-4)

    def test_offline_enforcement(self):
        """Wav2Vec2SSLEmbedder must work completely offline when local_dir is provided."""
        from audio_detection.models.ssl import Wav2Vec2SSLEmbedder
        from tempfile import TemporaryDirectory
        import os
        from unittest.mock import patch
        
        with TemporaryDirectory() as tmpdir:
            # First, download legitimately to temp dir to act as our local cache
            from transformers import AutoFeatureExtractor, AutoModel
            feat = AutoFeatureExtractor.from_pretrained("facebook/wav2vec2-base")
            model = AutoModel.from_pretrained("facebook/wav2vec2-base")
            feat.save_pretrained(tmpdir)
            model.save_pretrained(tmpdir)
            
            # Force it to ignore global cache by pointing HF_HOME to a missing dir
            with patch.dict(os.environ, {"HF_HOME": os.path.join(tmpdir, "empty_cache")}):
                # Block the network. We mock both requests and httpx which transformers uses
                with patch("requests.Session.request", side_effect=IOError("Network is disabled")), \
                     patch("httpx.Client.send", side_effect=IOError("Network is disabled")):
                    # Should succeed because local_files_only=True bypasses the network completely
                    embedder = Wav2Vec2SSLEmbedder(local_dir=tmpdir)
                    rate = 16000
                    signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
                    emb = embedder(signal, rate)
                    self.assertEqual(len(emb), 768)
                    
                    # Should fail if we try to instantiate from hub with network blocked
                    with self.assertRaises(Exception):
                        Wav2Vec2SSLEmbedder("facebook/wav2vec2-base")


class TestHybridFrontendWithSSL(unittest.TestCase):
    """Test HybridFrontend dimension with and without SSL embedder."""

    def test_classical_only_dimension(self):
        """Without SSL embedder, HybridFrontend produces 10D features."""
        from audio_detection.models.frontend import HybridFrontend
        frontend = HybridFrontend(ssl_embedder=None)
        rate = 16000
        signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
        feats = frontend.embed(signal, rate)
        self.assertEqual(len(feats), 10)

    def test_hybrid_dimension(self):
        """With SSL embedder, HybridFrontend produces 778D (10 + 768)."""
        from audio_detection.models.frontend import HybridFrontend
        from audio_detection.models.ssl import Wav2Vec2SSLEmbedder
        ssl = Wav2Vec2SSLEmbedder("facebook/wav2vec2-base")
        frontend = HybridFrontend(ssl_embedder=ssl)
        rate = 16000
        signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
        feats = frontend.embed(signal, rate)
        self.assertEqual(len(feats), 778)

    def test_hybrid_deterministic(self):
        """Hybrid features must be deterministic."""
        from audio_detection.models.frontend import HybridFrontend
        from audio_detection.models.ssl import Wav2Vec2SSLEmbedder
        ssl = Wav2Vec2SSLEmbedder("facebook/wav2vec2-base")
        frontend = HybridFrontend(ssl_embedder=ssl)
        rate = 16000
        signal = np.sin(2 * np.pi * 300 * np.linspace(0, 0.5, rate // 2)).tolist()
        f1 = frontend.embed(signal, rate)
        f2 = frontend.embed(signal, rate)
        self.assertEqual(f1, f2)


class TestSSLDetectorWeights(unittest.TestCase):
    """Test that AudioDetector correctly works with 778D weight vectors."""

    def test_detector_with_778d_weights(self):
        """AudioDetector must accept and use 778D weights."""
        from audio_detection.detector import AudioDetector
        weights = tuple([0.01] * 778)
        det = AudioDetector(
            model_version="test-ssl",
            weights=weights,
            bias=0.0,
        )
        self.assertEqual(len(det.weights), 778)
        self.assertEqual(det.model_version, "test-ssl")

    def test_checkpoint_round_trip(self):
        """Checkpoint save/load must preserve 778D weights exactly."""
        from audio_detection.detector import AudioDetector
        from audio_detection.training.trainer import save_checkpoint, load_checkpoint
        from tempfile import TemporaryDirectory

        weights = tuple([float(i) * 0.001 for i in range(778)])
        det = AudioDetector(
            model_version="test-ssl-ckpt",
            weights=weights,
            bias=-0.5,
        )

        with TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "test_ckpt.json"
            save_checkpoint(det, {"test": True}, ckpt_path)
            reloaded = load_checkpoint(ckpt_path)

        self.assertEqual(reloaded.weights, det.weights)
        self.assertAlmostEqual(reloaded.bias, det.bias, places=6)
        self.assertEqual(reloaded.model_version, det.model_version)


class TestSSLModuleExports(unittest.TestCase):
    """Test that SSL module is properly exported from the models package."""

    def test_import_from_models(self):
        """Wav2Vec2SSLEmbedder must be importable from audio_detection.models."""
        from audio_detection.models import Wav2Vec2SSLEmbedder
        self.assertTrue(callable(Wav2Vec2SSLEmbedder))

    def test_import_from_ssl(self):
        """Wav2Vec2SSLEmbedder must be importable from audio_detection.models.ssl."""
        from audio_detection.models.ssl import Wav2Vec2SSLEmbedder
        self.assertTrue(callable(Wav2Vec2SSLEmbedder))


if __name__ == "__main__":
    unittest.main()
