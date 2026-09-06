"""Phase 5 baseline evaluation suite for Phase 3 benchmark (phase3-v1)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from audio_detection.data import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.evaluation.metrics import MetricRecord, evaluate, to_dict


@dataclass(frozen=True)
class SliceResult:
    slice_name: str
    status: str  # "evaluated" or "not_evaluable"
    reason: str | None
    record: MetricRecord | None

    def to_dict(self) -> dict:
        return {
            "slice_name": self.slice_name,
            "status": self.status,
            "reason": self.reason,
            "metrics": to_dict(self.record) if self.record else None,
        }


def run_phase5_evaluation(
    detector: AudioDetector,
    manifest: CorpusManifest,
    audio_root: Path,
    held_out_config_path: Path,
) -> dict[str, SliceResult]:
    """Run Phase 5 evaluation across frozen Phase 3 slices."""
    with open(held_out_config_path, "r", encoding="utf-8") as f:
        held_out_cfg = json.load(f)
    held_out_gens = set(held_out_cfg.get("generators", []))

    evaluated_rows = []
    for sample in manifest.samples:
        path = audio_root / sample.audio_path
        with open(path, "rb") as f:
            audio_bytes = f.read()
        res = detector.detect(audio_bytes)
        evaluated_rows.append({
            "sample": sample,
            "label": 1 if sample.is_synthetic else 0,
            "score": res["score"],
        })

    results: dict[str, SliceResult] = {}

    # 1. in-domain clean
    in_domain_clean = [
        r for r in evaluated_rows
        if r["sample"].degradation == "clean" and r["sample"].generator not in held_out_gens
    ]
    results["in-domain clean"] = _evaluate_group(
        in_domain_clean, "in-domain clean", detector.model_version
    )

    # 2. cross-generator clean
    cross_gen_clean = [
        r for r in evaluated_rows
        if r["sample"].degradation == "clean" and r["sample"].generator in held_out_gens
    ]
    results["cross-generator clean"] = _evaluate_group(
        cross_gen_clean, "cross-generator clean", detector.model_version,
        empty_reason="no_held_out_generator_samples"
    )

    # 3. cross-generator telecom
    telecom_degradations = {"g711_8khz", "amr_nb", "whatsapp_opus"}
    cross_gen_telecom = [
        r for r in evaluated_rows
        if r["sample"].degradation in telecom_degradations and r["sample"].generator in held_out_gens
    ]
    results["cross-generator telecom"] = _evaluate_group(
        cross_gen_telecom, "cross-generator telecom", detector.model_version,
        empty_reason="no_held_out_telecom_samples"
    )

    # 4. language fairness
    for lang in ("hi", "ta", "en", "hinglish"):
        lang_group = [r for r in evaluated_rows if r["sample"].language == lang]
        slice_key = f"language fairness ({lang})"
        results[slice_key] = _evaluate_group(
            lang_group, slice_key, detector.model_version,
            empty_reason=f"no_samples_for_language_{lang}"
        )

    return results


def _evaluate_group(
    group: list[dict],
    slice_name: str,
    model_version: str,
    empty_reason: str = "no_data",
) -> SliceResult:
    if not group:
        return SliceResult(slice_name, "not_evaluable", empty_reason, None)

    labels = [r["label"] for r in group]
    scores = [r["score"] for r in group]

    if len(set(labels)) < 2:
        present_class = "synthetic_only" if labels[0] == 1 else "real_only"
        return SliceResult(
            slice_name,
            "not_evaluable",
            f"single_class_only_{present_class}_requires_both_classes",
            None,
        )

    rec = evaluate(
        labels,
        scores,
        dataset="corpus",
        split="mixed",
        language="mixed",
        generator="mixed",
        channel_condition="mixed",
        degradation="mixed",
        model_version=model_version,
    )
    return SliceResult(slice_name, "evaluated", None, rec)


def save_evaluation_report(results: dict[str, SliceResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = {k: v.to_dict() for k, v in results.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
