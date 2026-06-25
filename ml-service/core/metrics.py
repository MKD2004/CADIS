"""
core/metrics.py
===============
Lightweight in-process metrics collector for model inference latencies.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class Metrics:
    _instance: Metrics | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._start_time = time.time()
        self._total_requests = 0
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._data_lock = threading.Lock()

    @classmethod
    def get(cls) -> Metrics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record(self, model: str, duration_ms: float) -> None:
        with self._data_lock:
            self._latencies[model].append(duration_ms)

    def inc_requests(self) -> None:
        with self._data_lock:
            self._total_requests += 1

    def snapshot(self) -> dict:
        with self._data_lock:
            avg = {}
            for model, times in self._latencies.items():
                avg[model] = round(sum(times) / len(times), 1) if times else 0
            return {
                "avg_latency_ms": avg,
                "total_requests_served": self._total_requests,
                "uptime_seconds": round(time.time() - self._start_time),
            }


def timed_inference(model_name: str):
    """Context manager that records inference duration for a model."""
    class _Timer:
        def __init__(self):
            self.duration_ms = 0.0
        def __enter__(self):
            self._t0 = time.perf_counter()
            return self
        def __exit__(self, *exc):
            self.duration_ms = round((time.perf_counter() - self._t0) * 1000, 1)
            from core.logging import get_logger
            get_logger("metrics").info("%s inference: %.0fms", model_name, self.duration_ms)
            Metrics.get().record(model_name, self.duration_ms)
    return _Timer()
