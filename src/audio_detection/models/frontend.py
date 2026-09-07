"""Stable, peak-normalized raw-waveform acoustic features with optional local SSL adapter."""
from __future__ import annotations

import cmath
import math
import numpy as np


def _fft(x: list[complex]) -> list[complex]:
    n = len(x)
    if n <= 1:
        return x
    even = _fft(x[0::2])
    odd = _fft(x[1::2])
    twiddles = [cmath.exp(-2j * math.pi * k / n) * odd[k] for k in range(n // 2)]
    return [even[k] + twiddles[k] for k in range(n // 2)] + [even[k] - twiddles[k] for k in range(n // 2)]


class WavLMXLSRFrontend:
    """Adapter for a locally provisioned WavLM/XLS-R-compatible embedder.

    The callable is injected by the application so this package never fetches
    weights or makes network calls. It must return a deterministic embedding.
    """

    def __init__(self, embedder=None):
        self.embedder = embedder

    def embed(self, samples: list[float], sample_rate: int) -> list[float]:
        return list(self.embedder(samples, sample_rate)) if self.embedder else []


class HybridFrontend:
    """Offline classical acoustic frontend with peak-amplitude normalization.

    Extracts 10 deterministic scalar features:
      0: mean (peak-normalized)
      1: norm_rms (peak-normalized RMS energy)
      2: zero_crossing_rate (normalized)
      3: log1p_duration (log duration in seconds)
      4: spectral_centroid (normalized by Nyquist)
      5: spectral_bandwidth (normalized by Nyquist)
      6: spectral_rolloff (85% energy threshold, normalized)
      7: spectral_flatness (ratio of geo mean to arith mean)
      8: frame_energy_variance (prosodic energy dynamics across sub-frames)
      9: spectral_flux (mean frame-to-frame spectral magnitude distance)
    """

    def __init__(self, ssl_embedder=None):
        self.ssl = WavLMXLSRFrontend(ssl_embedder)

    def embed(self, samples: list[float] | np.ndarray, sample_rate: int) -> list[float]:
        if samples is None or len(samples) == 0:
            return [0.0] * 10

        if isinstance(samples, np.ndarray):
            samples = samples.tolist()

        # 1. Waveform Peak Normalization (invariance to recording volume/gain)
        peak = max(abs(x) for x in samples)
        if peak > 1e-6:
            norm_samples = [x / peak for x in samples]
        else:
            norm_samples = list(samples)

        # 2. Basic normalized time-domain metrics
        mean = sum(norm_samples) / len(norm_samples)
        norm_rms = math.sqrt(sum(x * x for x in norm_samples) / len(norm_samples))
        zc = sum(a * b < 0 for a, b in zip(norm_samples, norm_samples[1:])) / max(1, len(norm_samples) - 1)
        duration_sec = len(samples) / max(1, sample_rate)
        log1p_duration = math.log1p(duration_sec)

        # 3. Frame-level STFT & Spectral metrics
        frame_size = 256
        hop_size = 128
        n_samples = len(norm_samples)

        frames_mags: list[list[float]] = []
        frame_rmss: list[float] = []

        # Hann window
        window = [0.5 * (1 - math.cos(2 * math.pi * n / frame_size)) for n in range(frame_size)]

        for start in range(0, max(1, n_samples - frame_size + 1), hop_size):
            chunk = norm_samples[start : start + frame_size]
            if len(chunk) < frame_size:
                chunk = chunk + [0.0] * (frame_size - len(chunk))

            # Frame RMS
            f_rms = math.sqrt(sum(v * v for v in chunk) / frame_size)
            frame_rmss.append(f_rms)

            # Windowed FFT
            windowed = [complex(v * w, 0.0) for v, w in zip(chunk, window)]
            fft_res = _fft(windowed)

            # Half-spectrum magnitude
            half_len = frame_size // 2 + 1
            mags = [abs(fft_res[k]) for k in range(half_len)]
            frames_mags.append(mags)

        if not frames_mags:
            frames_mags = [[1e-6] * (frame_size // 2 + 1)]
            frame_rmss = [norm_rms]

        # Aggregate spectral statistics across sub-frames
        centroids: list[float] = []
        bandwidths: list[float] = []
        rolloffs: list[float] = []
        flatnesses: list[float] = []

        nyquist = max(1.0, sample_rate / 2.0)
        freq_bin = (sample_rate / 2.0) / (frame_size // 2)

        for mags in frames_mags:
            total_mag = sum(mags) + 1e-12

            # Centroid
            centroid = sum(k * freq_bin * mag for k, mag in enumerate(mags)) / total_mag
            centroids.append(centroid)

            # Bandwidth
            bw = math.sqrt(sum(((k * freq_bin - centroid) ** 2) * mag for k, mag in enumerate(mags)) / total_mag)
            bandwidths.append(bw)

            # Rolloff (85% energy threshold)
            target_energy = 0.85 * total_mag
            cum_energy = 0.0
            r_freq = 0.0
            for k, mag in enumerate(mags):
                cum_energy += mag
                if cum_energy >= target_energy:
                    r_freq = k * freq_bin
                    break
            rolloffs.append(r_freq)

            # Flatness (geometric mean / arithmetic mean)
            arith_mean = total_mag / len(mags)
            log_sum = sum(math.log(max(1e-12, m)) for m in mags)
            geo_mean = math.exp(log_sum / len(mags))
            flatness = geo_mean / max(1e-12, arith_mean)
            flatnesses.append(flatness)

        avg_centroid = (sum(centroids) / len(centroids)) / nyquist
        avg_bandwidth = (sum(bandwidths) / len(bandwidths)) / nyquist
        avg_rolloff = (sum(rolloffs) / len(rolloffs)) / nyquist
        avg_flatness = sum(flatnesses) / len(flatnesses)

        # 4. Energy variance & Spectral flux across frames
        mean_f_rms = sum(frame_rmss) / len(frame_rmss)
        frame_energy_var = sum((r - mean_f_rms) ** 2 for r in frame_rmss) / len(frame_rmss)

        fluxes: list[float] = []
        for f1, f2 in zip(frames_mags, frames_mags[1:]):
            flux = sum(abs(a - b) for a, b in zip(f1, f2)) / len(f1)
            fluxes.append(flux)
        avg_spectral_flux = (sum(fluxes) / len(fluxes)) if fluxes else 0.0

        raw = [
            round(mean, 6),
            round(norm_rms, 6),
            round(zc, 6),
            round(log1p_duration, 6),
            round(avg_centroid, 6),
            round(avg_bandwidth, 6),
            round(avg_rolloff, 6),
            round(avg_flatness, 6),
            round(frame_energy_var, 6),
            round(avg_spectral_flux, 6),
        ]

        ssl = self.ssl.embed(samples, sample_rate)
        return raw + ssl
