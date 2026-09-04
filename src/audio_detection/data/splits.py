from __future__ import annotations
from dataclasses import replace
import hashlib
from .manifest import CorpusManifest, Sample

def _bucket(key: str, seed: str) -> float:
    return int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()[:16], 16) / 2**64

def assign_splits(samples: list[Sample] | tuple[Sample, ...], held_out_generators: set[str], seed: str = "phase0", train: float = .8, validation: float = .1) -> CorpusManifest:
    """Assign one deterministic split to each connected source/speaker group.

    A source and a speaker are linked by every sample that names both.  The
    connected component is the grouping unit, so a multi-speaker source (and a
    speaker represented in multiple sources) can never cross a split.
    """
    if not 0 < train < 1 or not 0 < validation < 1 or train + validation >= 1: raise ValueError("invalid split proportions")
    by_source: dict[str, set[str]] = {}
    by_speaker: dict[str, set[str]] = {}
    for sample in samples:
        by_source.setdefault(sample.source_id, set()).add(sample.speaker_id)
        by_speaker.setdefault(sample.speaker_id, set()).add(sample.source_id)

    group_for_source: dict[str, str] = {}
    for source in by_source:
        if source in group_for_source:
            continue
        pending_sources, pending_speakers = [source], []
        sources, speakers = set(), set()
        while pending_sources or pending_speakers:
            while pending_sources:
                current = pending_sources.pop()
                if current in sources:
                    continue
                sources.add(current)
                pending_speakers.extend(by_source[current] - speakers)
            while pending_speakers:
                current = pending_speakers.pop()
                if current in speakers:
                    continue
                speakers.add(current)
                pending_sources.extend(by_speaker[current] - sources)
        group_key = "sources=" + "|".join(sorted(sources)) + ";speakers=" + "|".join(sorted(speakers))
        group_for_source.update({member: group_key for member in sources})

    held_out_groups = {
        group_for_source[sample.source_id]
        for sample in samples if sample.is_synthetic and sample.generator in held_out_generators
    }
    output = []
    for s in samples:
        group_key = group_for_source[s.source_id]
        if group_key in held_out_groups:
            split = "test"
        else:
            b = _bucket(group_key, seed)
            split = "train" if b < train else "validation" if b < train + validation else "test"
        output.append(replace(s, split=split))
    manifest = CorpusManifest(tuple(output)); assert_no_leakage(manifest, held_out_generators); return manifest

def assert_no_leakage(manifest: CorpusManifest, held_out_generators: set[str]) -> None:
    for field in ("source_id", "speaker_id"):
        memberships: dict[str, set[str]] = {}
        for s in manifest.samples: memberships.setdefault(getattr(s, field), set()).add(s.split)
        leaking = [v for v, groups in memberships.items() if len(groups) > 1]
        if leaking: raise ValueError(f"{field} leakage across splits: {leaking[:3]}")
    non_tested = {s.generator for s in manifest.samples if s.split in {"train", "validation"}}
    overlap = non_tested & held_out_generators
    if overlap: raise ValueError(f"held-out generators in training: {sorted(overlap)}")
    for field in ("source_id", "speaker_id"):
        held_out_pool = {getattr(s, field) for s in manifest.samples if s.is_synthetic and s.generator in held_out_generators}
        seen_pool = {getattr(s, field) for s in manifest.samples if s.is_synthetic and s.generator not in held_out_generators}
        shared = held_out_pool & seen_pool
        if shared: raise ValueError(f"held-out and seen generator {field} pools overlap: {sorted(shared)[:3]}")
