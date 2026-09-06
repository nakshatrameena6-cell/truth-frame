"""Run Phase 5 evaluation of trained baseline on Phase 3 benchmark slices."""
from __future__ import annotations

from pathlib import Path

from audio_detection.data import CorpusManifest
from audio_detection.training.trainer import load_checkpoint
from audio_detection.evaluation import run_phase5_evaluation, save_evaluation_report


def main() -> None:
    ckpt_path = Path("reports/checkpoints/phase4_baseline.json")
    manifest_path = Path("data/manifests/corpus.jsonl")
    held_out_path = Path("src/audio_detection/config/held_out_generators.json")
    report_path = Path("reports/benchmark/phase5_baseline_eval.json")

    print(f"Loading Phase 4 baseline model from {ckpt_path}...")
    detector = load_checkpoint(ckpt_path)
    manifest = CorpusManifest.load_jsonl(manifest_path)
    print(f"Loaded corpus manifest with {len(manifest.samples)} samples.")

    print("Running Phase 5 benchmark evaluation...")
    results = run_phase5_evaluation(detector, manifest, Path("."), held_out_path)

    for name, res in results.items():
        if res.status == "evaluated":
            m = res.record
            print(f"[{name}] EVALUATED: EER={m.eer:.4f}, TPR@0.1%={m.tpr_at_0_1pct_fpr:.4f}, TPR@1%={m.tpr_at_1pct_fpr:.4f}, TPR@5%={m.tpr_at_5pct_fpr:.4f}, ECE={m.ece:.4f} (count={m.count})")
        else:
            print(f"[{name}] NOT EVALUABLE: reason='{res.reason}'")

    save_evaluation_report(results, report_path)
    print(f"Evaluation report saved to {report_path}")


if __name__ == "__main__":
    main()
