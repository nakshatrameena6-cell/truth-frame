"""Metrics always carry the evaluation-slice identity; no anonymous EER."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class MetricRecord:
    dataset: str; split: str; language: str; generator: str; channel_condition: str; degradation: str; model_version: str
    eer: float; tpr_at_1pct_fpr: float; ece: float; count: int

def evaluate(labels: list[int], scores: list[float], *, dataset: str, split: str, language: str, generator: str, channel_condition: str, degradation: str, model_version: str, bins: int = 10) -> MetricRecord:
    if len(labels) != len(scores) or not labels or not set(labels) >= {0, 1}:
        raise ValueError("labels/scores require both classes")
    if bins <= 0:
        raise ValueError("bins must be positive")
    if any(not 0 <= score <= 1 for score in scores):
        raise ValueError("scores must be probabilities in [0, 1]")
    # Include the two all-negative/all-positive operating points.  This makes
    # threshold metrics correct even when all observed scores are identical.
    points = [(0.0, 0.0)]
    for threshold in sorted(set(scores), reverse=True):
        tp = sum(y and s >= threshold for y, s in zip(labels, scores)); fp = sum(not y and s >= threshold for y, s in zip(labels, scores))
        pos = sum(labels); neg = len(labels) - pos; points.append((fp / neg, tp / pos))
    points.append((1.0, 1.0))
    # EER is the ROC point closest to FPR == FNR.  This deterministic discrete
    # estimate avoids inventing interpolated operating points.
    fpr, tpr = min(points, key=lambda point: abs(point[0] - (1 - point[1])))
    # Top-label ECE: confidence is assigned to the predicted class, whether
    # synthetic (score >= .5) or human (score < .5), and is compared with
    # prediction correctness rather than the positive-class label alone.
    confidence_and_correctness = [
        (max(score, 1 - score), int((score >= .5) == bool(label)))
        for label, score in zip(labels, scores)
    ]
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        group = [(confidence, correct) for confidence, correct in confidence_and_correctness if lo <= confidence < (hi if b < bins - 1 else 1.0000001)]
        if group: ece += len(group) / len(labels) * abs(sum(confidence for confidence, _ in group) / len(group) - sum(correct for _, correct in group) / len(group))
    return MetricRecord(dataset, split, language, generator, channel_condition, degradation, model_version, (fpr + 1 - tpr) / 2, max((t for f, t in points if f <= .01), default=0.0), ece, len(labels))

def to_dict(record: MetricRecord) -> dict: return asdict(record)
