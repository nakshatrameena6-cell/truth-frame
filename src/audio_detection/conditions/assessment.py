"""Acoustic condition assessment module for PandaMIND (PRD FR-2).

Calculates:
- Effective bandwidth in Hz (from power spectral density 95% energy cutoff)
- Signal-to-noise ratio (SNR) in dB (active speech vs non-speech frames)
- Clipping ratio (fraction of samples reaching or exceeding clipping threshold)
- Estimated codec chain (narrowband G.711, AMR-NB, Opus, clean PCM, etc.)
- Total active speech duration in milliseconds
- Quality gate evaluation status ('passed' or 'failed')
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class ConditionAssessmentResult:
    effective_bandwidth_hz: int
    estimated_codec_chain: List[str]
    snr_db: float
    clipping_ratio: float
    speech_duration_ms: int
    quality_gate: str  # "passed" | "failed"

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_effective_bandwidth(samples: list[float], sample_rate: int) -> int:
    """Estimates effective bandwidth in Hz via 95% cumulative spectral power."""
    if not samples or sample_rate <= 0:
        return 0

    arr = np.asarray(samples, dtype=np.float64)
    # Detrend
    arr = arr - np.mean(arr)
    n = len(arr)
    if n < 32:
        return min(sample_rate // 2, 4000)

    # Compute FFT
    rfft = np.fft.rfft(arr)
    power = np.abs(rfft) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

    total_power = np.sum(power)
    if total_power <= 1e-12:
        return min(sample_rate // 2, 4000)

    cum_power = np.cumsum(power)
    target = 0.95 * total_power
    idx = int(np.searchsorted(cum_power, target))
    idx = min(idx, len(freqs) - 1)

    raw_bw = float(freqs[idx])

    # Bound by Nyquist
    max_nyquist = sample_rate // 2
    bw = int(min(max(raw_bw, 1000.0), float(max_nyquist)))

    # Clean quantization to typical telecom / audio boundaries
    if sample_rate == 8000:
        return min(bw, 4000)
    elif bw <= 3600:
        return 3400
    elif bw <= 4200:
        return 4000
    elif bw <= 7500:
        return 7000
    elif bw <= 8500:
        return 8000
    return bw


def calculate_snr_db(
    samples: list[float],
    spans: list[Tuple[int, int]],
    sample_rate: int = 16000,
) -> float:
    """Estimates SNR in dB by comparing active speech energy to non-active / background energy."""
    if not samples:
        return 0.0

    arr = np.asarray(samples, dtype=np.float64)
    n = len(arr)

    speech_mask = np.zeros(n, dtype=bool)
    for st, ed in spans:
        st = max(0, min(st, n))
        ed = max(0, min(ed, n))
        if ed > st:
            speech_mask[st:ed] = True

    if np.any(speech_mask):
        signal_power = float(np.mean(arr[speech_mask] ** 2))
    else:
        signal_power = float(np.mean(arr ** 2)) if n > 0 else 1e-6

    noise_mask = ~speech_mask
    if np.any(noise_mask):
        noise_power = float(np.mean(arr[noise_mask] ** 2))
    else:
        # Fallback: estimate noise from bottom 10th percentile frame energies
        frame_len = max(16, sample_rate * 30 // 1000)
        n_frames = n // frame_len
        if n_frames > 0:
            framed = arr[: n_frames * frame_len].reshape(n_frames, frame_len)
            frame_powers = np.mean(framed ** 2, axis=1)
            noise_power = float(np.percentile(frame_powers, 10))
        else:
            noise_power = 1e-5

    noise_power = max(noise_power, 1e-6)
    signal_power = max(signal_power, 1e-6)

    ratio = signal_power / noise_power
    snr = 10.0 * math.log10(max(1e-4, ratio))
    return round(float(np.clip(snr, -10.0, 60.0)), 1)


def calculate_clipping_ratio(samples: list[float], threshold: float = 0.999) -> float:
    """Computes the fraction of audio samples whose absolute value exceeds the clipping threshold."""
    if not samples:
        return 0.0
    arr = np.asarray(samples, dtype=np.float64)
    clipped_count = np.sum(np.abs(arr) >= threshold)
    return round(float(clipped_count / len(arr)), 4)


def estimate_codec_chain(
    sample_rate: int,
    effective_bw_hz: int,
    snr_db: float,
    clipping_ratio: float,
    filename: Optional[str] = None,
) -> List[str]:
    """Infers likely codec chain and acoustic channel degradations."""
    chain: List[str] = []
    fname_lower = (filename or "").lower()

    if fname_lower.endswith(".amr") or "amr" in fname_lower:
        chain.append("amr_nb")
    elif fname_lower.endswith((".opus", ".ogg")):
        chain.append("opus")
    elif fname_lower.endswith(".mp3"):
        chain.append("mp3")
    elif fname_lower.endswith(".flac"):
        chain.append("flac")

    if sample_rate == 8000 or effective_bw_hz <= 3800:
        if "amr_nb" not in chain:
            chain.append("g711_8khz")
    elif effective_bw_hz <= 7000:
        chain.append("telecom_wideband")

    if clipping_ratio > 0.05:
        chain.append("clipped_audio")

    if snr_db < 10.0:
        chain.append("noisy_channel")

    if not chain:
        chain.append("clean_pcm")

    return chain


def assess_conditions(
    samples: list[float],
    sample_rate: int,
    spans: list[Tuple[int, int]],
    filename: Optional[str] = None,
    min_speech_duration_ms: int = 2000,
    min_snr_db: float = 3.0,
    max_clipping_ratio: float = 0.25,
) -> ConditionAssessmentResult:
    """Performs full PRD L1 condition assessment and evaluates mandatory quality gate."""
    if not samples or sample_rate <= 0:
        return ConditionAssessmentResult(
            effective_bandwidth_hz=0,
            estimated_codec_chain=["unreadable"],
            snr_db=0.0,
            clipping_ratio=0.0,
            speech_duration_ms=0,
            quality_gate="failed",
        )

    # 1. Total speech duration from VAD spans
    speech_samples = sum(ed - st for st, ed in spans if ed > st)
    speech_duration_ms = round(speech_samples * 1000 / sample_rate)

    # 2. Bandwidth, SNR, Clipping
    bandwidth_hz = calculate_effective_bandwidth(samples, sample_rate)
    snr_db = calculate_snr_db(samples, spans, sample_rate)
    clipping_ratio = calculate_clipping_ratio(samples)

    # 3. Estimated codec chain
    codec_chain = estimate_codec_chain(
        sample_rate=sample_rate,
        effective_bw_hz=bandwidth_hz,
        snr_db=snr_db,
        clipping_ratio=clipping_ratio,
        filename=filename,
    )

    # 4. Mandatory Quality Gate (FR-4):
    # Under 2.0s of speech OR condition metrics below floor -> failed
    if (
        speech_duration_ms < min_speech_duration_ms
        or snr_db < min_snr_db
        or clipping_ratio > max_clipping_ratio
    ):
        quality_gate = "failed"
    else:
        quality_gate = "passed"

    return ConditionAssessmentResult(
        effective_bandwidth_hz=bandwidth_hz,
        estimated_codec_chain=codec_chain,
        snr_db=snr_db,
        clipping_ratio=clipping_ratio,
        speech_duration_ms=speech_duration_ms,
        quality_gate=quality_gate,
    )
