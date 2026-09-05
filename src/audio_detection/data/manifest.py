"""Strict corpus-manifest schema. JSONL is deliberately dependency-free."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
import wave

REQUIRED_FIELDS = {"sample_id", "source_id", "speaker_id", "language", "is_synthetic", "generator", "audio_path", "degradation", "sample_rate", "channels", "split"}
VALID_SPLITS = {"train", "validation", "test", "unassigned"}

@dataclass(frozen=True)
class Sample:
    sample_id: str; source_id: str; speaker_id: str; language: str
    is_synthetic: bool; generator: str; audio_path: str; degradation: str
    sample_rate: int; channels: int; split: str = "unassigned"

    @classmethod
    def from_dict(cls, item: dict) -> "Sample":
        if not isinstance(item, dict):
            raise ValueError("manifest sample must be an object")
        missing = REQUIRED_FIELDS - item.keys()
        if missing: raise ValueError(f"manifest sample missing fields: {sorted(missing)}")
        unknown = item.keys() - REQUIRED_FIELDS
        if unknown: raise ValueError(f"manifest sample has unrecognised fields: {sorted(unknown)}")
        value = cls(**item)
        text_fields = ("sample_id", "source_id", "speaker_id", "language", "generator", "audio_path", "degradation", "split")
        if any(not isinstance(getattr(value, field), str) for field in text_fields):
            raise ValueError("manifest text fields must be strings")
        if not value.sample_id or not value.source_id or not value.speaker_id or not value.language:
            raise ValueError("sample/source/speaker IDs and language must be non-empty")
        if not value.audio_path or not value.degradation:
            raise ValueError("audio_path and degradation must be non-empty")
        if not isinstance(value.is_synthetic, bool):
            raise ValueError("is_synthetic must be boolean")
        if value.split not in VALID_SPLITS: raise ValueError(f"invalid split: {value.split}")
        if (not isinstance(value.sample_rate, int) or isinstance(value.sample_rate, bool)
                or not isinstance(value.channels, int) or isinstance(value.channels, bool)
                or value.sample_rate <= 0 or value.channels <= 0):
            raise ValueError("sample_rate and channels must be positive integers")
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
    paths = [Path(s.audio_path).as_posix().casefold() for s in manifest.samples]
    if len(paths) != len(set(paths)): raise ValueError("duplicate or ambiguous audio_path")


@dataclass(frozen=True)
class ValidationIssue:
    sample_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class CorpusValidation:
    checked: int
    passed: int
    failed: int
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return self.failed == 0


def validate_corpus_audio(
    manifest: CorpusManifest,
    root: str | Path,
    *,
    min_sample_rate: int = 1,
    max_channels: int = 8,
    near_empty_rms: float = 1e-5,
) -> CorpusValidation:
    """Validate local PCM WAV assets referenced by a manifest.

    Paths are resolved under ``root``; paths escaping it are rejected.  WAV is
    intentionally the only supported format in this dependency-free project.
    """
    if min_sample_rate < 1 or max_channels < 1 or near_empty_rms < 0:
        raise ValueError("invalid audio validation limits")
    base = Path(root).resolve()
    issues: list[ValidationIssue] = []
    failed_ids: set[str] = set()

    def fail(sample: Sample, code: str, detail: str) -> None:
        failed_ids.add(sample.sample_id)
        issues.append(ValidationIssue(sample.sample_id, code, detail))

    resolved_paths: dict[Path, list[Sample]] = {}
    for sample in manifest.samples:
        candidate = (base / sample.audio_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            continue
        resolved_paths.setdefault(candidate, []).append(sample)
    for path, samples in resolved_paths.items():
        if len(samples) > 1:
            for sample in samples:
                fail(sample, "ambiguous_audio_path", str(path))

    for sample in manifest.samples:
        path = (base / sample.audio_path).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            fail(sample, "path_outside_root", sample.audio_path)
            continue
        if not path.is_file():
            fail(sample, "missing_file", sample.audio_path)
            continue
        if path.suffix.casefold() != ".wav":
            fail(sample, "unsupported_format", path.suffix or "no extension")
            continue
        try:
            with wave.open(str(path), "rb") as audio:
                rate, channels = audio.getframerate(), audio.getnchannels()
                frames, width = audio.getnframes(), audio.getsampwidth()
                if audio.getcomptype() != "NONE":
                    fail(sample, "unsupported_format", "compressed WAV")
                    continue
                if frames == 0:
                    fail(sample, "empty_audio", "zero frames")
                    continue
                if rate < min_sample_rate:
                    fail(sample, "invalid_sample_rate", str(rate))
                if channels < 1 or channels > max_channels:
                    fail(sample, "invalid_channels", str(channels))
                if sample.sample_rate != rate:
                    fail(sample, "sample_rate_mismatch", f"manifest={sample.sample_rate}, file={rate}")
                if sample.channels != channels:
                    fail(sample, "channels_mismatch", f"manifest={sample.channels}, file={channels}")
                raw = audio.readframes(frames)
                if _pcm_rms(raw, width) <= near_empty_rms:
                    fail(sample, "near_empty_audio", f"rms<={near_empty_rms:g}")
        except (EOFError, wave.Error, OSError) as exc:
            fail(sample, "unreadable_audio", str(exc))
    return CorpusValidation(len(manifest.samples), len(manifest.samples) - len(failed_ids), len(failed_ids), tuple(issues))


def _pcm_rms(raw: bytes, width: int) -> float:
    """Return normalized RMS for unsigned 8-bit or signed 16/24/32-bit PCM."""
    if width not in {1, 2, 3, 4}:
        raise wave.Error(f"unsupported PCM sample width: {width}")
    if not raw:
        return 0.0
    if width == 1:
        values = (byte - 128 for byte in raw)
        scale = 128
    else:
        values = (
            int.from_bytes(raw[index:index + width] + (b"\xff" if raw[index + width - 1] & 0x80 else b"\x00"), "little", signed=True)
            for index in range(0, len(raw), width)
        )
        scale = 2 ** (8 * width - 1)
    total = sum(value * value for value in values)
    return math.sqrt(total / (len(raw) / width)) / scale
