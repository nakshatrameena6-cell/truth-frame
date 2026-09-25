"""Deterministic WAV decoding, normalisation and energy VAD."""
from __future__ import annotations
import math
import wave
from io import BytesIO
import numpy as np

def decode_wav(blob: bytes) -> tuple[list[float], int]:
    with wave.open(BytesIO(blob), "rb") as f:
        if f.getcomptype() != "NONE":
            raise ValueError("only PCM WAV is supported by the dependency-free decoder")
        width, channels, rate = f.getsampwidth(), f.getnchannels(), f.getframerate()
        raw = f.readframes(f.getnframes())
    if width not in (1, 2):
        raise ValueError("only 8-bit and 16-bit PCM WAV are supported")

    dtype = np.uint8 if width == 1 else np.int16
    vals = np.frombuffer(raw, dtype=dtype)
    scale, offset = (128.0, 128.0) if width == 1 else (32768.0, 0.0)

    if channels > 1:
        vals = vals.reshape(-1, channels)
        mono = (vals.astype(np.float64) - offset).mean(axis=1) / scale
    else:
        mono = (vals.astype(np.float64) - offset) / scale

    peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0
    if peak > 0.0:
        norm = np.clip(mono / peak, -1.0, 1.0)
    else:
        norm = mono

    return norm.tolist(), rate

def normalise(samples: list[float]) -> list[float]:
    if not samples:
        return []
    arr = np.asarray(samples, dtype=np.float64)
    peak = float(np.max(np.abs(arr)))
    if peak == 0.0:
        return arr.tolist()
    return np.clip(arr / peak, -1.0, 1.0).tolist()

def vad_segments(samples: list[float], sample_rate: int, frame_ms: int = 30, threshold: float = .015, min_ms: int = 120) -> list[tuple[int, int]]:
    frame = max(1, sample_rate * frame_ms // 1000)
    minimum = sample_rate * min_ms // 1000
    if not samples:
        return []

    arr = np.asarray(samples, dtype=np.float64)
    n = len(arr)
    n_frames = n // frame

    if n_frames > 0:
        framed = arr[: n_frames * frame].reshape(n_frames, frame)
        frame_rms = np.sqrt(np.mean(framed ** 2, axis=1))
        active = (frame_rms >= threshold).tolist()
    else:
        active = []

    if n > n_frames * frame:
        rem_rms = float(np.sqrt(np.mean(arr[n_frames * frame:] ** 2)))
        active.append(rem_rms >= threshold)

    runs = []
    start = None
    for i, is_active in enumerate(active + [False]):
        if is_active and start is None:
            start = i * frame
        if not is_active and start is not None:
            end = min(i * frame, n)
            if end - start >= minimum:
                runs.append((start, end))
            start = None
    return runs
