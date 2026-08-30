"""Named Phase 0 evaluation slices; records cannot lose required provenance."""
from __future__ import annotations
from collections import defaultdict
from .metrics import evaluate, MetricRecord

def evaluate_slices(rows: list[dict], model_version: str) -> list[MetricRecord]:
    required = {"label", "score", "dataset", "split", "language", "generator", "channel_condition", "degradation"}
    groups = defaultdict(list)
    for row in rows:
        missing = required - row.keys()
        if missing: raise ValueError(f"evaluation row missing: {sorted(missing)}")
        key = tuple(row[k] for k in ("dataset", "split", "language", "generator", "channel_condition", "degradation"))
        groups[key].append(row)
    return [evaluate([r["label"] for r in group], [r["score"] for r in group], dataset=key[0], split=key[1], language=key[2], generator=key[3], channel_condition=key[4], degradation=key[5], model_version=model_version) for key, group in groups.items()]
