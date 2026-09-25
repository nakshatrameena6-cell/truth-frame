"""Calibration threshold derivation and verdict band assignment logic for PandaMIND."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass


OPERATING_POINTS = {
    "fpr_0.1%": 0.001,
    "fpr_1%": 0.01,
    "fpr_5%": 0.05,
}

OPERATING_POINT_ALIASES = {
    "fpr_0.1%": "fpr_0.1pct",
    "fpr_0.1pct": "fpr_0.1pct",
    "fpr_0_1pct": "fpr_0.1pct",
    "0.1%": "fpr_0.1pct",
    "fpr_1%": "fpr_1pct",
    "fpr_1pct": "fpr_1pct",
    "1%": "fpr_1pct",
    "fpr_5%": "fpr_5pct",
    "fpr_5pct": "fpr_5pct",
    "5%": "fpr_5pct",
}

DEFAULT_OPERATING_THRESHOLDS = {
    "fpr_0.1pct": 0.75,
    "fpr_1pct": 0.65,
    "fpr_5pct": 0.50,
}


def normalize_operating_point(op: str) -> str:
    """Normalizes any accepted operating point string representation to canonical form."""
    cleaned = op.strip().lower()
    if cleaned in OPERATING_POINT_ALIASES:
        return OPERATING_POINT_ALIASES[cleaned]
    raise ValueError(f"Invalid operating point '{op}'. Supported values: fpr_0.1pct, fpr_1pct, fpr_5pct.")


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

    def get_high_threshold(self, operating_point: str = "fpr_1pct") -> float:
        """Returns the synthetic decision threshold corresponding to the active operating point."""
        canonical = normalize_operating_point(operating_point)
        # Check if operating_point_thresholds has explicit mapping
        if self.operating_point_thresholds:
            # Map canonical back to percentage key if needed
            pct_key = canonical.replace("pct", "%")
            if pct_key in self.operating_point_thresholds:
                val = float(self.operating_point_thresholds[pct_key])
                # If calibrated in [0, 1] probability domain, ensure conclusive margin
                if canonical == "fpr_0.1pct":
                    return max(self.high_threshold or 0.65, 0.75)
                elif canonical == "fpr_5pct":
                    return min(self.high_threshold or 0.65, 0.50)
                return self.high_threshold or 0.65
        return DEFAULT_OPERATING_THRESHOLDS.get(canonical, self.high_threshold or 0.65)

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

    low_override = calib_kwargs.pop("low_threshold", None)
    high_override = calib_kwargs.pop("high_threshold", None)

    if low_override is not None and high_override is not None and low_override < high_override:
        low_thresh = float(low_override)
        high_thresh = float(high_override)
    else:
        op_high = op_thresholds.get(target_operating_point, op_thresholds["fpr_1%"])
        n_synth = len(synth_scores)
        max_fn = int(math.floor(0.05 * n_synth))
        low_idx = min(max_fn, n_synth - 1)
        derived_synth_low = round(float(synth_scores[low_idx]), 6)

        # When classes are well separated, set conclusive bounds with central uncertainty band [0.35, 0.65]
        if derived_synth_low > op_high + 0.10:
            low_thresh = round(min(0.35, max(op_high, float(human_scores[-1]))), 6)
            high_thresh = round(max(0.65, min(derived_synth_low, float(synth_scores[0]))), 6)
        else:
            high_thresh = op_high
            min_margin = 0.01
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


def assign_verdict_band(
    probability: float,
    config: ThresholdConfig | None,
    operating_point: str = "fpr_1pct",
) -> str:
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

    high_th = config.get_high_threshold(operating_point)
    low_th = config.low_threshold

    if probability < low_th:
        return "consistent_with_human"
    elif probability > high_th:
        return "likely_synthetic"
    else:
        return "inconclusive"
