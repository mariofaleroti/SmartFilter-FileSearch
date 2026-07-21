from __future__ import annotations

import os
import tempfile
from pathlib import Path
from threading import Event, Timer

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine.cancellation import SearchCancelledError
from smart_filter.engine.parallel_analysis import recommended_analysis_processes
from smart_filter.engine.search_engine import run_search


def _result_signature(summary):
    return [
        (
            result.file_name,
            result.location_label,
            tuple(result.matched_terms),
            result.occurrence_count,
            tuple(
                (
                    location.get("location_label"),
                    tuple(location.get("matched_terms") or []),
                    location.get("preview_text"),
                )
                for location in result.match_locations
            ),
        )
        for result in summary.results
    ]


def _build_state(root: Path) -> SearchFormState:
    return SearchFormState(
        mode="Carpeta",
        path=str(root),
        search_text="atencion al cliente",
        category="Ninguna",
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        source="cpu_parallel_validator",
    )


def main() -> int:
    previous_mode = os.environ.get("SMARTFILTER_CPU_ANALYSIS")
    try:
        with tempfile.TemporaryDirectory(prefix="smartfilter_cpu_validation_") as temp:
            root = Path(temp)
            for index in range(180):
                marker = (
                    "administracion oficina atencion al cliente"
                    if index % 3 == 0
                    else "contenido neutro"
                )
                lines = [
                    f"Línea {line}: {marker if line in {7, 31, 77} else 'texto operativo'}"
                    for line in range(1, 120)
                ]
                (root / f"documento_{index:04d}.txt").write_text(
                    "\n".join(lines),
                    encoding="utf-8",
                )

            state = _build_state(root)
            os.environ["SMARTFILTER_CPU_ANALYSIS"] = "off"
            baseline = run_search(state)

            os.environ["SMARTFILTER_CPU_ANALYSIS"] = "always"
            parallel = run_search(state)

            assert _result_signature(baseline) == _result_signature(parallel)
            assert baseline.analyzed_candidates_count == parallel.analyzed_candidates_count == 180
            assert baseline.match_occurrences_count == parallel.match_occurrences_count == 180
            assert parallel.scan_stats["analysis_backend"] == "spawn_process_pool"
            assert parallel.scan_stats["analysis_processes_count"] == recommended_analysis_processes()
            assert parallel.scan_stats["analysis_batches_submitted_count"] > 0
            assert parallel.scan_stats["analysis_batches_failed_count"] == 0
            assert parallel.scan_stats["analysis_fallback_batches_count"] == 0
            assert parallel.scan_stats["analysis_worker_pids"]
            performance = parallel.scan_stats["performance"]
            assert performance["pipeline"]["pending_limit_respected"] is True
            assert (
                performance["pipeline"]["peak_pending_batches"]
                <= performance["pipeline"]["max_pending_batches"]
            )
            assert parallel.scan_stats["retained_candidate_content_chars_count"] == 0

            cancel_event = Event()
            Timer(0.05, cancel_event.set).start()
            try:
                run_search(state, cancel_requested=cancel_event.is_set)
            except SearchCancelledError:
                pass
            else:
                raise AssertionError("La búsqueda debía cancelarse.")

            print("CPU_PARALLEL_ANALYSIS_OK")
            print(
                {
                    "processes": parallel.scan_stats["analysis_processes_count"],
                    "worker_pids": parallel.scan_stats["analysis_worker_pids"],
                    "batches": parallel.scan_stats["analysis_batches_submitted_count"],
                    "results": parallel.match_occurrences_count,
                }
            )
            return 0
    finally:
        if previous_mode is None:
            os.environ.pop("SMARTFILTER_CPU_ANALYSIS", None)
        else:
            os.environ["SMARTFILTER_CPU_ANALYSIS"] = previous_mode


if __name__ == "__main__":
    raise SystemExit(main())
