from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Mapping

try:  # Optional at import time; requirements install it for normal releases.
    import psutil  # type: ignore
except Exception:  # pragma: no cover - fallback for minimal environments.
    psutil = None

RESOURCE_PROFILE_LOW = "Bajo consumo"
RESOURCE_PROFILE_BALANCED = "Equilibrado"
RESOURCE_PROFILE_HIGH = "Alto rendimiento"
RESOURCE_PROFILE_OPTIONS = [
    RESOURCE_PROFILE_LOW,
    RESOURCE_PROFILE_BALANCED,
    RESOURCE_PROFILE_HIGH,
]

PROCESSING_MODE_AUTOMATIC = "Automático"
PROCESSING_MODE_MANUAL = "Manual técnico"
PROCESSING_MODE_OPTIONS = [PROCESSING_MODE_AUTOMATIC, PROCESSING_MODE_MANUAL]

DEFAULT_RESOURCE_PROFILE = RESOURCE_PROFILE_BALANCED
DEFAULT_PROCESSING_MODE = PROCESSING_MODE_AUTOMATIC
DEFAULT_MANUAL_ANALYSIS_PROCESSES = 2
DEFAULT_MANUAL_READER_WORKERS = 4
DEFAULT_MANUAL_RESERVED_CORES = 2
DEFAULT_MANUAL_MAX_PENDING_BATCHES = 4
DEFAULT_PERFORMANCE_MONITOR_ENABLED = True
DEFAULT_PERFORMANCE_TIMELINE_ENABLED = True
DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS = 1.0
DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS = 10.0


@dataclass(frozen=True)
class CpuTopology:
    physical_cores: int
    logical_cores: int
    detection_backend: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "detection_backend": self.detection_backend,
        }


@dataclass(frozen=True)
class ResourcePolicy:
    processing_mode: str
    resource_profile: str
    physical_cores: int
    logical_cores: int
    reserved_system_cores: int
    available_physical_cores: int
    analysis_processes: int
    reader_workers: int
    reader_queue_capacity: int
    max_pending_batches: int
    pending_batches_per_process: int
    manual_override: bool
    recommended_analysis_processes: int
    recommended_reader_workers: int
    monitor_enabled: bool
    timeline_enabled: bool
    sample_interval_seconds: float
    timeline_interval_seconds: float
    detection_backend: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "processing_mode": self.processing_mode,
            "resource_profile": self.resource_profile,
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "reserved_system_cores": self.reserved_system_cores,
            "available_physical_cores": self.available_physical_cores,
            "recommended_analysis_processes": self.recommended_analysis_processes,
            "recommended_reader_workers": self.recommended_reader_workers,
            "active_analysis_processes": self.analysis_processes,
            "active_reader_workers": self.reader_workers,
            "reader_queue_capacity": self.reader_queue_capacity,
            "max_pending_batches": self.max_pending_batches,
            "pending_batches_per_process": self.pending_batches_per_process,
            "manual_override": self.manual_override,
            "monitor_enabled": self.monitor_enabled,
            "timeline_enabled": self.timeline_enabled,
            "sample_interval_seconds": self.sample_interval_seconds,
            "timeline_interval_seconds": self.timeline_interval_seconds,
            "detection_backend": self.detection_backend,
        }


def detect_cpu_topology() -> CpuTopology:
    logical = max(1, int(os.cpu_count() or 1))
    physical = 0
    backend = "os_cpu_count_fallback"
    if psutil is not None:
        try:
            logical = max(1, int(psutil.cpu_count(logical=True) or logical))
            physical = int(psutil.cpu_count(logical=False) or 0)
            backend = "psutil"
        except Exception:
            physical = 0
    if physical <= 0:
        # Conservative fallback: SMT is common, but never invent more physical cores
        # than logical ones and never return zero.
        physical = max(1, logical // 2 if logical >= 4 else logical)
    physical = min(physical, logical)
    return CpuTopology(physical_cores=physical, logical_cores=logical, detection_backend=backend)


def _clean_profile(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in RESOURCE_PROFILE_OPTIONS else DEFAULT_RESOURCE_PROFILE


def _clean_mode(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in PROCESSING_MODE_OPTIONS else DEFAULT_PROCESSING_MODE


def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _safe_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _automatic_values(topology: CpuTopology, profile: str) -> tuple[int, int, int, int]:
    physical = topology.physical_cores
    logical = topology.logical_cores

    if profile == RESOURCE_PROFILE_LOW:
        reserved = max(1, min(physical - 1 if physical > 1 else 1, math.ceil(physical * 0.50)))
        processes = 1
        readers = min(2, logical)
        pending_per_process = 1
    elif profile == RESOURCE_PROFILE_HIGH:
        reserved = max(1, math.ceil(physical * 0.20))
        available = max(1, physical - reserved)
        processes = max(1, min(6, math.ceil(available * 0.75)))
        readers = max(2, min(6, logical, physical + 1))
        pending_per_process = 2
    else:
        reserved = max(2 if physical >= 4 else 1, math.ceil(physical / 3))
        available = max(1, physical - reserved)
        processes = max(1, min(4, math.ceil(available / 2)))
        readers = max(1, min(4, logical, physical))
        pending_per_process = 2

    available = max(1, physical - reserved)
    processes = min(processes, available, max(1, logical - 1))
    queue_capacity = {
        RESOURCE_PROFILE_LOW: max(4, readers * 2),
        RESOURCE_PROFILE_BALANCED: max(8, readers * 4),
        RESOURCE_PROFILE_HIGH: max(12, readers * 4),
    }[profile]
    return reserved, max(1, processes), max(1, readers), max(1, pending_per_process)


def resolve_resource_policy(
    settings: Mapping[str, Any] | None = None,
    *,
    topology: CpuTopology | None = None,
) -> ResourcePolicy:
    values = dict(settings or {})
    topology = topology or detect_cpu_topology()
    mode = _clean_mode(values.get("processing_mode"))
    profile = _clean_profile(values.get("resource_profile"))

    auto_reserved, auto_processes, auto_readers, auto_pending_per_process = _automatic_values(
        topology, profile
    )
    manual_override = mode == PROCESSING_MODE_MANUAL

    if manual_override:
        reserved = _safe_int(
            values.get("manual_reserved_cores"),
            DEFAULT_MANUAL_RESERVED_CORES,
            1,
            max(1, topology.physical_cores - 1),
        )
        available = max(1, topology.physical_cores - reserved)
        processes = _safe_int(
            values.get("manual_analysis_processes"),
            DEFAULT_MANUAL_ANALYSIS_PROCESSES,
            1,
            max(1, min(8, available, topology.logical_cores - 1 if topology.logical_cores > 1 else 1)),
        )
        readers = _safe_int(
            values.get("manual_reader_workers"),
            DEFAULT_MANUAL_READER_WORKERS,
            1,
            max(1, min(8, topology.logical_cores)),
        )
        max_pending = _safe_int(
            values.get("manual_max_pending_batches"),
            DEFAULT_MANUAL_MAX_PENDING_BATCHES,
            1,
            max(1, processes * 4),
        )
        pending_per_process = max(1, math.ceil(max_pending / processes))
        queue_capacity = max(readers, min(64, readers * 4))
    else:
        reserved = auto_reserved
        available = max(1, topology.physical_cores - reserved)
        processes = auto_processes
        readers = auto_readers
        pending_per_process = auto_pending_per_process
        max_pending = max(1, processes * pending_per_process)
        queue_capacity = {
            RESOURCE_PROFILE_LOW: max(4, readers * 2),
            RESOURCE_PROFILE_BALANCED: max(8, readers * 4),
            RESOURCE_PROFILE_HIGH: max(12, readers * 4),
        }[profile]

    return ResourcePolicy(
        processing_mode=mode,
        resource_profile=profile,
        physical_cores=topology.physical_cores,
        logical_cores=topology.logical_cores,
        reserved_system_cores=reserved,
        available_physical_cores=max(1, topology.physical_cores - reserved),
        analysis_processes=max(1, processes),
        reader_workers=max(1, readers),
        reader_queue_capacity=max(1, queue_capacity),
        max_pending_batches=max(1, max_pending),
        pending_batches_per_process=max(1, pending_per_process),
        manual_override=manual_override,
        recommended_analysis_processes=auto_processes,
        recommended_reader_workers=auto_readers,
        monitor_enabled=bool(values.get("performance_monitor_enabled", DEFAULT_PERFORMANCE_MONITOR_ENABLED)),
        timeline_enabled=bool(values.get("performance_timeline_enabled", DEFAULT_PERFORMANCE_TIMELINE_ENABLED)),
        sample_interval_seconds=_safe_float(
            values.get("performance_sample_interval_seconds"),
            DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS,
            0.5,
            5.0,
        ),
        timeline_interval_seconds=_safe_float(
            values.get("performance_timeline_interval_seconds"),
            DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS,
            5.0,
            60.0,
        ),
        detection_backend=topology.detection_backend,
    )


def get_resource_profile_options() -> list[str]:
    return list(RESOURCE_PROFILE_OPTIONS)


def get_processing_mode_options() -> list[str]:
    return list(PROCESSING_MODE_OPTIONS)
