import io
import struct
import unittest
import wave
from dataclasses import replace
from unittest.mock import patch
from audio_detection.data import Sample, CorpusManifest, assign_splits, assert_no_leakage
from audio_detection.detector import AudioDetector
from audio_detection.evaluation import evaluate

def make_wav(samples, rate=8000):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(rate)
        output.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return stream.getvalue()

class Phase0Tests(unittest.TestCase):
    def sample(self, ident, source, speaker, generator):
        return Sample(ident, source, speaker, "hi", True, generator, "x.wav", "clean", 16000, 1)
    def test_heldout_is_test_and_no_leakage(self):
        manifest = assign_splits([self.sample("1", "a", "p", "held"), self.sample("2", "b", "q", "train")], {"held"})
        self.assertEqual(manifest.samples[0].split, "test")
    def test_same_source_never_crosses_split(self):
        manifest = assign_splits([self.sample("1", "a", "p", "x"), self.sample("2", "a", "p", "x")], set())
        self.assertEqual(manifest.samples[0].split, manifest.samples[1].split)
    def test_manual_source_leakage_is_rejected(self):
        left = self.sample("1", "shared", "p", "x").__class__("1", "shared", "p", "hi", True, "x", "x.wav", "clean", 16000, 1, "train")
        right = self.sample("2", "shared", "p", "x").__class__("2", "shared", "p", "hi", True, "x", "x.wav", "clean", 16000, 1, "test")
        with self.assertRaises(ValueError): assert_no_leakage(CorpusManifest((left, right)), set())
    def test_split_bucket_excludes_generator(self):
        samples = [self.sample("1", "source", "speaker", "g1"), self.sample("2", "source", "speaker", "g2")]
        with patch("audio_detection.data.splits._bucket", return_value=.1) as bucket:
            assign_splits(samples, set())
        self.assertEqual([call.args[0] for call in bucket.call_args_list], ["source|speaker", "source|speaker"])
    def test_seen_generator_may_span_splits(self):
        samples = (
            replace(self.sample("1", "source-1", "speaker-1", "seen"), split="train"),
            replace(self.sample("2", "source-2", "speaker-2", "seen"), split="validation"),
            replace(self.sample("3", "source-3", "speaker-3", "seen"), split="test"),
        )
        assert_no_leakage(CorpusManifest(samples), set())
    def test_held_out_and_seen_generator_pools_are_disjoint(self):
        samples = (
            replace(self.sample("1", "shared", "held-speaker", "held"), split="test"),
            replace(self.sample("2", "shared", "seen-speaker", "seen"), split="test"),
        )
        with self.assertRaises(ValueError): assert_no_leakage(CorpusManifest(samples), {"held"})
    def test_deterministic_detector_contract(self):
        detector = AudioDetector(weights=(0, 1, 0, 0)); result = detector.detect(make_wav([1000] * 2000))
        self.assertEqual(result, detector.detect(make_wav([1000] * 2000)))
        self.assertEqual(set(result), {"score", "segments", "model_version", "confidence"})
    def test_metrics_are_identified(self):
        record = evaluate([0, 0, 1, 1], [.1, .2, .8, .9], dataset="d", split="test", language="hi", generator="g", channel_condition="clean", degradation="none", model_version="v")
        self.assertEqual(record.eer, 0); self.assertEqual(record.language, "hi")
