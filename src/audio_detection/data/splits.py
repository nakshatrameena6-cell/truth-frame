from __future__ import annotations
from dataclasses import replace
import hashlib
from .manifest import CorpusManifest, Sample

def _bucket(key: str, seed: str) -> float:
    return int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()[:16], 16) / 2**64

def assign_splits(samples: list[Sample] | tuple[Sample, ...], held_out_generators: set[str], seed: str = "phase0", train: float = .8, validation: float = .1) -> CorpusManifest:
    """Group by source (then speaker) so related audio can never cross a split."""
    if not 0 < train < 1 or not 0 < validation < 1 or train + validation >= 1: raise ValueError("invalid split proportions")
    output = []
    for s in samples:
        if s.generator in held_out_generators:
            split = "test"
        else:
            b = _bucket(f"{s.source_id}|{s.speaker_id}", seed)
            split = "train" if b < train else "validation" if b < train + validation else "test"
        output.append(replace(s, split=split))
    manifest = CorpusManifest(tuple(output)); assert_no_leakage(manifest, held_out_generators); return manifest

def assert_no_leakage(manifest: CorpusManifest, held_out_generators: set[str]) -> None:
    for field in ("source_id", "speaker_id"):
        memberships: dict[str, set[str]] = {}
        for s in manifest.samples: memberships.setdefault(getattr(s, field), set()).add(s.split)
        leaking = [v for v, groups in memberships.items() if len(groups) > 1]
        if leaking: raise ValueError(f"{field} leakage across splits: {leaking[:3]}")
    trained = {s.generator for s in manifest.samples if s.split == "train"}
    overlap = trained & held_out_generators
    if overlap: raise ValueError(f"held-out generators in training: {sorted(overlap)}")
    for field in ("source_id", "speaker_id"):
        held_out_pool = {getattr(s, field) for s in manifest.samples if s.is_synthetic and s.generator in held_out_generators}
        seen_pool = {getattr(s, field) for s in manifest.samples if s.is_synthetic and s.generator not in held_out_generators}
        shared = held_out_pool & seen_pool
        if shared: raise ValueError(f"held-out and seen generator {field} pools overlap: {sorted(shared)[:3]}")
