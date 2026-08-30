"""Deterministic channel degradations. AMR-NB/Opus require a local ffmpeg binary."""
from __future__ import annotations
import audioop, shutil, subprocess

def g711_mulaw(pcm16: bytes, sample_rate: int) -> bytes:
    """G.711 μ-law companding; caller must first resample to 8 kHz."""
    if sample_rate != 8000: raise ValueError("G.711 telecom profile requires 8 kHz PCM")
    return audioop.lin2ulaw(pcm16, 2)

def ffmpeg_reencode(input_path: str, output_path: str, codec: str) -> None:
    if codec not in {"amr_nb", "opus"}: raise ValueError("codec must be amr_nb or opus")
    binary = shutil.which("ffmpeg")
    if not binary: raise RuntimeError("AMR-NB/Opus degradation needs locally installed ffmpeg; no network download is attempted")
    args = [binary, "-y", "-i", input_path, "-ar", "8000"] if codec == "amr_nb" else [binary, "-y", "-i", input_path]
    args += ["-c:a", "libopencore_amrnb" if codec == "amr_nb" else "libopus", output_path]
    subprocess.run(args, check=True, capture_output=True)
