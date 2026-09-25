"""Inference latency benchmarking for PRD Milestone M3 (PRD NFR-1).

Benchmarks real production model inference across:
1. Short clips (~2.5s speech at 16 kHz)
2. Telecom clips (~4.0s speech at 8 kHz narrowband)
3. 60-second audio clips (60.0s at 16 kHz)

Measures min, mean, p50, p90, p95, and p99 latency in seconds and evaluates against
PRD NFR-1: 60-second audio p95 < 8.0 seconds.
"""
from __future__ import annotations

import io
import json
import struct
import time
import wave
from pathlib import Path
from typing import Dict, List

import numpy as np

from audio_detection.api.service import scoring_engine


def generate_pcm_wav(samples: List[int], rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def create_audio_clip(duration_s: float, rate: int = 16000, freq: float = 440.0) -> bytes:
    n_samples = int(duration_s * rate)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    # Multi-component harmonic signal simulating speech
    sig = (
        0.4 * np.sin(2 * np.pi * freq * t)
        + 0.2 * np.sin(2 * np.pi * (freq * 2) * t)
        + 0.1 * np.cos(2 * np.pi * (freq * 3) * t)
    )
    int16_samples = (np.clip(sig, -1.0, 1.0) * 32767).astype(np.int16).tolist()
    return generate_pcm_wav(int16_samples, rate=rate)


def measure_latencies(
    audio_bytes: bytes,
    n_runs: int = 20,
    warmup: int = 3,
) -> Dict[str, float]:
    # Warmup
    for i in range(warmup):
        scoring_engine.score_audio(audio_bytes, f"warmup_{i}")

    times: List[float] = []
    for i in range(n_runs):
        t0 = time.perf_counter()
        res = scoring_engine.score_audio(audio_bytes, f"bench_{i}")
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    arr = np.array(times)
    return {
        "n_runs": n_runs,
        "min_s": round(float(np.min(arr)), 4),
        "mean_s": round(float(np.mean(arr)), 4),
        "max_s": round(float(np.max(arr)), 4),
        "p50_s": round(float(np.percentile(arr, 50)), 4),
        "p90_s": round(float(np.percentile(arr, 90)), 4),
        "p95_s": round(float(np.percentile(arr, 95)), 4),
        "p99_s": round(float(np.percentile(arr, 99)), 4),
    }


def main():
    print("=" * 60)
    print(" PandaMIND M3 — Real Model Inference Latency Benchmark")
    print("=" * 60)

    # 1. Representative Short Clip (2.5s, 16kHz)
    print("\n[1/3] Benchmarking Short Clip (2.5s @ 16kHz)...")
    short_wav = create_audio_clip(duration_s=2.5, rate=16000, freq=350.0)
    short_metrics = measure_latencies(short_wav, n_runs=25, warmup=5)
    print(f"  Short (2.5s): p50={short_metrics['p50_s']}s, p95={short_metrics['p95_s']}s, p99={short_metrics['p99_s']}s")

    # 2. Representative Telecom Clip (4.0s, 8kHz G.711)
    print("\n[2/3] Benchmarking Telecom Clip (4.0s @ 8kHz)...")
    telecom_wav = create_audio_clip(duration_s=4.0, rate=8000, freq=300.0)
    telecom_metrics = measure_latencies(telecom_wav, n_runs=25, warmup=5)
    print(f"  Telecom (4.0s): p50={telecom_metrics['p50_s']}s, p95={telecom_metrics['p95_s']}s, p99={telecom_metrics['p99_s']}s")

    # 3. 60-Second Clip (60.0s, 16kHz)
    print("\n[3/3] Benchmarking 60-Second Audio Clip (60.0s @ 16kHz)...")
    long_wav = create_audio_clip(duration_s=60.0, rate=16000, freq=440.0)
    long_metrics = measure_latencies(long_wav, n_runs=15, warmup=2)
    print(f"  60-Second: p50={long_metrics['p50_s']}s, p95={long_metrics['p95_s']}s, p99={long_metrics['p99_s']}s")

    # NFR-1 Verification: p95 < 8.0s
    nfr1_threshold = 8.0
    nfr1_pass = long_metrics["p95_s"] < nfr1_threshold
    print("\n" + "=" * 60)
    print(f" PRD NFR-1 REQUIREMENT CHECK:")
    print(f" Target: 60-second audio p95 < {nfr1_threshold:.1f}s")
    print(f" Measured: {long_metrics['p95_s']:.4f}s")
    print(f" Status: {'PASS' if nfr1_pass else 'FAIL'}")
    print("=" * 60)

    # Save to reports/benchmark/m3_eval_report.json
    out_dir = Path("reports/benchmark")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "m3_eval_report.json"

    report_data = {
        "milestone": "M3",
        "model_version": "m2-waveform-10d",
        "benchmark_environment": {
            "os": "Windows",
            "runtime": "CPython 3.14",
            "feature_extractor": "HybridFrontend 10D",
        },
        "latency_benchmarks": {
            "short_2_5s": short_metrics,
            "telecom_4_0s": telecom_metrics,
            "long_60_0s": long_metrics,
        },
        "nfr_compliance": {
            "NFR-1": {
                "name": "60-second audio latency",
                "requirement": "p95 < 8.0 seconds",
                "measured_p95_s": long_metrics["p95_s"],
                "measured_p50_s": long_metrics["p50_s"],
                "measured_p99_s": long_metrics["p99_s"],
                "status": "PASS" if nfr1_pass else "FAIL",
            }
        },
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved latency evaluation report to: {report_file}")


if __name__ == "__main__":
    main()
