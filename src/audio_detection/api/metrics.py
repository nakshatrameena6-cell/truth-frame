"""Operational Metrics Collector for PandaMIND VPC Deployment (PRD Milestone M5).

Tracks:
- Requests total, completed jobs, failed jobs
- Validation errors and inconclusive results
- Score/verdict distributions for drift monitoring
- Operating point selection distributions
- Latency percentiles (p50, p95, p99) without logging any audio content
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional
import numpy as np


class MetricsCollector:
    """Thread-safe collector for production observability metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._requests_total = 0
        self._jobs_completed_total = 0
        self._jobs_failed_total = 0
        self._validation_errors_total = 0
        self._inconclusive_results_total = 0

        self._verdicts_total: Dict[str, int] = {
            "likely_synthetic": 0,
            "consistent_with_human": 0,
            "inconclusive": 0,
        }
        self._operating_points_total: Dict[str, int] = {
            "fpr_0.1pct": 0,
            "fpr_1pct": 0,
            "fpr_5pct": 0,
        }
        self._latencies_s: List[float] = []
        self._max_latency_history = 1000

    def record_request(self) -> None:
        with self._lock:
            self._requests_total += 1

    def record_validation_error(self) -> None:
        with self._lock:
            self._validation_errors_total += 1

    def record_job_failure(self) -> None:
        with self._lock:
            self._jobs_failed_total += 1

    def record_job_completion(
        self,
        operating_point: str,
        verdict_band: str,
        latency_s: float,
    ) -> None:
        with self._lock:
            self._jobs_completed_total += 1

            if verdict_band in self._verdicts_total:
                self._verdicts_total[verdict_band] += 1
            else:
                self._verdicts_total[verdict_band] = 1

            if verdict_band == "inconclusive":
                self._inconclusive_results_total += 1

            if operating_point in self._operating_points_total:
                self._operating_points_total[operating_point] += 1
            else:
                self._operating_points_total[operating_point] = 1

            self._latencies_s.append(latency_s)
            if len(self._latencies_s) > self._max_latency_history:
                self._latencies_s.pop(0)

    def get_summary(self, model_version: str = "m2-waveform-10d") -> dict:
        """Computes summary statistics for the /v1/metrics endpoint."""
        with self._lock:
            uptime = round(time.time() - self._start_time, 2)
            reqs = self._requests_total
            completed = self._jobs_completed_total
            failed = self._jobs_failed_total
            val_errs = self._validation_errors_total
            inconcl = self._inconclusive_results_total
            verdicts = dict(self._verdicts_total)
            op_points = dict(self._operating_points_total)

            if self._latencies_s:
                arr = np.array(self._latencies_s)
                p50 = round(float(np.percentile(arr, 50)), 4)
                p95 = round(float(np.percentile(arr, 95)), 4)
                p99 = round(float(np.percentile(arr, 99)), 4)
                mean_l = round(float(np.mean(arr)), 4)
                last_l = round(float(self._latencies_s[-1]), 4)
            else:
                p50 = p95 = p99 = mean_l = last_l = 0.0

        return {
            "service": "pandamind-audio-scoring",
            "model_version": model_version,
            "uptime_seconds": uptime,
            "requests_total": reqs,
            "jobs_completed_total": completed,
            "jobs_failed_total": failed,
            "validation_errors_total": val_errs,
            "inconclusive_results_total": inconcl,
            "verdict_distribution": verdicts,
            "operating_point_distribution": op_points,
            "latency_seconds": {
                "last": last_l,
                "mean": mean_l,
                "p50": p50,
                "p95": p95,
                "p99": p99,
            },
            "drift_monitoring": {
                "status": "active_in_process",
                "synthetic_ratio": round(verdicts.get("likely_synthetic", 0) / max(1, completed), 4),
                "inconclusive_ratio": round(inconcl / max(1, completed), 4),
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._start_time = time.time()
            self._requests_total = 0
            self._jobs_completed_total = 0
            self._jobs_failed_total = 0
            self._validation_errors_total = 0
            self._inconclusive_results_total = 0
            self._verdicts_total = {
                "likely_synthetic": 0,
                "consistent_with_human": 0,
                "inconclusive": 0,
            }
            self._operating_points_total = {
                "fpr_0.1pct": 0,
                "fpr_1pct": 0,
                "fpr_5pct": 0,
            }
            self._latencies_s.clear()


# Global singleton metrics collector
metrics_collector = MetricsCollector()
