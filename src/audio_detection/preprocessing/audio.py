"""Deterministic WAV decoding, normalisation and energy VAD."""
from __future__ import annotations
import array, math, wave
from io import BytesIO

def decode_wav(blob: bytes) -> tuple[list[float], int]:
    with wave.open(BytesIO(blob), "rb") as f:
        if f.getcomptype() != "NONE": raise ValueError("only PCM WAV is supported by the dependency-free decoder")
        width, channels, rate = f.getsampwidth(), f.getnchannels(), f.getframerate()
        raw = f.readframes(f.getnframes())
    if width not in (1, 2): raise ValueError("only 8-bit and 16-bit PCM WAV are supported")
    values = array.array("B" if width == 1 else "h"); values.frombytes(raw)
    scale, offset = (128., 128.) if width == 1 else (32768., 0.)
    mono = [sum((values[i + c] - offset) / scale for c in range(channels)) / channels for i in range(0, len(values), channels)]
    return normalise(mono), rate

def normalise(samples: list[float]) -> list[float]:
    peak = max((abs(x) for x in samples), default=0.)
    return samples[:] if peak == 0 else [max(-1., min(1., x / peak)) for x in samples]

def vad_segments(samples: list[float], sample_rate: int, frame_ms: int = 30, threshold: float = .015, min_ms: int = 120) -> list[tuple[int, int]]:
    frame = max(1, sample_rate * frame_ms // 1000); minimum = sample_rate * min_ms // 1000
    active = [math.sqrt(sum(x*x for x in samples[i:i+frame]) / max(1, len(samples[i:i+frame]))) >= threshold for i in range(0, len(samples), frame)]
    runs=[]; start=None
    for i, is_active in enumerate(active + [False]):
        if is_active and start is None: start=i*frame
        if not is_active and start is not None:
            end=min(i*frame, len(samples));
            if end-start >= minimum: runs.append((start,end))
            start=None
    return runs
