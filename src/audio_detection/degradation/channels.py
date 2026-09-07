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
        try:
            import imageio_ffmpeg
            binary = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            binary = None
    if not binary:
        raise RuntimeError("AMR-NB/Opus degradation needs locally installed ffmpeg; no network download is attempted")
    import tempfile
    import os
    ext = ".amr" if codec == "amr_nb" else ".opus"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if codec == "amr_nb":
            cmd_enc = [binary, "-y", "-i", input_path, "-ar", "8000", "-c:a", "libopencore_amrnb", "-f", "amr", tmp_path]
            cmd_dec = [binary, "-y", "-i", tmp_path, "-ar", "8000", "-c:a", "pcm_s16le", output_path]
        else:
            cmd_enc = [binary, "-y", "-i", input_path, "-c:a", "libopus", "-b:a", "16k", "-f", "opus", tmp_path]
            cmd_dec = [binary, "-y", "-i", tmp_path, "-ar", "16000", "-c:a", "pcm_s16le", output_path]
        subprocess.run(cmd_enc, check=True, capture_output=True)
        subprocess.run(cmd_dec, check=True, capture_output=True)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


