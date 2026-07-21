from __future__ import annotations

import math
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional fallback.
    psutil = None


def _round(value: float, digits: int = 3) -> float:
    return round(float(value or 0.0), digits)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


@dataclass
class _PidMetrics:
    cpu_cores: list[float] = field(default_factory=list)
    memory_mb: list[float] = field(default_factory=list)

    def to_dict(self, pid: int) -> dict[str, Any]:
        return {
            "pid": pid,
            "samples_count": len(self.cpu_cores),
            "average_cpu_cores": _round(_average(self.cpu_cores)),
            "peak_cpu_cores": _round(max(self.cpu_cores, default=0.0)),
            "average_memory_mb": _round(_average(self.memory_mb)),
            "peak_memory_mb": _round(max(self.memory_mb, default=0.0)),
        }


@dataclass
class _PhaseMetrics:
    system_cpu_percent: list[float] = field(default_factory=list)
    smartfilter_cpu_cores: list[float] = field(default_factory=list)
    total_memory_mb: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples_count": len(self.system_cpu_percent),
            "system_average_percent": _round(_average(self.system_cpu_percent)),
            "system_peak_percent": _round(max(self.system_cpu_percent, default=0.0)),
            "smartfilter_average_cores": _round(_average(self.smartfilter_cpu_cores)),
            "smartfilter_peak_cores": _round(max(self.smartfilter_cpu_cores, default=0.0)),
            "memory_average_mb": _round(_average(self.total_memory_mb)),
            "memory_peak_mb": _round(max(self.total_memory_mb, default=0.0)),
        }


class PerformanceMonitor:
    """Sample system and Smart Filter process-tree CPU/RAM with low overhead."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        sample_interval_seconds: float = 1.0,
        timeline_enabled: bool = True,
        timeline_interval_seconds: float = 10.0,
        logical_cores: int | None = None,
        physical_cores: int | None = None,
    ) -> None:
        self.enabled = bool(enabled and psutil is not None)
        self.requested = bool(enabled)
        self.sample_interval_seconds = max(0.5, float(sample_interval_seconds))
        self.timeline_enabled = bool(timeline_enabled)
        self.timeline_interval_seconds = max(5.0, float(timeline_interval_seconds))
        self.logical_cores = max(1, int(logical_cores or os.cpu_count() or 1))
        self.physical_cores = max(1, int(physical_cores or self.logical_cores))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._phase = "scan_and_read"
        self._started_at = 0.0
        self._stopped_at = 0.0
        self._last_timeline_at = 0.0
        self._main_process = None
        self._known_processes: dict[int, Any] = {}
        self._cpu_pending_pids: set[int] = set()
        self._system_cpu_percent: list[float] = []
        self._smartfilter_cpu_cores: list[float] = []
        self._main_cpu_cores: list[float] = []
        self._children_cpu_cores: list[float] = []
        self._main_memory_mb: list[float] = []
        self._children_memory_mb: list[float] = []
        self._total_memory_mb: list[float] = []
        self._available_memory_mb: list[float] = []
        self._phases: dict[str, _PhaseMetrics] = defaultdict(_PhaseMetrics)
        self._per_pid: dict[int, _PidMetrics] = defaultdict(_PidMetrics)
        self._timeline: list[dict[str, Any]] = []

    @property
    def backend(self) -> str:
        if self.enabled:
            return "psutil_process_tree"
        if self.requested:
            return "unavailable"
        return "disabled"

    def start(self) -> None:
        self._started_at = monotonic()
        self._last_timeline_at = self._started_at
        if not self.enabled:
            return
        try:
            self._main_process = psutil.Process(os.getpid())
            psutil.cpu_percent(interval=None)
            main_process = self._prime_process(self._main_process)
            if main_process is not None:
                # The monitor thread waits one full sample interval before
                # reading the main process, so its baseline is already safe.
                self._cpu_pending_pids.discard(int(main_process.pid))
        except Exception:
            self.enabled = False
            return
        self._thread = threading.Thread(
            target=self._run,
            name="smartfilter-performance-monitor",
            daemon=True,
        )
        self._thread.start()

    def set_phase(self, phase: str) -> None:
        clean = str(phase or "").strip()
        if not clean:
            return
        with self._lock:
            self._phase = clean

    def stop(self) -> dict[str, Any]:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.sample_interval_seconds * 2.5))
        self._stopped_at = monotonic()
        return self.to_dict()

    def _prime_process(self, process: Any) -> Any | None:
        """Prime and cache one psutil.Process instance per PID.

        psutil keeps the baseline used by ``cpu_percent(interval=None)`` on the
        Process instance itself. Recreating that instance on every sample makes
        every child-process reading behave like a first call and commonly
        returns 0.0 forever.
        """
        try:
            process.cpu_percent(interval=None)
            pid = int(process.pid)
            self._known_processes[pid] = process
            # A process discovered inside a capture cycle must not be read
            # again immediately. The near-zero interval can produce an
            # artificial CPU spike. Its first capture records memory only;
            # CPU begins on the next scheduled sample.
            self._cpu_pending_pids.add(pid)
            return process
        except Exception:
            return None

    def _process_tree(self) -> tuple[Any | None, list[Any]]:
        main = self._main_process
        if main is None:
            return None, []
        try:
            discovered_children = main.children(recursive=True)
        except Exception:
            discovered_children = []

        live_pids: set[int] = set()
        cached_children: list[Any] = []
        for discovered in discovered_children:
            pid = int(getattr(discovered, "pid", 0) or 0)
            if not pid:
                continue
            live_pids.add(pid)
            process = self._known_processes.get(pid)
            try:
                same_process = process is not None and process == discovered
            except Exception:
                same_process = False
            if not same_process:
                process = self._prime_process(discovered)
            if process is not None:
                cached_children.append(process)

        # Process-pool workers can be replaced during a run. Keep historical
        # metrics in ``_per_pid`` but discard dead Process handles so a reused
        # PID is primed again instead of inheriting an obsolete CPU baseline.
        main_pid = int(getattr(main, "pid", 0) or 0)
        for pid in list(self._known_processes):
            if pid != main_pid and pid not in live_pids:
                self._known_processes.pop(pid, None)
                self._cpu_pending_pids.discard(pid)

        return main, cached_children

    def _sample_process(self, process: Any) -> tuple[float, float]:
        try:
            pid = int(process.pid)
            memory_mb = max(0.0, float(process.memory_info().rss) / (1024 * 1024))
            if pid in self._cpu_pending_pids:
                self._cpu_pending_pids.discard(pid)
                return 0.0, memory_mb
            cpu_cores = max(0.0, float(process.cpu_percent(interval=None)) / 100.0)
            return cpu_cores, memory_mb
        except Exception:
            return 0.0, 0.0

    def _run(self) -> None:
        while not self._stop_event.wait(self.sample_interval_seconds):
            self._capture_sample()
        # A final sample helps short drains and clean shutdowns.
        self._capture_sample()

    def _capture_sample(self) -> None:
        if not self.enabled:
            return
        now = monotonic()
        try:
            system_cpu = max(0.0, float(psutil.cpu_percent(interval=None)))
            available_mb = max(0.0, float(psutil.virtual_memory().available) / (1024 * 1024))
        except Exception:
            system_cpu = 0.0
            available_mb = 0.0

        main, children = self._process_tree()
        main_cpu, main_memory = self._sample_process(main) if main is not None else (0.0, 0.0)
        child_cpu = 0.0
        child_memory = 0.0
        child_samples: list[tuple[int, float, float]] = []
        for child in children:
            pid = int(getattr(child, "pid", 0) or 0)
            cpu_cores, memory_mb = self._sample_process(child)
            child_cpu += cpu_cores
            child_memory += memory_mb
            if pid:
                child_samples.append((pid, cpu_cores, memory_mb))

        total_cpu = main_cpu + child_cpu
        total_memory = main_memory + child_memory
        with self._lock:
            phase = self._phase
            self._system_cpu_percent.append(system_cpu)
            self._smartfilter_cpu_cores.append(total_cpu)
            self._main_cpu_cores.append(main_cpu)
            self._children_cpu_cores.append(child_cpu)
            self._main_memory_mb.append(main_memory)
            self._children_memory_mb.append(child_memory)
            self._total_memory_mb.append(total_memory)
            self._available_memory_mb.append(available_mb)
            phase_metrics = self._phases[phase]
            phase_metrics.system_cpu_percent.append(system_cpu)
            phase_metrics.smartfilter_cpu_cores.append(total_cpu)
            phase_metrics.total_memory_mb.append(total_memory)
            for pid, cpu_cores, memory_mb in child_samples:
                metrics = self._per_pid[pid]
                metrics.cpu_cores.append(cpu_cores)
                metrics.memory_mb.append(memory_mb)

            if self.timeline_enabled and (now - self._last_timeline_at) >= self.timeline_interval_seconds:
                self._timeline.append(
                    {
                        "elapsed_seconds": _round(now - self._started_at),
                        "phase": phase,
                        "system_cpu_percent": _round(system_cpu),
                        "smartfilter_cpu_cores": _round(total_cpu),
                        "smartfilter_normalized_percent": _round(total_cpu * 100.0 / self.logical_cores),
                        "memory_mb": _round(total_memory),
                        "available_memory_mb": _round(available_mb),
                        "child_processes_count": len(children),
                    }
                )
                self._last_timeline_at = now

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            system = list(self._system_cpu_percent)
            total_cpu = list(self._smartfilter_cpu_cores)
            main_cpu = list(self._main_cpu_cores)
            children_cpu = list(self._children_cpu_cores)
            main_memory = list(self._main_memory_mb)
            children_memory = list(self._children_memory_mb)
            total_memory = list(self._total_memory_mb)
            available_memory = list(self._available_memory_mb)
            phases = {name: metrics.to_dict() for name, metrics in self._phases.items()}
            per_pid = [metrics.to_dict(pid) for pid, metrics in sorted(self._per_pid.items())]
            timeline = [dict(item) for item in self._timeline]

        duration = max(0.0, (self._stopped_at or monotonic()) - self._started_at) if self._started_at else 0.0
        average_cores = _average(total_cpu)
        peak_cores = max(total_cpu, default=0.0)
        return {
            "enabled": self.enabled,
            "requested": self.requested,
            "backend": self.backend,
            "sample_interval_seconds": _round(self.sample_interval_seconds),
            "samples_count": len(system),
            "duration_seconds": _round(duration, 6),
            "cpu": {
                "physical_cores": self.physical_cores,
                "logical_cores": self.logical_cores,
                "system_average_percent": _round(_average(system)),
                "system_peak_percent": _round(max(system, default=0.0)),
                "system_p95_percent": _round(_percentile(system, 0.95)),
                "smartfilter_average_cores": _round(average_cores),
                "smartfilter_peak_cores": _round(peak_cores),
                "smartfilter_p95_cores": _round(_percentile(total_cpu, 0.95)),
                "smartfilter_normalized_average_percent": _round(average_cores * 100.0 / self.logical_cores),
                "smartfilter_normalized_peak_percent": _round(peak_cores * 100.0 / self.logical_cores),
                "main_average_cores": _round(_average(main_cpu)),
                "main_peak_cores": _round(max(main_cpu, default=0.0)),
                "children_average_cores": _round(_average(children_cpu)),
                "children_peak_cores": _round(max(children_cpu, default=0.0)),
            },
            "memory": {
                "main_average_mb": _round(_average(main_memory)),
                "main_peak_mb": _round(max(main_memory, default=0.0)),
                "children_average_mb": _round(_average(children_memory)),
                "children_peak_mb": _round(max(children_memory, default=0.0)),
                "total_average_mb": _round(_average(total_memory)),
                "total_peak_mb": _round(max(total_memory, default=0.0)),
                "system_available_minimum_mb": _round(min(available_memory, default=0.0)),
            },
            "analysis_processes": per_pid,
            "phases": phases,
            "timeline_interval_seconds": _round(self.timeline_interval_seconds),
            "timeline": timeline,
        }
