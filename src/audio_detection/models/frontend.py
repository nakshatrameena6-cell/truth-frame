"""Stable, peak-normalized raw-waveform acoustic features with optional local SSL adapter."""
from __future__ import annotations

import cmath
import math
import numpy as np


def _fft(x: list[complex]) -> list[complex]:
    try:
        return list(np.fft.fft(x))
    except Exception:
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

        if isinstance(samples, list):
            samples_arr = np.asarray(samples, dtype=np.float64)
        else:
            samples_arr = samples.astype(np.float64)

        # 1. Waveform Peak Normalization (invariance to recording volume/gain)
        peak = float(np.max(np.abs(samples_arr))) if len(samples_arr) > 0 else 0.0
        if peak > 1e-6:
            norm_samples = samples_arr / peak
        else:
            norm_samples = samples_arr.copy()

        # 2. Basic normalized time-domain metrics
        mean = float(np.mean(norm_samples))
        norm_rms = float(np.sqrt(np.mean(norm_samples ** 2)))
        zc = float(np.sum((norm_samples[:-1] * norm_samples[1:]) < 0) / max(1, len(norm_samples) - 1))
        duration_sec = len(samples_arr) / max(1, sample_rate)
        log1p_duration = math.log1p(duration_sec)

        # 3. Frame-level STFT & Spectral metrics
        frame_size = 256
        hop_size = 128
        n_samples = len(norm_samples)

        frames = []
        for start in range(0, max(1, n_samples - frame_size + 1), hop_size):
            chunk = norm_samples[start : start + frame_size]
            if len(chunk) < frame_size:
                chunk = np.pad(chunk, (0, frame_size - len(chunk)))
            frames.append(chunk)

        if not frames:
            frames_arr = np.zeros((1, frame_size), dtype=np.float64)
        else:
            frames_arr = np.asarray(frames, dtype=np.float64)

        window_arr = 0.5 * (1.0 - np.cos(2 * np.pi * np.arange(frame_size, dtype=np.float64) / frame_size))

        # Frame RMS
        frame_rmss = np.sqrt(np.mean(frames_arr ** 2, axis=1))

        # Windowed FFT (all frames in one vectorized C call)
        windowed_arr = frames_arr * window_arr
        fft_arr = np.fft.rfft(windowed_arr, axis=1)
        mags_arr = np.abs(fft_arr)

        nyquist = max(1.0, sample_rate / 2.0)
        freq_bin = (sample_rate / 2.0) / (frame_size // 2)

        total_mag = np.sum(mags_arr, axis=1, keepdims=True) + 1e-12
        k_bins = np.arange(mags_arr.shape[1], dtype=np.float64) * freq_bin

        # Centroid
        centroids = np.sum(mags_arr * k_bins, axis=1, keepdims=True) / total_mag
        # Bandwidth
        bandwidths = np.sqrt(np.sum(mags_arr * ((k_bins - centroids) ** 2), axis=1, keepdims=True) / total_mag)

        # Rolloff (85% energy threshold)
        target_energy = 0.85 * total_mag
        cum_energy = np.cumsum(mags_arr, axis=1)
        rolloff_indices = np.argmax(cum_energy >= target_energy, axis=1)
        rolloffs = rolloff_indices.astype(np.float64) * freq_bin

        # Flatness (geometric mean / arithmetic mean)
        arith_mean = total_mag / mags_arr.shape[1]
        log_mags = np.log(np.maximum(1e-12, mags_arr))
        geo_mean = np.exp(np.mean(log_mags, axis=1, keepdims=True))
        flatnesses = geo_mean / np.maximum(1e-12, arith_mean)

        avg_centroid = float(np.mean(centroids)) / nyquist
        avg_bandwidth = float(np.mean(bandwidths)) / nyquist
        avg_rolloff = float(np.mean(rolloffs)) / nyquist
        avg_flatness = float(np.mean(flatnesses))

        # 4. Energy variance & Spectral flux across frames
        mean_f_rms = float(np.mean(frame_rmss))
        frame_energy_var = float(np.mean((frame_rmss - mean_f_rms) ** 2))

        if len(mags_arr) > 1:
            fluxes = np.mean(np.abs(np.diff(mags_arr, axis=0)), axis=1)
            avg_spectral_flux = float(np.mean(fluxes))
        else:
            avg_spectral_flux = 0.0

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
