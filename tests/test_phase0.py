import io
import struct
import unittest
import wave
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from audio_detection.data import CorpusManifest, Sample, assert_no_leakage, assign_splits, validate_corpus_audio
from audio_detection.detector import AudioDetector
from audio_detection.evaluation import evaluate


def make_wav(samples, rate=8000):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return stream.getvalue()


class Phase1Tests(unittest.TestCase):
    def sample(self, ident, source, speaker, generator="seen", **overrides):
        values = dict(
            sample_id=ident, source_id=source, speaker_id=speaker,
            language="hi", is_synthetic=True, generator=generator,
            audio_path="x.wav", degradation="clean", sample_rate=16000,
            channels=1, split="unassigned",
        )
        values.update(overrides)
        return Sample(**values)

    def test_manifest_rejects_missing_unknown_and_invalid_values(self):
        valid = asdict(self.sample("1", "source", "speaker"))
        for mutation in (
            lambda row: row.pop("language"),
            lambda row: row.update(extra="unexpected"),
            lambda row: row.update(is_synthetic="true"),
            lambda row: row.update(sample_rate=0),
            lambda row: row.update(split="development"),
            lambda row: row.update(generator=""),
        ):
            row = valid.copy()
            mutation(row)
            with self.assertRaises(ValueError):
                Sample.from_dict(row)

    def test_manifest_rejects_duplicate_ids(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.jsonl"
            CorpusManifest((self.sample("same", "a", "p"), self.sample("same", "b", "q"))).write_jsonl(path)
            with self.assertRaisesRegex(ValueError, "duplicate sample_id"):
                CorpusManifest.load_jsonl(path)

    def test_manifest_rejects_duplicate_audio_paths(self):
        manifest = CorpusManifest((
            self.sample("one", "source-a", "speaker-a", audio_path="audio/one.wav"),
            self.sample("two", "source-b", "speaker-b", audio_path="audio/one.wav"),
        ))
        with self.assertRaisesRegex(ValueError, "audio_path"):
            from audio_detection.data.manifest import validate_manifest
            validate_manifest(manifest)

    def test_corpus_audio_validation_reports_metadata_and_signal_problems(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio").mkdir()
            (root / "audio" / "valid.wav").write_bytes(make_wav([500] * 100, rate=8000))
            (root / "audio" / "mismatch.wav").write_bytes(make_wav([500] * 100, rate=8000))
            (root / "audio" / "silent.wav").write_bytes(make_wav([0] * 100, rate=8000))
            (root / "audio" / "broken.wav").write_bytes(b"not a wav")
            manifest = CorpusManifest((
                self.sample("valid", "a", "p", audio_path="audio/valid.wav", sample_rate=8000),
                self.sample("missing", "b", "q", audio_path="audio/missing.wav"),
                self.sample("mismatch", "c", "r", audio_path="audio/mismatch.wav", sample_rate=16000),
                self.sample("silent", "d", "s", audio_path="audio/silent.wav", sample_rate=8000),
                self.sample("broken", "e", "t", audio_path="audio/broken.wav", sample_rate=8000),
                self.sample("escape", "f", "u", audio_path="../outside.wav"),
            ))
            result = validate_corpus_audio(manifest, root)
        self.assertEqual(result.checked, 6)
        self.assertEqual(result.passed, 1)
        self.assertEqual(result.failed, 5)
        self.assertEqual({issue.code for issue in result.issues}, {
            "missing_file", "sample_rate_mismatch", "near_empty_audio", "unreadable_audio", "path_outside_root",
        })

    def test_corpus_audio_validation_rejects_resolved_path_aliases(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio").mkdir()
            (root / "audio" / "voice.wav").write_bytes(make_wav([500] * 100, rate=8000))
            manifest = CorpusManifest((
                self.sample("one", "a", "p", audio_path="audio/voice.wav", sample_rate=8000),
                self.sample("two", "b", "q", audio_path="audio/../audio/voice.wav", sample_rate=8000),
            ))
            result = validate_corpus_audio(manifest, root)
        self.assertEqual(result.failed, 2)
        self.assertEqual({issue.code for issue in result.issues}, {"ambiguous_audio_path"})

    def test_splits_are_deterministic(self):
        samples = [self.sample("1", "a", "p"), self.sample("2", "b", "q")]
        self.assertEqual(assign_splits(samples, set(), seed="fixed"), assign_splits(samples, set(), seed="fixed"))

    def test_source_and_speaker_leakage_are_rejected(self):
        source_leak = CorpusManifest((
            self.sample("1", "shared-source", "p", split="train"),
            self.sample("2", "shared-source", "q", split="test"),
        ))
        speaker_leak = CorpusManifest((
            self.sample("1", "a", "shared-speaker", split="train"),
            self.sample("2", "b", "shared-speaker", split="validation"),
        ))
        with self.assertRaisesRegex(ValueError, "source_id leakage"):
            assert_no_leakage(source_leak, set())
        with self.assertRaisesRegex(ValueError, "speaker_id leakage"):
            assert_no_leakage(speaker_leak, set())

    def test_multi_speaker_source_is_assigned_as_one_group(self):
        manifest = assign_splits((
            self.sample("1", "shared-source", "speaker-a"),
            self.sample("2", "shared-source", "speaker-b"),
            self.sample("3", "other-source", "speaker-b"),
        ), set())
        self.assertEqual({sample.split for sample in manifest.samples}, {manifest.samples[0].split})

    def test_held_out_generators_are_test_only(self):
        manifest = assign_splits((
            self.sample("1", "held-source", "held-speaker", "held"),
            self.sample("2", "seen-source", "seen-speaker", "seen"),
        ), {"held"})
        self.assertEqual(manifest.samples[0].split, "test")
        self.assertNotIn("held", {sample.generator for sample in manifest.samples if sample.split in {"train", "validation"}})
        invalid = CorpusManifest((replace(manifest.samples[0], split="validation"), manifest.samples[1]))
        with self.assertRaisesRegex(ValueError, "held-out generators"):
            assert_no_leakage(invalid, {"held"})

    def test_detector_is_deterministic_with_stable_per_segment_shape(self):
        detector = AudioDetector(weights=(0, 1, 0, 0))
        result = detector.detect(make_wav([1000] * 2000))
        self.assertEqual(result, detector.detect(make_wav([1000] * 2000)))
        self.assertEqual(set(result), {"score", "segments", "model_version", "confidence"})
        self.assertEqual(result["model_version"], "phase0-untrained")
        self.assertTrue(result["segments"])
        self.assertEqual(set(result["segments"][0]), {"start_ms", "end_ms", "score"})

    def test_eer_and_tpr_at_one_percent_fpr(self):
        record = evaluate(
            [0, 0, 1, 1], [.1, .2, .8, .9],
            dataset="d", split="test", language="hi", generator="g",
            channel_condition="clean", degradation="none", model_version="v",
        )
        self.assertEqual(record.eer, 0.0)
        self.assertEqual(record.tpr_at_1pct_fpr, 1.0)

    def test_top_label_ece(self):
        record = evaluate(
            [0, 1], [.9, .9],
            dataset="d", split="test", language="hi", generator="g",
            channel_condition="clean", degradation="none", model_version="v",
        )
        self.assertAlmostEqual(record.ece, 0.4)

