from __future__ import annotations

import multiprocessing as mp
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.engine.performance_monitor import PerformanceMonitor


def _cpu_bound_worker(duration_seconds: float) -> None:
    deadline = time.perf_counter() + duration_seconds
    value = 1
    while time.perf_counter() < deadline:
        value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
    if value < 0:  # pragma: no cover - keeps the loop observable.
        raise RuntimeError(value)


def main() -> int:
    context = mp.get_context("spawn")
    monitor = PerformanceMonitor(
        enabled=True,
        sample_interval_seconds=0.5,
        timeline_enabled=True,
        timeline_interval_seconds=5.0,
    )
    monitor.start()

    worker = context.Process(target=_cpu_bound_worker, args=(5.0,))
    worker.start()
    worker_pid = int(worker.pid or 0)
    worker.join(timeout=15.0)
    if worker.is_alive():
        worker.terminate()
        worker.join(timeout=5.0)
        raise AssertionError("The CPU validation worker did not finish.")
    assert worker.exitcode == 0, worker.exitcode

    result = monitor.stop()
    cpu = dict(result.get("cpu") or {})
    records = {
        int(item.get("pid") or 0): dict(item)
        for item in result.get("analysis_processes") or []
    }
    record = records.get(worker_pid)

    assert result["backend"] == "psutil_process_tree"
    assert result["samples_count"] >= 5, result["samples_count"]
    assert record is not None, (worker_pid, sorted(records))
    assert int(record["samples_count"]) >= 3, record
    assert float(record["average_cpu_cores"]) > 0.25, record
    assert float(record["peak_cpu_cores"]) > 0.50, record
    assert float(cpu["children_average_cores"]) > 0.20, cpu
    assert float(cpu["children_peak_cores"]) > 0.50, cpu

    print("PERFORMANCE_MONITOR_CHILD_CPU_OK")
    print(
        {
            "pid": worker_pid,
            "samples": record["samples_count"],
            "average_cpu_cores": record["average_cpu_cores"],
            "peak_cpu_cores": record["peak_cpu_cores"],
            "children_average_cores": cpu["children_average_cores"],
            "children_peak_cores": cpu["children_peak_cores"],
        }
    )
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
