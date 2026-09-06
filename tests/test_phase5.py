import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audio_detection.data.manifest import CorpusManifest, Sample
from audio_detection.detector import AudioDetector
from audio_detection.evaluation import run_phase5_evaluation, save_evaluation_report, SliceResult

def make_wav(samples, rate=8000):
    import io, struct, wave
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<%dh" % len(samples), *samples))
    return stream.getvalue()


class Phase5Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.held_out_path = self.root / "held_out.json"
        with open(self.held_out_path, "w", encoding="utf-8") as f:
            json.dump({"generators": ["held_gen"]}, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def sample(self, ident, source, speaker, is_synthetic=False, generator="seen", split="train", lang="hi", deg="clean", **overrides):
        values = dict(
            sample_id=ident, source_id=source, speaker_id=speaker,
            language=lang, is_synthetic=is_synthetic, generator=generator,
            audio_path=f"{ident}.wav", degradation=deg, sample_rate=8000,
            channels=1, split=split,
        )
        values.update(overrides)
        return Sample(**values)

    def test_evaluation_slices_status_and_determinism(self):
        (self.root / "real_hi.wav").write_bytes(make_wav([500] * 100))
        (self.root / "synth_hi.wav").write_bytes(make_wav([1000] * 100))

        manifest = CorpusManifest((
            self.sample("real_hi", "s1", "sp1", is_synthetic=False, lang="hi"),
            self.sample("synth_hi", "s2", "sp2", is_synthetic=True, generator="gen_x", lang="hi"),
        ))

        detector = AudioDetector(model_version="phase4-baseline", weights=(0.1, 0.2, -0.1, 0.05), bias=0.0)

        # Run evaluation twice to check determinism
        res1 = run_phase5_evaluation(detector, manifest, self.root, self.held_out_path)
        res2 = run_phase5_evaluation(detector, manifest, self.root, self.held_out_path)

        self.assertEqual(list(res1.keys()), list(res2.keys()))
        for k in res1:
            self.assertEqual(res1[k].status, res2[k].status)
            self.assertEqual(res1[k].reason, res2[k].reason)

        # in-domain clean should be evaluated since both real and synthetic exist for clean
        self.assertEqual(res1["in-domain clean"].status, "evaluated")
        self.assertIsNotNone(res1["in-domain clean"].record)
        self.assertEqual(res1["in-domain clean"].record.count, 2)

        # cross-generator slices should be not_evaluable
        self.assertEqual(res1["cross-generator clean"].status, "not_evaluable")
        self.assertEqual(res1["cross-generator clean"].reason, "no_held_out_generator_samples")
        self.assertEqual(res1["cross-generator telecom"].status, "not_evaluable")
        self.assertEqual(res1["cross-generator telecom"].reason, "no_held_out_telecom_samples")

        # language fairness (hi) should be evaluated
        self.assertEqual(res1["language fairness (hi)"].status, "evaluated")

        # language fairness (ta) should be not_evaluable (no samples)
        self.assertEqual(res1["language fairness (ta)"].status, "not_evaluable")
        self.assertEqual(res1["language fairness (ta)"].reason, "no_samples_for_language_ta")

        # Save and verify report
        report_path = self.root / "report.json"
        save_evaluation_report(res1, report_path)
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("in-domain clean", data)
        self.assertEqual(data["in-domain clean"]["status"], "evaluated")
