"""Deterministic channel degradations. AMR-NB/Opus require a local ffmpeg binary."""
from __future__ import annotations

import shutil
import subprocess

import numpy as np

try:
    import audioop
except ImportError:
    class audioop:
        @staticmethod
        def lin2ulaw(pcm16_bytes: bytes, width: int = 2) -> bytes:
            samples = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            abs_samples = np.abs(samples)
            companded = np.sign(samples) * np.log1p(255.0 * abs_samples) / np.log(256.0)
            quantized = np.clip(np.rint((companded + 1.0) * 127.5), 0, 255).astype(np.uint8)
            return quantized.tobytes()

        @staticmethod
        def ulaw2lin(ulaw_bytes: bytes, width: int = 2) -> bytes:
            quantized = np.frombuffer(ulaw_bytes, dtype=np.uint8).astype(np.float32)
            companded = (quantized / 127.5) - 1.0
            abs_companded = np.abs(companded)
            samples = np.sign(companded) * (1.0 / 255.0) * (np.power(256.0, abs_companded) - 1.0)
            pcm16 = np.clip(np.rint(samples * 32767.0), -32768, 32767).astype(np.int16)
            return pcm16.tobytes()


def g711_mulaw(pcm16: bytes, sample_rate: int) -> bytes:
    """G.711 μ-law companding; caller must first resample to 8 kHz."""
    if sample_rate != 8000:
        raise ValueError("G.711 telecom profile requires 8 kHz PCM")
    return audioop.lin2ulaw(pcm16, 2)


def ulaw2lin(ulaw_bytes: bytes) -> bytes:
    """Convert G.711 μ-law bytes back to 16-bit linear PCM."""
    return audioop.ulaw2lin(ulaw_bytes, 2)


def ffmpeg_reencode(input_path: str, output_path: str, codec: str) -> None:
    if codec not in {"amr_nb", "opus"}:
        raise ValueError("codec must be amr_nb or opus")
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("AMR-NB/Opus degradation needs locally installed ffmpeg; no network download is attempted")
    args = [binary, "-y", "-i", input_path, "-ar", "8000"] if codec == "amr_nb" else [binary, "-y", "-i", input_path]
    args += ["-c:a", "libopencore_amrnb" if codec == "amr_nb" else "libopus", output_path]
    subprocess.run(args, check=True, capture_output=True)
