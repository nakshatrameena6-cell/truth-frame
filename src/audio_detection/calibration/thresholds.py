"""Calibration threshold derivation and verdict band assignment logic for PandaMIND."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass


OPERATING_POINTS = {
    "fpr_0.1%": 0.001,
    "fpr_1%": 0.01,
    "fpr_5%": 0.05,
}


@dataclass(frozen=True)
class ThresholdConfig:
    temperature: float | None = None
    scale: float | None = None
    shift: float | None = None
    calibration_status: str = "not_calibrated"  # "calibrated" | "not_calibrated"
    calibration_reason: str | None = "insufficient_validation_data"
    operating_point_thresholds: dict[str, float] | None = None
    low_threshold: float | None = None   # Upper bound for consistent_with_human
    high_threshold: float | None = None  # Lower bound for likely_synthetic
    target_operating_point: str = "fpr_1%"

    def to_dict(self) -> dict:
        return asdict(self)


def derive_calibration_thresholds(
    val_scores: list[float],
    val_labels: list[int],
    target_operating_point: str = "fpr_1%",
    **calib_kwargs,
) -> ThresholdConfig:
    """Derive calibration thresholds at FPR operating points from validation data.

    Returns an explicit 'not_calibrated' state if validation data is insufficient.
    """
    if not val_scores or not val_labels or len(val_scores) != len(val_labels):
        return ThresholdConfig(
            calibration_status="not_calibrated",
            calibration_reason="insufficient_validation_data",
            target_operating_point=target_operating_point,
            **calib_kwargs
        )

    labels_set = set(val_labels)
    if labels_set != {0, 1}:
        return ThresholdConfig(
            calibration_status="not_calibrated",
            calibration_reason="insufficient_validation_data_missing_classes",
            target_operating_point=target_operating_point,
            **calib_kwargs
        )

    human_scores = sorted([s for s, y in zip(val_scores, val_labels) if y == 0])
    synth_scores = sorted([s for s, y in zip(val_scores, val_labels) if y == 1])

    # Minimum sample requirement per class to estimate thresholds
    if len(human_scores) < 2 or len(synth_scores) < 2:
        return ThresholdConfig(
            calibration_status="not_calibrated",
            calibration_reason="insufficient_validation_sample_count",
            target_operating_point=target_operating_point,
            **calib_kwargs
        )

    op_thresholds: dict[str, float] = {}
    n_human = len(human_scores)

    for op_name, fpr_target in OPERATING_POINTS.items():
        max_fp = int(math.floor(fpr_target * n_human))
        cutoff_idx = n_human - 1 - max_fp
        if cutoff_idx < 0:
            cutoff_idx = 0
        op_thresholds[op_name] = round(float(human_scores[cutoff_idx]), 6)

    high_thresh = op_thresholds.get(target_operating_point, op_thresholds["fpr_1%"])

    # Derive low threshold based on synthetic sample distribution (e.g. FNR 5% bound)
    n_synth = len(synth_scores)
    max_fn = int(math.floor(0.05 * n_synth))
    low_idx = min(max_fn, n_synth - 1)
    low_thresh = round(float(synth_scores[low_idx]), 6)

    # Ensure conclusive bands never collapse and inconclusive is NEVER disableable
    min_margin = 0.01
    if low_thresh >= high_thresh - min_margin:
        low_thresh = max(0.0, round(high_thresh - min_margin, 6))

    return ThresholdConfig(
        calibration_status="calibrated",
        calibration_reason=None,
        operating_point_thresholds=op_thresholds,
        low_threshold=low_thresh,
        high_threshold=high_thresh,
        target_operating_point=target_operating_point,
        **calib_kwargs
    )


def assign_verdict_band(probability: float, config: ThresholdConfig | None) -> str:
    """Assign verdict band based on calibrated probability and threshold config.

    Verdict bands:
      - 'consistent_with_human' (probability < low_threshold)
      - 'inconclusive' (low_threshold <= probability <= high_threshold)
      - 'likely_synthetic' (probability > high_threshold)
      - 'not_calibrated' (if config is None or calibration_status != 'calibrated')
    """
    if (
        config is None
        or config.calibration_status != "calibrated"
        or config.low_threshold is None
        or config.high_threshold is None
    ):
        return "not_calibrated"

    if probability < config.low_threshold:
        return "consistent_with_human"
    elif probability > config.high_threshold:
        return "likely_synthetic"
    else:
        return "inconclusive"
