"""Validate PandaMIND's local corpus manifest and print a compact summary."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from audio_detection.data.manifest import CorpusManifest, validate_corpus_audio
from audio_detection.data.splits import assert_no_leakage


def _counts(samples, field):
    return dict(sorted(Counter(getattr(sample, field) for sample in samples).items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/corpus.jsonl"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--held-out", type=Path, default=Path("src/audio_detection/config/held_out_generators.json"))
    args = parser.parse_args()
    manifest = CorpusManifest.load_jsonl(args.manifest)
    held_out = set(__import__("json").loads(args.held_out.read_text(encoding="utf8"))["generators"])
    assert_no_leakage(manifest, held_out)
    result = validate_corpus_audio(manifest, args.root)
    samples = manifest.samples
    print(f"total: {len(samples)}")
    print(f"real: {sum(not sample.is_synthetic for sample in samples)}")
    print(f"synthetic: {sum(sample.is_synthetic for sample in samples)}")
    for label, field in (("language", "language"), ("generator", "generator"), ("degradation", "degradation"), ("split", "split")):
        print(f"{label}: {_counts(samples, field)}")
    print(f"validation: passed={result.passed} failed={result.failed}")
    for issue in result.issues:
        print(f"  {issue.sample_id}: {issue.code}: {issue.detail}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
