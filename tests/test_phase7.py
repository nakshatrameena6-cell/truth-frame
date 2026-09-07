import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audio_detection.calibration.calibrator import calibrate_model
from audio_detection.data import (
    CorpusManifest,
    Sample,
    assert_no_leakage,
    validate_corpus_audio,
)
from audio_detection.training.trainer import train_model


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


class Phase7IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_corpus_integrity_rejects_conflicting_label_duplicates(self):
        wav_bytes = make_wav([500] * 100)
        (self.root / "real.wav").write_bytes(wav_bytes)
        (self.root / "fake_synth.wav").write_bytes(wav_bytes)

        manifest = CorpusManifest((
            Sample(
                sample_id="real-01", source_id="src1", speaker_id="spk1",
                language="hi", is_synthetic=False, generator="human",
                audio_path="real.wav", degradation="clean", sample_rate=8000,
                channels=1, split="train",
            ),
            Sample(
                sample_id="synth-01", source_id="src2", speaker_id="spk2",
                language="hi", is_synthetic=True, generator="elevenlabs_v3",
                audio_path="fake_synth.wav", degradation="clean", sample_rate=8000,
                channels=1, split="train",
            ),
        ))

        res = validate_corpus_audio(manifest, self.root)
        self.assertEqual(res.failed, 1)
        self.assertTrue(any(issue.code == "conflicting_label_duplicate" for issue in res.issues))

    def test_corpus_integrity_rejects_conflicting_generator_duplicates(self):
        wav_bytes = make_wav([500] * 100)
        (self.root / "gen1.wav").write_bytes(wav_bytes)
        (self.root / "gen2.wav").write_bytes(wav_bytes)

        manifest = CorpusManifest((
            Sample(
                sample_id="s1", source_id="src1", speaker_id="spk1",
                language="en", is_synthetic=True, generator="elevenlabs_v3",
                audio_path="gen1.wav", degradation="clean", sample_rate=8000,
                channels=1, split="train",
            ),
            Sample(
                sample_id="s2", source_id="src2", speaker_id="spk2",
                language="en", is_synthetic=True, generator="pending_unresolved",
                audio_path="gen2.wav", degradation="clean", sample_rate=8000,
                channels=1, split="train",
            ),
        ))

        res = validate_corpus_audio(manifest, self.root)
        self.assertEqual(res.failed, 1)
        self.assertTrue(any(issue.code == "conflicting_generator_duplicate" for issue in res.issues))

    def test_legitimate_same_class_derived_degradation_passes_validation(self):
        clean_wav = make_wav([500] * 100)
        g711_wav = make_wav([490] * 100)  # different bytes
        (self.root / "real_clean.wav").write_bytes(clean_wav)
        (self.root / "real_g711.wav").write_bytes(g711_wav)

        manifest = CorpusManifest((
            Sample(
                sample_id="real-clean", source_id="src1", speaker_id="spk1",
                language="hi", is_synthetic=False, generator="human",
                audio_path="real_clean.wav", degradation="clean", sample_rate=8000,
                channels=1, split="train",
            ),
            Sample(
                sample_id="real-g711", source_id="src1", speaker_id="spk1",
                language="hi", is_synthetic=False, generator="human",
                audio_path="real_g711.wav", degradation="g711_8khz", sample_rate=8000,
                channels=1, split="train",
            ),
        ))

        res = validate_corpus_audio(manifest, self.root)
        self.assertTrue(res.ok)
        self.assertEqual(res.passed, 2)

    def test_verified_authentic_corpus_manifest_properties(self):
        manifest_path = Path("data/manifests/corpus.jsonl")
        held_out_path = Path("src/audio_detection/config/held_out_generators.json")

        manifest = CorpusManifest.load_jsonl(manifest_path)
        val_res = validate_corpus_audio(manifest, Path("."))
        self.assertTrue(val_res.ok)

        with open(held_out_path, "r", encoding="utf-8") as f:
            held_out_cfg = json.load(f)
        held_out_gens = set(held_out_cfg.get("generators", []))

        assert_no_leakage(manifest, held_out_gens)

    def test_refuses_calibration_when_validation_data_is_absent(self):
        manifest_path = Path("data/manifests/corpus.jsonl")
        held_out_path = Path("src/audio_detection/config/held_out_generators.json")
        full_manifest = CorpusManifest.load_jsonl(manifest_path)
        no_val_manifest = CorpusManifest(tuple(s for s in full_manifest.samples if s.split != "validation"))

        detector = train_model(no_val_manifest, Path("."), held_out_path, epochs=2, seed=42)
        detector = calibrate_model(detector, no_val_manifest, Path("."), target_operating_point="fpr_1%")

        self.assertEqual(detector.threshold_config.calibration_status, "not_calibrated")
        self.assertEqual(detector.threshold_config.calibration_reason, "insufficient_validation_data")

    def test_calibrates_successfully_when_validation_data_is_present(self):
        manifest_path = Path("data/manifests/corpus.jsonl")
        held_out_path = Path("src/audio_detection/config/held_out_generators.json")
        manifest = CorpusManifest.load_jsonl(manifest_path)

        detector = train_model(manifest, Path("."), held_out_path, epochs=2, seed=42)
        detector = calibrate_model(detector, manifest, Path("."), target_operating_point="fpr_1%")

        self.assertEqual(detector.threshold_config.calibration_status, "calibrated")

