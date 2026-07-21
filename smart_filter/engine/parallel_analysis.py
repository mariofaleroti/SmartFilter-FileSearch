from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from smart_filter.domain.search_config import ANALYSIS_MODE_FOLDER
from smart_filter.domain.search_models import FileCandidate, SearchRequest
from smart_filter.engine.candidate_analysis import CandidateAnalysisOutcome, CandidateAnalyzer

PROCESS_ANALYSIS_ENVIRONMENT_KEY = "SMARTFILTER_CPU_ANALYSIS"
PROCESS_BATCH_MAX_ITEMS = 64
PROCESS_BATCH_MAX_CONTENT_CHARS = 4 * 1024 * 1024
PROCESS_PENDING_BATCHES_PER_WORKER = 2
PROCESS_READER_QUEUE_CAPACITY = 16


@dataclass(frozen=True)
class AnalysisBatchItem:
    sequence: int
    candidate: FileCandidate


@dataclass(frozen=True)
class AnalysisItemOutcome:
    sequence: int
    outcome: CandidateAnalysisOutcome | None = None
    error_detail: dict[str, object] | None = None
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class AnalysisBatchOutcome:
    items: tuple[AnalysisItemOutcome, ...] = ()
    worker_pid: int = 0
    elapsed_seconds: float = 0.0


_PROCESS_ANALYZER: CandidateAnalyzer | None = None


def initialize_analysis_process(request: SearchRequest) -> None:
    """Compile the request once inside each persistent worker process."""

    global _PROCESS_ANALYZER
    _PROCESS_ANALYZER = CandidateAnalyzer(request)


def _analyze_items(
    analyzer: CandidateAnalyzer,
    batch: Iterable[AnalysisBatchItem],
) -> AnalysisBatchOutcome:
    batch_started_at = perf_counter()
    outcomes: list[AnalysisItemOutcome] = []
    for item in batch:
        item_started_at = perf_counter()
        try:
            outcome = analyzer.analyze(item.candidate)
            outcomes.append(
                AnalysisItemOutcome(
                    sequence=item.sequence,
                    outcome=outcome,
                    elapsed_seconds=perf_counter() - item_started_at,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive process boundary.
            outcomes.append(
                AnalysisItemOutcome(
                    sequence=item.sequence,
                    error_detail={
                        "code": "match_analysis_process_error",
                        "error_type": "match_analysis_process_error",
                        "path": str(item.candidate.full_path),
                        "stage": "match_analysis_process",
                        "message": str(exc),
                        "exception_type": type(exc).__name__,
                        "source": "smart_filter",
                        "severity": "error",
                    },
                    elapsed_seconds=perf_counter() - item_started_at,
                )
            )
    return AnalysisBatchOutcome(
        items=tuple(outcomes),
        worker_pid=os.getpid(),
        elapsed_seconds=perf_counter() - batch_started_at,
    )


def analyze_candidate_batch(batch: tuple[AnalysisBatchItem, ...]) -> AnalysisBatchOutcome:
    """Analyze a compact batch in a spawned worker process."""

    if _PROCESS_ANALYZER is None:
        raise RuntimeError("El proceso de análisis no fue inicializado.")
    return _analyze_items(_PROCESS_ANALYZER, batch)


def analyze_candidate_batch_locally(
    request: SearchRequest,
    batch: tuple[AnalysisBatchItem, ...],
) -> AnalysisBatchOutcome:
    """Correctness fallback used when one process batch cannot be recovered."""

    return _analyze_items(CandidateAnalyzer(request), batch)


def recommended_analysis_processes(logical_cpu_count: int | None = None) -> int:
    """Leave CPU capacity for the OS, GUI, readers and foreground applications."""

    logical = max(1, int(logical_cpu_count or os.cpu_count() or 1))
    if logical <= 4:
        return 1
    if logical <= 12:
        return 2
    if logical <= 20:
        return 3
    return 4


def should_use_process_analysis(
    request: SearchRequest,
    *,
    broad_scan_root_detected: bool,
) -> bool:
    """Select true CPU parallelism only for broad scans unless explicitly forced."""

    override = str(os.environ.get(PROCESS_ANALYSIS_ENVIRONMENT_KEY, "auto") or "auto").strip().casefold()
    if override in {"0", "false", "off", "disabled", "no"}:
        return False
    if override in {"1", "true", "on", "enabled", "yes", "always"}:
        return request.form_state.mode == ANALYSIS_MODE_FOLDER
    return request.form_state.mode == ANALYSIS_MODE_FOLDER and broad_scan_root_detected
