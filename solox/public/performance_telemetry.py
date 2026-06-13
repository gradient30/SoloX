# -*- coding: utf-8 -*-
"""Bounded in-process telemetry for API and ADB performance diagnostics."""

import math
import time
from collections import deque
from threading import Lock


class _MetricSeries:

    def __init__(self, sample_limit):
        self.samples = deque(maxlen=sample_limit)
        self.active = 0
        self.max_active = 0
        self.count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0

    def begin(self):
        self.active += 1
        self.max_active = max(self.max_active, self.active)

    def end(self, duration_ms):
        self.active = max(0, self.active - 1)
        self.count += 1
        self.total_ms += duration_ms
        self.max_ms = max(self.max_ms, duration_ms)
        self.samples.append(duration_ms)

    def reset(self):
        self.samples.clear()
        self.active = 0
        self.max_active = 0
        self.count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0

    def snapshot(self):
        ordered = sorted(self.samples)
        p95_ms = 0.0
        if ordered:
            index = max(0, math.ceil(len(ordered) * 0.95) - 1)
            p95_ms = ordered[index]
        average = self.total_ms / self.count if self.count else 0.0
        return {
            'count': self.count,
            'active': self.active,
            'max_active': self.max_active,
            'avg_ms': round(average, 3),
            'max_ms': round(self.max_ms, 3),
            'p95_ms': round(p95_ms, 3),
            'sample_count': len(self.samples),
        }


class PerformanceTelemetry:

    def __init__(self, sample_limit=200, route_limit=128):
        self._sample_limit = sample_limit
        self._route_limit = max(1, route_limit)
        self._lock = Lock()
        self._generation = 0
        self._api = _MetricSeries(sample_limit)
        self._adb = _MetricSeries(sample_limit)
        self._api_routes = {}

    def _begin(self, series):
        with self._lock:
            series.begin()
            generation = self._generation
        return time.perf_counter(), generation

    def _end(self, series, token):
        started_at, generation = token
        duration_ms = (time.perf_counter() - started_at) * 1000
        with self._lock:
            if generation != self._generation:
                return None
            series.end(duration_ms)
        return duration_ms

    def begin_api(self, route):
        with self._lock:
            self._api.begin()
            if (
                route not in self._api_routes
                and len(self._api_routes) >= self._route_limit - 1
            ):
                route = '__other__'
            route_series = self._api_routes.setdefault(
                route,
                _MetricSeries(self._sample_limit),
            )
            route_series.begin()
            generation = self._generation
        return time.perf_counter(), generation, route

    def end_api(self, route, token):
        started_at, generation, recorded_route = token
        duration_ms = (time.perf_counter() - started_at) * 1000
        with self._lock:
            if generation != self._generation:
                return None
            self._api.end(duration_ms)
            route_series = self._api_routes.get(recorded_route)
            if route_series is not None:
                route_series.end(duration_ms)
        return duration_ms

    def begin_adb(self):
        return self._begin(self._adb)

    def end_adb(self, token):
        return self._end(self._adb, token)

    def reset(self):
        with self._lock:
            self._generation += 1
            self._api.reset()
            self._adb.reset()
            self._api_routes = {}

    def snapshot(self):
        with self._lock:
            api = self._api.snapshot()
            api['routes'] = {
                route: series.snapshot()
                for route, series in sorted(self._api_routes.items())
            }
            return {
                'api': api,
                'adb': self._adb.snapshot(),
                'sample_limit': self._sample_limit,
                'route_limit': self._route_limit,
            }


telemetry = PerformanceTelemetry()
