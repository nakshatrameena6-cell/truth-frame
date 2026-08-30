"""Strict corpus-manifest schema. JSONL is deliberately dependency-free."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json

REQUIRED_FIELDS = {"sample_id", "source_id", "speaker_id", "language", "is_synthetic", "generator", "audio_path", "degradation", "sample_rate", "channels", "split"}
VALID_SPLITS = {"train", "validation", "test", "unassigned"}

@dataclass(frozen=True)
class Sample:
    sample_id: str; source_id: str; speaker_id: str; language: str
    is_synthetic: bool; generator: str; audio_path: str; degradation: str
    sample_rate: int; channels: int; split: str = "unassigned"

    @classmethod
    def from_dict(cls, item: dict) -> "Sample":
        missing = REQUIRED_FIELDS - item.keys()
        if missing: raise ValueError(f"manifest sample missing fields: {sorted(missing)}")
        unknown = item.keys() - REQUIRED_FIELDS
        if unknown: raise ValueError(f"manifest sample has unrecognised fields: {sorted(unknown)}")
        value = cls(**item)
        if not value.sample_id or not value.source_id or not value.speaker_id: raise ValueError("sample/source/speaker IDs must be non-empty")
        if value.split not in VALID_SPLITS: raise ValueError(f"invalid split: {value.split}")
        if value.sample_rate <= 0 or value.channels <= 0: raise ValueError("sample_rate and channels must be positive")
        if value.is_synthetic and not value.generator: raise ValueError("synthetic samples require a generator")
        if not value.is_synthetic and value.generator not in {"", "human", "none"}: raise ValueError("human samples must use generator human, none, or empty")
        return value

@dataclass(frozen=True)
class CorpusManifest:
    samples: tuple[Sample, ...]
    @classmethod
    def load_jsonl(cls, path: str | Path) -> "CorpusManifest":
        entries = [Sample.from_dict(json.loads(line)) for line in Path(path).read_text(encoding="utf8").splitlines() if line.strip()]
        manifest = cls(tuple(entries)); validate_manifest(manifest); return manifest
    def write_jsonl(self, path: str | Path) -> None:
        Path(path).write_text("".join(json.dumps(asdict(s), sort_keys=True) + "\n" for s in self.samples), encoding="utf8")

def validate_manifest(manifest: CorpusManifest) -> None:
    ids = [s.sample_id for s in manifest.samples]
    if len(ids) != len(set(ids)): raise ValueError("duplicate sample_id")
