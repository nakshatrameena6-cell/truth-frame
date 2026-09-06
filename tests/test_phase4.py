import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audio_detection.data.manifest import CorpusManifest, Sample
from audio_detection.training.trainer import train_model, save_checkpoint, load_checkpoint, TrainingDataError

def make_wav(samples, rate=8000):
    import io, struct, wave
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return stream.getvalue()

class Phase4Tests(unittest.TestCase):
    def sample(self, ident, source, speaker, is_synthetic=False, generator="seen", split="train", **overrides):
        values = dict(
            sample_id=ident, source_id=source, speaker_id=speaker,
            language="hi", is_synthetic=is_synthetic, generator=generator,
            audio_path=f"{ident}.wav", degradation="clean", sample_rate=8000,
            channels=1, split=split,
        )
        values.update(overrides)
        return Sample(**values)

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.held_out_path = self.root / "held_out.json"
        with open(self.held_out_path, "w") as f:
            json.dump({"generators": ["held_gen"]}, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_training_pipeline_and_checkpoints(self):
        # Create audio files
        (self.root / "real.wav").write_bytes(make_wav([500] * 100))
        (self.root / "synth.wav").write_bytes(make_wav([1000] * 100))

        manifest = CorpusManifest((
            self.sample("real", "s1", "sp1", is_synthetic=False),
            self.sample("synth", "s2", "sp2", is_synthetic=True, generator="gen_x"),
        ))

        # Train model
        detector = train_model(manifest, self.root, self.held_out_path, epochs=2)
        self.assertEqual(detector.model_version, "phase4-baseline")
        self.assertTrue(any(w != 0.0 for w in detector.weights))

        # Test deterministic inference
        audio = make_wav([800] * 100)
        result1 = detector.detect(audio)
        result2 = detector.detect(audio)
        self.assertEqual(result1, result2)

        # Save checkpoint
        ckpt_path = self.root / "ckpt.json"
        save_checkpoint(detector, {"epochs": 2}, ckpt_path)

        # Load checkpoint
        loaded = load_checkpoint(ckpt_path)
        self.assertEqual(loaded.model_version, detector.model_version)
        self.assertEqual(loaded.weights, detector.weights)
        self.assertEqual(loaded.bias, detector.bias)
        
        # Inference with loaded model
        self.assertEqual(loaded.detect(audio), result1)

    def test_training_data_validation_fails_on_single_class(self):
        (self.root / "real.wav").write_bytes(make_wav([500] * 100))
        manifest = CorpusManifest((
            self.sample("real", "s1", "sp1", is_synthetic=False),
        ))
        
        with self.assertRaisesRegex(TrainingDataError, "Insufficient labeled data"):
            train_model(manifest, self.root, self.held_out_path)

    def test_held_out_generator_protection(self):
        (self.root / "real.wav").write_bytes(make_wav([500] * 100))
        (self.root / "synth.wav").write_bytes(make_wav([1000] * 100))
        
        # held_gen is in self.held_out_path
        manifest = CorpusManifest((
            self.sample("real", "s1", "sp1", is_synthetic=False),
            self.sample("synth", "s2", "sp2", is_synthetic=True, generator="held_gen"),
        ))
        
        with self.assertRaisesRegex(TrainingDataError, "Held-out generator 'held_gen' found in training data"):
            train_model(manifest, self.root, self.held_out_path)
