from __future__ import annotations

import os
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import get_context
from dataclasses import dataclass, field, replace
from pathlib import Path
from time import monotonic, perf_counter
from typing import Any, Callable, Iterable, Iterator, Mapping

from file_scan_core import (
    DEFAULT_MAX_WORKERS,
    DEFAULT_QUEUE_CAPACITY,
    DirectoryExclusionMatch,
    DirectoryWalkStats,
    ScanError,
    WorkerPoolStats,
    build_scan_error,
    build_validation_error,
    iter_bounded_workers,
    iter_safe_directories,
)

from smart_filter.domain.search_config import ANALYSIS_MODE_FILE, ANALYSIS_MODE_FOLDER
from smart_filter.domain.scan_exclusions import (
    BROAD_SCAN_OPTIONS,
    build_scan_exclusion_context,
)
from smart_filter.domain.search_models import FileCandidate, SearchRequest, SearchResult
from smart_filter.engine.candidate_analysis import CandidateAnalysisOutcome, CandidateAnalyzer
from smart_filter.engine.cancellation import SearchCancelledError
from smart_filter.engine.parallel_analysis import (
    PROCESS_BATCH_MAX_CONTENT_CHARS,
    PROCESS_BATCH_MAX_ITEMS,
    AnalysisBatchItem,
    AnalysisBatchOutcome,
    analyze_candidate_batch,
    analyze_candidate_batch_locally,
    initialize_analysis_process,
    should_use_process_analysis,
)
from smart_filter.engine.performance_monitor import PerformanceMonitor
from smart_filter.engine.resource_policy import resolve_resource_policy
from smart_filter.engine.file_filter_engine import (
    build_path_candidate,
    candidate_is_technically_allowed,
    is_temporary_file,
    keyword_matches_path,
)
from smart_filter.readers.base import ReaderResult
from smart_filter.readers.reader_registry import read_file_content
from smart_filter.services.settings_service import get_max_content_file_size_bytes, get_settings

SMARTFILTER_OUTPUT_MARKER_NAME = ".smartfilter_output"
DEFAULT_SMARTFILTER_SKIPPED_DIRECTORY_NAMES = (
    SMARTFILTER_OUTPUT_MARKER_NAME,
    "__smartfilter__",
)
NORMAL_PROGRESS_EMIT_INTERVAL_SECONDS = 0.12
ROOT_PROGRESS_EMIT_INTERVAL_SECONDS = 0.25

ProgressCallback = Callable[[int | None, str], None]
CancelRequestedCallback = Callable[[], bool]




def _is_cancel_requested(callback: CancelRequestedCallback | None) -> bool:
    if callback is None:
        return False
    try:
        return bool(callback())
    except Exception:
        return False


def _raise_if_cancelled(callback: CancelRequestedCallback | None) -> None:
    if _is_cancel_requested(callback):
        raise SearchCancelledError()

def _progress_emit_interval_seconds(*, broad_scan_root_detected: bool) -> float:
    """Limit GUI progress traffic only for full-root scans."""

    if broad_scan_root_detected:
        return ROOT_PROGRESS_EMIT_INTERVAL_SECONDS
    return NORMAL_PROGRESS_EMIT_INTERVAL_SECONDS


@dataclass(frozen=True)
class ScanPipelineStats:
    """Counters produced by Smart Filter's scan and reader pipeline."""

    mode: str
    root_path: str
    directories_scanned_count: int = 0
    directories_skipped_count: int = 0
    files_seen_count: int = 0
    candidates_count: int = 0
    skipped_temporary_count: int = 0
    skipped_extension_count: int = 0
    skipped_file_keyword_count: int = 0
    skipped_exact_path_count: int = 0
    readers_executed_count: int = 0
    reader_errors_count: int = 0
    content_skipped_size_count: int = 0
    content_text_chars_count: int = 0
    reader_workers_count: int = 0
    reader_queue_capacity: int = 0
    reader_peak_in_flight_count: int = 0
    reader_peak_queued_count: int = 0
    reader_pipeline_elapsed_seconds: float = 0.0
    reader_succeeded_count: int = 0
    reader_failed_count: int = 0
    reader_controlled_error_count: int = 0
    reader_worker_failed_count: int = 0
    reader_skipped_count: int = 0
    reader_task_succeeded_count: int = 0
    reader_task_failed_count: int = 0
    reader_peak_active_count: int = 0
    files_seen_per_second: float = 0.0
    candidates_read_per_second: float = 0.0
    match_analysis_mode: str = "separate_pass"
    analysis_backend: str = "separate_pass"
    analysis_processes_count: int = 0
    analysis_batch_max_items: int = 0
    analysis_batch_max_content_chars: int = 0
    analysis_batches_submitted_count: int = 0
    analysis_batches_completed_count: int = 0
    analysis_batches_failed_count: int = 0
    analysis_fallback_batches_count: int = 0
    analysis_peak_pending_batches_count: int = 0
    analysis_worker_pids: tuple[int, ...] = ()
    analysis_pipeline_elapsed_seconds: float = 0.0
    analysis_candidates_per_second: float = 0.0
    analysis_payload_content_chars_count: int = 0
    analysis_cancelled: bool = False
    match_analyzed_candidates_count: int = 0
    match_results_count: int = 0
    match_occurrences_count: int = 0
    match_no_match_count: int = 0
    match_skipped_by_discard_count: int = 0
    match_unsupported_extension_count: int = 0
    match_worker_elapsed_seconds_total: float = 0.0
    content_released_after_analysis_count: int = 0
    retained_candidate_content_chars_count: int = 0
    scan_errors_count: int = 0
    issues_count: int = 0
    warnings_count: int = 0
    critical_errors_count: int = 0
    duplicate_issue_occurrences_count: int = 0
    policy_skipped_directories_count: int = 0
    link_or_reparse_skipped_directories_count: int = 0
    name_skipped_directories_count: int = 0
    keyword_skipped_directories_count: int = 0
    revisited_skipped_directories_count: int = 0
    unclassified_skipped_directories_count: int = 0
    broad_scan_root_detected: bool = False
    broad_scan_safe_enabled: bool = False
    automatic_exclusion_groups: tuple[str, ...] = ()
    automatic_excluded_directories_count: int = 0
    automatic_excluded_directories_by_group: dict[str, int] = field(default_factory=dict)
    manual_excluded_directories_count: int = 0
    exclusion_samples: tuple[dict[str, str], ...] = ()
    performance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "root_path": self.root_path,
            "directories_scanned_count": self.directories_scanned_count,
            "directories_skipped_count": self.directories_skipped_count,
            "files_seen_count": self.files_seen_count,
            "candidates_count": self.candidates_count,
            "skipped_temporary_count": self.skipped_temporary_count,
            "skipped_extension_count": self.skipped_extension_count,
            "skipped_file_keyword_count": self.skipped_file_keyword_count,
            "skipped_exact_path_count": self.skipped_exact_path_count,
            "readers_executed_count": self.readers_executed_count,
            "reader_errors_count": self.reader_errors_count,
            "content_skipped_size_count": self.content_skipped_size_count,
            "content_text_chars_count": self.content_text_chars_count,
            "reader_workers_count": self.reader_workers_count,
            "reader_queue_capacity": self.reader_queue_capacity,
            "reader_peak_in_flight_count": self.reader_peak_in_flight_count,
            "reader_peak_queued_count": self.reader_peak_queued_count,
            "reader_pipeline_elapsed_seconds": round(self.reader_pipeline_elapsed_seconds, 6),
            "reader_succeeded_count": self.reader_succeeded_count,
            "reader_failed_count": self.reader_failed_count,
            "reader_controlled_error_count": self.reader_controlled_error_count,
            "reader_worker_failed_count": self.reader_worker_failed_count,
            "reader_skipped_count": self.reader_skipped_count,
            "reader_task_succeeded_count": self.reader_task_succeeded_count,
            "reader_task_failed_count": self.reader_task_failed_count,
            "reader_peak_active_count": self.reader_peak_active_count,
            "files_seen_per_second": round(self.files_seen_per_second, 3),
            "candidates_read_per_second": round(self.candidates_read_per_second, 3),
            "match_analysis_mode": self.match_analysis_mode,
            "analysis_backend": self.analysis_backend,
            "analysis_processes_count": self.analysis_processes_count,
            "analysis_batch_max_items": self.analysis_batch_max_items,
            "analysis_batch_max_content_chars": self.analysis_batch_max_content_chars,
            "analysis_batches_submitted_count": self.analysis_batches_submitted_count,
            "analysis_batches_completed_count": self.analysis_batches_completed_count,
            "analysis_batches_failed_count": self.analysis_batches_failed_count,
            "analysis_fallback_batches_count": self.analysis_fallback_batches_count,
            "analysis_peak_pending_batches_count": self.analysis_peak_pending_batches_count,
            "analysis_worker_pids": list(self.analysis_worker_pids),
            "analysis_pipeline_elapsed_seconds": round(self.analysis_pipeline_elapsed_seconds, 6),
            "analysis_candidates_per_second": round(self.analysis_candidates_per_second, 3),
            "analysis_payload_content_chars_count": self.analysis_payload_content_chars_count,
            "analysis_cancelled": self.analysis_cancelled,
            "match_analyzed_candidates_count": self.match_analyzed_candidates_count,
            "match_results_count": self.match_results_count,
            "match_occurrences_count": self.match_occurrences_count,
            "match_no_match_count": self.match_no_match_count,
            "match_skipped_by_discard_count": self.match_skipped_by_discard_count,
            "match_unsupported_extension_count": self.match_unsupported_extension_count,
            "match_worker_elapsed_seconds_total": round(self.match_worker_elapsed_seconds_total, 6),
            "content_released_after_analysis_count": self.content_released_after_analysis_count,
            "retained_candidate_content_chars_count": self.retained_candidate_content_chars_count,
            "scan_errors_count": self.scan_errors_count,
            "issues_count": self.issues_count,
            "warnings_count": self.warnings_count,
            "critical_errors_count": self.critical_errors_count,
            "duplicate_issue_occurrences_count": self.duplicate_issue_occurrences_count,
            "policy_skipped_directories_count": self.policy_skipped_directories_count,
            "link_or_reparse_skipped_directories_count": self.link_or_reparse_skipped_directories_count,
            "name_skipped_directories_count": self.name_skipped_directories_count,
            "keyword_skipped_directories_count": self.keyword_skipped_directories_count,
            "revisited_skipped_directories_count": self.revisited_skipped_directories_count,
            "unclassified_skipped_directories_count": self.unclassified_skipped_directories_count,
            "skipped_directories_breakdown": {
                "policy": self.policy_skipped_directories_count,
                "link_or_reparse": self.link_or_reparse_skipped_directories_count,
                "exact_name": self.name_skipped_directories_count,
                "keyword": self.keyword_skipped_directories_count,
                "revisited": self.revisited_skipped_directories_count,
                "unclassified": self.unclassified_skipped_directories_count,
            },
            "broad_scan_root_detected": self.broad_scan_root_detected,
            "broad_scan_safe_enabled": self.broad_scan_safe_enabled,
            "automatic_exclusion_groups": list(self.automatic_exclusion_groups),
            "automatic_excluded_directories_count": self.automatic_excluded_directories_count,
            "automatic_excluded_directories_by_group": dict(self.automatic_excluded_directories_by_group),
            "manual_excluded_directories_count": self.manual_excluded_directories_count,
            "exclusion_samples": [dict(item) for item in self.exclusion_samples],
            "performance": dict(self.performance),
        }


@dataclass(frozen=True)
class ScanPipelineResult:
    candidates: list[FileCandidate] = field(default_factory=list)
    results: list[SearchResult] = field(default_factory=list)
    analyzed_candidates_count: int = 0
    no_match_count: int = 0
    skipped_by_discard_count: int = 0
    unsupported_extension_count: int = 0
    stats: ScanPipelineStats | None = None
    errors: list[str] = field(default_factory=list)
    error_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats": self.stats.to_dict() if self.stats else {},
            "candidates_count": len(self.candidates),
            "candidate_preview": [candidate.to_dict() for candidate in self.candidates[:10]],
            "results_count": len(self.results),
            "analyzed_candidates_count": self.analyzed_candidates_count,
            "no_match_count": self.no_match_count,
            "skipped_by_discard_count": self.skipped_by_discard_count,
            "unsupported_extension_count": self.unsupported_extension_count,
            "errors": list(self.errors),
            "error_details": [dict(detail) for detail in self.error_details],
        }


@dataclass(frozen=True)
class _IssueRollup:
    issues_count: int = 0
    warnings_count: int = 0
    critical_errors_count: int = 0
    duplicate_occurrences_count: int = 0
    scan_issues_count: int = 0


@dataclass
class _ContentCounters:
    readers_executed_count: int = 0
    reader_errors_count: int = 0
    reader_success_count: int = 0
    reader_controlled_error_count: int = 0
    reader_worker_failed_count: int = 0
    reader_skipped_count: int = 0
    content_skipped_size_count: int = 0
    content_text_chars_count: int = 0


@dataclass
class _ScanCounters:
    files_seen_count: int = 0
    eligible_candidates_count: int = 0
    skipped_temporary_count: int = 0
    skipped_extension_count: int = 0
    skipped_file_keyword_count: int = 0
    skipped_exact_path_count: int = 0
    last_progress_percent: int | None = None
    last_progress_signature: tuple[int, ...] | None = None
    last_progress_emitted_at: float = 0.0
    source_exhausted: bool = False


@dataclass
class _ProcessAnalysisCounters:
    batches_submitted_count: int = 0
    batches_completed_count: int = 0
    batches_failed_count: int = 0
    fallback_batches_count: int = 0
    peak_pending_batches_count: int = 0
    analyzed_count: int = 0
    results_count: int = 0
    occurrences_count: int = 0
    no_match_count: int = 0
    skipped_by_discard_count: int = 0
    unsupported_count: int = 0
    worker_elapsed_total: float = 0.0
    worker_pids: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class _ReaderWorkResult:
    candidate: FileCandidate
    reader_result: ReaderResult
    analysis_outcome: CandidateAnalysisOutcome | None = None
    analysis_error: dict[str, Any] | None = None
    analysis_elapsed_seconds: float = 0.0


def _split_keywords(raw_value: Any) -> list[str]:
    if isinstance(raw_value, str):
        raw_items = raw_value.replace(";", ",").split(",")
    elif isinstance(raw_value, Iterable):
        raw_items = list(raw_value)
    else:
        raw_items = []

    keywords: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        clean_item = str(item or "").strip()
        lookup = clean_item.casefold()
        if not clean_item or lookup in seen:
            continue
        seen.add(lookup)
        keywords.append(clean_item)
    return keywords


def _split_paths(raw_value: Any) -> list[Path]:
    if isinstance(raw_value, str):
        raw_items = raw_value.replace(";", "\n").replace(",", "\n").splitlines()
    elif isinstance(raw_value, Iterable):
        raw_items = list(raw_value)
    else:
        raw_items = []

    paths: list[Path] = []
    seen: set[str] = set()
    for item in raw_items:
        clean_item = str(item or "").strip()
        if not clean_item:
            continue
        try:
            candidate = Path(clean_item).expanduser().resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            candidate = Path(clean_item).expanduser()
        lookup = str(candidate).casefold()
        if lookup in seen:
            continue
        paths.append(candidate)
        seen.add(lookup)
    return paths


def _normalize_path_for_match(path: Path) -> Path:
    try:
        return path.expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return path.expanduser()


def _path_matches_exact(path: Path, ignored_paths: list[Path]) -> bool:
    normalized_path = _normalize_path_for_match(path)
    path_text = str(normalized_path).casefold()
    return any(path_text == str(ignored_path).casefold() for ignored_path in ignored_paths)


def _path_inside_ignored_folder(path: Path, ignored_folders: list[Path]) -> bool:
    if not ignored_folders:
        return False
    normalized_path = _normalize_path_for_match(path)
    normalized_text = str(normalized_path).casefold()
    for ignored_folder in ignored_folders:
        ignored_text = str(ignored_folder).casefold()
        if normalized_text == ignored_text:
            return True
        try:
            normalized_path.relative_to(ignored_folder)
            return True
        except ValueError:
            continue
    return False


def _scan_error_to_text(error: ScanError) -> str:
    return f"[{error.error_type}] {error.path}: {error.message}"


def _scan_error_to_detail(error: ScanError, *, source: str = "filescan_core") -> dict[str, Any]:
    detail = error.to_dict()
    severity = (
        "error"
        if error.stage in {"source_validation", "root_validation", "validation"}
        else "warning"
    )
    detail.update(
        {
            "code": error.error_type,
            "source": source,
            "severity": severity,
        }
    )
    return detail


def _reader_error_detail(
    *,
    code: str,
    path: Path,
    message: str,
    stage: str,
    exception_type: str | None = None,
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "code": code,
        "error_type": code,
        "path": str(path),
        "stage": stage,
        "message": str(message or ""),
        "exception_type": exception_type,
        "source": "smart_filter",
        "severity": severity,
    }


def _normalized_issue_key(detail: Mapping[str, Any]) -> tuple[str, str, str, str]:
    path = os.path.normcase(str(detail.get("path") or "").strip())
    issue_type = str(detail.get("error_type") or detail.get("code") or "unknown_issue").strip().casefold()
    exception_type = str(detail.get("exception_type") or "").strip().casefold()
    message = " ".join(str(detail.get("message") or "").split()).casefold()
    return path, issue_type, exception_type, message


def _deduplicate_issues(
    errors: Iterable[str],
    error_details: Iterable[Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, Any]], _IssueRollup]:
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str, str]] = []
    raw_details = [dict(detail) for detail in error_details]

    for detail in raw_details:
        detail.setdefault("severity", "warning")
        key = _normalized_issue_key(detail)
        stage = str(detail.get("stage") or "").strip()
        if key not in merged:
            stored = dict(detail)
            stored["stages"] = [stage] if stage else []
            stored["occurrences_count"] = 1
            merged[key] = stored
            ordered_keys.append(key)
            continue

        stored = merged[key]
        stored["occurrences_count"] = int(stored.get("occurrences_count") or 1) + 1
        stages = list(stored.get("stages") or [])
        if stage and stage not in stages:
            stages.append(stage)
        stored["stages"] = stages
        if stored.get("severity") != "error" and detail.get("severity") == "error":
            stored["severity"] = "error"

    unique_details = [merged[key] for key in ordered_keys]
    unique_errors = [
        f"[{detail.get('error_type') or detail.get('code') or 'issue'}] "
        f"{detail.get('path') or ''}: {detail.get('message') or ''}".strip()
        for detail in unique_details
    ]

    # Compatibility fallback for unexpected plain messages without details.
    plain_errors = [str(message).strip() for message in errors if str(message).strip()]
    if len(plain_errors) > len(raw_details):
        unique_errors.extend(plain_errors[len(raw_details):])

    warnings_count = sum(1 for detail in unique_details if detail.get("severity") != "error")
    critical_errors_count = sum(1 for detail in unique_details if detail.get("severity") == "error")
    scan_issues_count = sum(1 for detail in unique_details if detail.get("source") == "filescan_core")
    return (
        unique_errors,
        unique_details,
        _IssueRollup(
            issues_count=len(unique_details),
            warnings_count=warnings_count,
            critical_errors_count=critical_errors_count,
            duplicate_occurrences_count=max(0, len(raw_details) - len(unique_details)),
            scan_issues_count=scan_issues_count,
        ),
    )


def _safe_file_candidate(path: Path, *, source: str) -> tuple[FileCandidate | None, ScanError | None]:
    try:
        return build_path_candidate(path, source=source), None
    except OSError as exc:
        return None, build_scan_error(path, exc, stage="file_metadata")


def _candidate_allowed_for_scan(
    candidate: FileCandidate,
    request: SearchRequest,
    ignored_file_keywords: list[str],
) -> tuple[bool, str]:
    if is_temporary_file(candidate):
        return False, "archivo_temporal"

    if keyword_matches_path(candidate.file_name, ignored_file_keywords) or keyword_matches_path(
        candidate.full_path,
        ignored_file_keywords,
    ):
        return False, "keyword_archivo_ignorada"

    allowed, reason = candidate_is_technically_allowed(candidate, request)
    return allowed, reason


def _content_size_limit_bytes() -> int | None:
    settings = get_settings()
    return get_max_content_file_size_bytes(str(settings.get("max_content_file_size") or "Sin límite"))


def _read_candidate_content(
    candidate: FileCandidate,
    *,
    max_size_bytes: int | None,
    analyzer: CandidateAnalyzer | None = None,
) -> _ReaderWorkResult:
    """Read one candidate and optionally match it in the same worker."""

    reader_result = read_file_content(candidate.full_path, max_size_bytes=max_size_bytes)
    if analyzer is None:
        return _ReaderWorkResult(candidate=candidate, reader_result=reader_result)

    enriched_candidate = replace(
        candidate,
        content_text=reader_result.text,
        content_reader=reader_result.reader_name,
        content_status=reader_result.status,
        content_error=reader_result.error,
        content_chars=reader_result.char_count,
    )
    analysis_started_at = perf_counter()
    try:
        outcome = analyzer.analyze(enriched_candidate)
        return _ReaderWorkResult(
            candidate=candidate,
            reader_result=reader_result,
            analysis_outcome=outcome,
            analysis_elapsed_seconds=perf_counter() - analysis_started_at,
        )
    except Exception as exc:  # pragma: no cover - defensive worker boundary.
        return _ReaderWorkResult(
            candidate=candidate,
            reader_result=reader_result,
            analysis_error={
                "code": "match_analysis_error",
                "error_type": "match_analysis_error",
                "path": str(candidate.full_path),
                "stage": "match_analysis",
                "message": str(exc),
                "exception_type": type(exc).__name__,
                "source": "smart_filter",
                "severity": "error",
            },
            analysis_elapsed_seconds=perf_counter() - analysis_started_at,
        )


def _candidate_from_reader_work(work_result: _ReaderWorkResult) -> FileCandidate:
    candidate = work_result.candidate
    reader_result = work_result.reader_result
    return FileCandidate.from_path(
        candidate.full_path,
        content_text=reader_result.text,
        source=candidate.source,
        content_reader=reader_result.reader_name,
        content_status=reader_result.status,
        content_error=reader_result.error,
    )


def _collect_reader_work(
    work_result: _ReaderWorkResult,
    *,
    candidates: list[FileCandidate] | None,
    counters: _ContentCounters,
    errors: list[str],
    error_details: list[dict[str, Any]],
) -> None:
    reader_result = work_result.reader_result
    candidate = work_result.candidate

    counters.readers_executed_count += 1
    counters.content_text_chars_count += reader_result.char_count

    if reader_result.status in {"ok", "unsupported_extension"}:
        counters.reader_success_count += 1
    elif reader_result.status == "reader_error":
        counters.reader_errors_count += 1
        counters.reader_controlled_error_count += 1
        errors.append(f"[reader_error] {candidate.full_path}: {reader_result.error}")
        error_details.append(
            _reader_error_detail(
                code="reader_error",
                path=candidate.full_path,
                message=reader_result.error,
                stage="content_read",
            )
        )
    elif reader_result.status == "skipped_by_size":
        counters.content_skipped_size_count += 1
        counters.reader_skipped_count += 1
        errors.append(f"[content_skipped_by_size] {candidate.full_path}: {reader_result.error}")
        error_details.append(
            _reader_error_detail(
                code="content_skipped_by_size",
                path=candidate.full_path,
                message=reader_result.error,
                stage="content_size_guard",
            )
        )
    elif reader_result.status not in {"ok", "unsupported_extension"}:
        counters.reader_errors_count += 1
        counters.reader_controlled_error_count += 1
        if reader_result.error:
            errors.append(f"[{reader_result.status}] {candidate.full_path}: {reader_result.error}")
            error_details.append(
                _reader_error_detail(
                    code=reader_result.status,
                    path=candidate.full_path,
                    message=reader_result.error,
                    stage="content_read",
                )
            )

    if candidates is not None:
        candidates.append(_candidate_from_reader_work(work_result))


def _collect_analysis_work(
    work_result: _ReaderWorkResult,
    *,
    ordered_results: list[tuple[int, tuple[SearchResult, ...]]],
    sequence: int,
    errors: list[str],
    error_details: list[dict[str, Any]],
) -> CandidateAnalysisOutcome:
    if work_result.analysis_error:
        detail = dict(work_result.analysis_error)
        errors.append(
            f"[match_analysis_error] {detail.get('path', work_result.candidate.full_path)}: "
            f"{detail.get('message', '')}"
        )
        error_details.append(detail)
        return CandidateAnalysisOutcome()

    outcome = work_result.analysis_outcome or CandidateAnalysisOutcome()
    if outcome.results:
        ordered_results.append((sequence, outcome.results))
    return outcome


def _flatten_ordered_results(
    ordered_results: list[tuple[int, tuple[SearchResult, ...]]],
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for _sequence, candidate_results in sorted(ordered_results, key=lambda item: item[0]):
        for result in candidate_results:
            results.append(replace(result, index=len(results) + 1))
    return results


def _count_result_occurrences(results: Iterable[SearchResult]) -> int:
    return sum(max(1, int(result.occurrence_count or 1)) for result in results)


def _scan_single_file(
    path: Path,
    request: SearchRequest,
    ignored_file_keywords: list[str],
    ignored_folder_paths: list[Path],
    ignored_file_paths: list[Path],
    *,
    analyzer: CandidateAnalyzer | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_requested: CancelRequestedCallback | None = None,
) -> ScanPipelineResult:
    errors: list[str] = []
    error_details: list[dict[str, Any]] = []
    files_seen_count = 0
    eligible_candidates_count = 0
    candidates: list[FileCandidate] = []
    ordered_results: list[tuple[int, tuple[SearchResult, ...]]] = []
    skipped_temporary_count = 0
    skipped_extension_count = 0
    skipped_file_keyword_count = 0
    skipped_exact_path_count = 0
    content_counters = _ContentCounters()
    analyzed_count = no_match_count = skipped_by_discard_count = unsupported_count = 0
    analysis_elapsed_total = 0.0

    _raise_if_cancelled(cancel_requested)
    if progress_callback:
        progress_callback(12, "Escaneando archivo individual...")

    if not path.exists():
        issue = build_validation_error(path, "path_not_found", "La ruta indicada no existe.", stage="source_validation")
        errors.append(_scan_error_to_text(issue))
        error_details.append(_scan_error_to_detail(issue))
    elif not path.is_file():
        issue = build_validation_error(path, "not_a_file", "El modo archivo individual requiere un archivo.", stage="source_validation")
        errors.append(_scan_error_to_text(issue))
        error_details.append(_scan_error_to_detail(issue))
    else:
        files_seen_count = 1
        if progress_callback:
            progress_callback(30, f"Archivo detectado: {path.name}")
        if _path_inside_ignored_folder(path, ignored_folder_paths) or _path_matches_exact(path, ignored_file_paths):
            skipped_exact_path_count += 1
            candidate = None
            error = None
        else:
            candidate, error = _safe_file_candidate(path, source="filescan_core_single_file_pipeline")
        if error:
            errors.append(_scan_error_to_text(error))
            error_details.append(_scan_error_to_detail(error))
        elif candidate:
            allowed, reason = _candidate_allowed_for_scan(candidate, request, ignored_file_keywords)
            if allowed:
                _raise_if_cancelled(cancel_requested)
                eligible_candidates_count = 1
                work_result = _read_candidate_content(
                    candidate,
                    max_size_bytes=_content_size_limit_bytes(),
                    analyzer=analyzer,
                )
                _collect_reader_work(
                    work_result,
                    candidates=None if analyzer else candidates,
                    counters=content_counters,
                    errors=errors,
                    error_details=error_details,
                )
                if analyzer:
                    outcome = _collect_analysis_work(
                        work_result,
                        ordered_results=ordered_results,
                        sequence=0,
                        errors=errors,
                        error_details=error_details,
                    )
                    analyzed_count += outcome.analyzed_count
                    no_match_count += outcome.no_match_count
                    skipped_by_discard_count += outcome.skipped_by_discard_count
                    unsupported_count += outcome.unsupported_extension_count
                    analysis_elapsed_total += work_result.analysis_elapsed_seconds
            elif reason == "archivo_temporal":
                skipped_temporary_count += 1
            elif reason == "extension_no_soportada":
                skipped_extension_count += 1
            elif reason == "keyword_archivo_ignorada":
                skipped_file_keyword_count += 1

    results = _flatten_ordered_results(ordered_results)
    if progress_callback:
        progress_callback(
            96 if analyzer else 62,
            (
                f"Lectura y análisis terminados: {_count_result_occurrences(results)} coincidencia(s) "
                f"en {len(results)} fila(s)"
                if analyzer
                else f"Lectura terminada: {len(candidates)} candidato(s) · {content_counters.readers_executed_count} reader(s)"
            ),
        )

    errors, error_details, issue_rollup = _deduplicate_issues(errors, error_details)
    stats = ScanPipelineStats(
        mode=ANALYSIS_MODE_FILE,
        root_path=str(path),
        directories_scanned_count=0,
        directories_skipped_count=0,
        files_seen_count=files_seen_count,
        candidates_count=eligible_candidates_count if analyzer else len(candidates),
        skipped_temporary_count=skipped_temporary_count,
        skipped_extension_count=skipped_extension_count,
        skipped_file_keyword_count=skipped_file_keyword_count,
        skipped_exact_path_count=skipped_exact_path_count,
        readers_executed_count=content_counters.readers_executed_count,
        reader_errors_count=content_counters.reader_errors_count,
        content_skipped_size_count=content_counters.content_skipped_size_count,
        content_text_chars_count=content_counters.content_text_chars_count,
        reader_workers_count=1 if content_counters.readers_executed_count else 0,
        reader_queue_capacity=0,
        reader_peak_in_flight_count=1 if content_counters.readers_executed_count else 0,
        reader_peak_queued_count=0,
        reader_succeeded_count=content_counters.reader_success_count,
        reader_failed_count=content_counters.reader_controlled_error_count,
        reader_controlled_error_count=content_counters.reader_controlled_error_count,
        reader_worker_failed_count=0,
        reader_skipped_count=content_counters.reader_skipped_count,
        reader_task_succeeded_count=content_counters.readers_executed_count,
        reader_task_failed_count=0,
        reader_peak_active_count=1 if content_counters.readers_executed_count else 0,
        match_analysis_mode="integrated_worker" if analyzer else "separate_pass",
        match_analyzed_candidates_count=analyzed_count,
        match_results_count=len(results),
        match_occurrences_count=_count_result_occurrences(results),
        match_no_match_count=no_match_count,
        match_skipped_by_discard_count=skipped_by_discard_count,
        match_unsupported_extension_count=unsupported_count,
        match_worker_elapsed_seconds_total=analysis_elapsed_total,
        content_released_after_analysis_count=eligible_candidates_count if analyzer else 0,
        retained_candidate_content_chars_count=0 if analyzer else content_counters.content_text_chars_count,
        scan_errors_count=issue_rollup.scan_issues_count,
        issues_count=issue_rollup.issues_count,
        warnings_count=issue_rollup.warnings_count,
        critical_errors_count=issue_rollup.critical_errors_count,
        duplicate_issue_occurrences_count=issue_rollup.duplicate_occurrences_count,
    )
    return ScanPipelineResult(
        candidates=candidates,
        results=results,
        analyzed_candidates_count=analyzed_count,
        no_match_count=no_match_count,
        skipped_by_discard_count=skipped_by_discard_count,
        unsupported_extension_count=unsupported_count,
        stats=stats,
        errors=errors,
        error_details=error_details,
    )


def _iter_directory_files(directory_path: Path, scan_errors: list[ScanError]) -> Iterable[Path]:
    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    yield Path(entry.path)
                except OSError as error:
                    scan_errors.append(build_scan_error(Path(entry.path), error, stage="file_entry_check"))
                    continue
    except OSError as error:
        scan_errors.append(build_scan_error(directory_path, error, stage="file_enumeration"))
        return


def scan_file_candidates(
    request: SearchRequest,
    *,
    analyze_during_read: bool = False,
    progress_callback: ProgressCallback | None = None,
    cancel_requested: CancelRequestedCallback | None = None,
) -> ScanPipelineResult:
    """Build candidates or run a bounded read + match pipeline.

    Normal locations preserve the proven integrated thread path. Broad roots use
    four I/O readers plus a spawned process pool that receives bounded batches,
    performs CPU-heavy normalization/matching, and returns compact outcomes.
    """

    _raise_if_cancelled(cancel_requested)
    state = request.form_state
    root_path = Path(state.path).expanduser()
    settings = get_settings()
    resource_policy = resolve_resource_policy(settings)
    ignored_folder_keywords = _split_keywords(settings.get("ignored_folder_keywords", ""))
    ignored_file_keywords = _split_keywords(settings.get("ignored_file_keywords", ""))
    ignored_folder_paths = _split_paths(settings.get("ignored_folder_paths", []))
    ignored_file_paths = _split_paths(settings.get("ignored_file_paths", []))
    exclusion_context = build_scan_exclusion_context(
        root_path=root_path,
        settings=settings,
        manual_folder_paths=ignored_folder_paths,
    )

    analysis_requested = bool(analyze_during_read)
    use_process_analysis = bool(
        analysis_requested
        and should_use_process_analysis(
            request,
            broad_scan_root_detected=exclusion_context.broad_scan_root_detected,
        )
    )
    thread_analyzer = (
        CandidateAnalyzer(request)
        if analysis_requested and not use_process_analysis
        else None
    )

    if progress_callback:
        progress_callback(8, "Preparando recorrido, colas y trabajadores...")

    if state.mode == ANALYSIS_MODE_FILE:
        return _scan_single_file(
            root_path,
            request,
            ignored_file_keywords,
            ignored_folder_paths,
            ignored_file_paths,
            analyzer=CandidateAnalyzer(request) if analysis_requested else None,
            progress_callback=progress_callback,
            cancel_requested=cancel_requested,
        )

    errors: list[str] = []
    error_details: list[dict[str, Any]] = []
    if state.mode != ANALYSIS_MODE_FOLDER:
        issue = build_validation_error(
            root_path,
            "invalid_mode",
            f"Modo no reconocido: {state.mode}",
            stage="source_validation",
        )
        errors.append(_scan_error_to_text(issue))
        error_details.append(_scan_error_to_detail(issue))

    if not root_path.exists():
        issue = build_validation_error(
            root_path,
            "path_not_found",
            "La carpeta indicada no existe.",
            stage="source_validation",
        )
        issue_errors, issue_details, issue_rollup = _deduplicate_issues(
            [_scan_error_to_text(issue)],
            [_scan_error_to_detail(issue)],
        )
        stats = ScanPipelineStats(
            mode=state.mode,
            root_path=str(root_path),
            scan_errors_count=issue_rollup.scan_issues_count,
            issues_count=issue_rollup.issues_count,
            warnings_count=issue_rollup.warnings_count,
            critical_errors_count=issue_rollup.critical_errors_count,
        )
        return ScanPipelineResult(
            candidates=[],
            stats=stats,
            errors=issue_errors,
            error_details=issue_details,
        )

    if not root_path.is_dir():
        issue = build_validation_error(
            root_path,
            "not_a_directory",
            "El modo carpeta requiere una carpeta.",
            stage="source_validation",
        )
        issue_errors, issue_details, issue_rollup = _deduplicate_issues(
            [_scan_error_to_text(issue)],
            [_scan_error_to_detail(issue)],
        )
        stats = ScanPipelineStats(
            mode=state.mode,
            root_path=str(root_path),
            scan_errors_count=issue_rollup.scan_issues_count,
            issues_count=issue_rollup.issues_count,
            warnings_count=issue_rollup.warnings_count,
            critical_errors_count=issue_rollup.critical_errors_count,
        )
        return ScanPipelineResult(
            candidates=[],
            stats=stats,
            errors=issue_errors,
            error_details=issue_details,
        )

    if _path_inside_ignored_folder(root_path, ignored_folder_paths):
        stats = ScanPipelineStats(
            mode=ANALYSIS_MODE_FOLDER,
            root_path=str(root_path),
            directories_scanned_count=0,
            directories_skipped_count=1,
            skipped_exact_path_count=1,
            policy_skipped_directories_count=1,
            manual_excluded_directories_count=1,
        )
        return ScanPipelineResult(candidates=[], stats=stats, errors=[], error_details=[])

    walk_errors: list[ScanError] = []
    walk_stats = DirectoryWalkStats()
    scan_counters = _ScanCounters()
    content_counters = _ContentCounters()
    worker_stats = WorkerPoolStats()
    process_counters = _ProcessAnalysisCounters()
    candidates: list[FileCandidate] = []
    ordered_reader_results: list[tuple[int, _ReaderWorkResult]] = []
    ordered_analysis_results: list[tuple[int, tuple[SearchResult, ...]]] = []
    match_analyzed_count = 0
    match_results_count = 0
    match_occurrences_count = 0
    match_no_match_count = 0
    match_skipped_by_discard_count = 0
    match_unsupported_count = 0
    match_worker_elapsed_total = 0.0
    max_content_size = _content_size_limit_bytes()
    excluded_by_group: Counter[str] = Counter()
    exclusion_samples: list[dict[str, str]] = []
    performance_monitor = PerformanceMonitor(
        enabled=resource_policy.monitor_enabled,
        sample_interval_seconds=resource_policy.sample_interval_seconds,
        timeline_enabled=resource_policy.timeline_enabled,
        timeline_interval_seconds=resource_policy.timeline_interval_seconds,
        logical_cores=resource_policy.logical_cores,
        physical_cores=resource_policy.physical_cores,
    )
    performance_data: dict[str, Any] = {}
    performance_monitor.start()

    reader_workers_count = (
        resource_policy.reader_workers if use_process_analysis else DEFAULT_MAX_WORKERS
    )
    analysis_processes_count = resource_policy.analysis_processes if use_process_analysis else 0
    effective_reader_queue_capacity = (
        resource_policy.reader_queue_capacity if use_process_analysis else DEFAULT_QUEUE_CAPACITY
    )
    process_pending_limit = (
        resource_policy.max_pending_batches if use_process_analysis else 0
    )
    process_executor: ProcessPoolExecutor | None = None
    process_pipeline_started_at: float | None = None
    process_pipeline_elapsed_seconds = 0.0
    process_pool_broken = False
    pending_analysis_futures: dict[
        Future[AnalysisBatchOutcome], tuple[AnalysisBatchItem, ...]
    ] = {}
    current_analysis_batch: list[AnalysisBatchItem] = []
    current_analysis_batch_chars = 0

    def record_directory_exclusion(match: DirectoryExclusionMatch) -> None:
        excluded_by_group[match.group_id] += 1
        if match.group_id == "manual_exact_paths":
            scan_counters.skipped_exact_path_count += 1
        if len(exclusion_samples) < 40:
            exclusion_samples.append(match.to_dict())

    if progress_callback:
        if use_process_analysis:
            mode_description = (
                f"{reader_workers_count} lectores + "
                f"{analysis_processes_count} procesos CPU · perfil {resource_policy.resource_profile}"
            )
        else:
            mode_description = f"{reader_workers_count} trabajadores integrados"
        progress_callback(
            10,
            (
                f"Escaneando con {mode_description}"
                + (" · modo amplio seguro" if exclusion_context.broad_scan_safe_enabled else "")
                + f": {root_path}"
            ),
        )

    def _format_count(value: int) -> str:
        return f"{max(0, int(value)):,}".replace(",", ".")

    def _current_match_analyzed_count() -> int:
        if use_process_analysis:
            return process_counters.analyzed_count
        return match_analyzed_count

    def _current_match_occurrences_count() -> int:
        if use_process_analysis:
            return process_counters.occurrences_count
        return match_occurrences_count

    def emit_scan_progress(
        *,
        completed: int = 0,
        active: int = 0,
        queued: int = 0,
        force: bool = False,
    ) -> None:
        if progress_callback is None:
            return

        analyzed_now = _current_match_analyzed_count()
        occurrences_now = _current_match_occurrences_count()
        pending_batches = len(pending_analysis_futures)

        if scan_counters.source_exhausted:
            total_candidates = scan_counters.eligible_candidates_count
            if analysis_requested:
                finished = analyzed_now if use_process_analysis else completed
                completion_ratio = (finished / total_candidates) if total_candidates else 1.0
                percent: int | None = min(95, 60 + int(completion_ratio * 35))
                stage_text = (
                    "Finalizando análisis CPU"
                    if use_process_analysis
                    else "Finalizando lectura y análisis"
                )
            else:
                completion_ratio = (completed / total_candidates) if total_candidates else 1.0
                percent = min(64, 60 + int(completion_ratio * 4))
                stage_text = "Finalizando lecturas"
        else:
            percent = None
            stage_text = "Escaneando"

        signature = (
            walk_stats.scanned_count,
            scan_counters.files_seen_count,
            scan_counters.eligible_candidates_count,
            completed,
            active,
            queued,
            analyzed_now,
            occurrences_now,
            pending_batches,
        )
        now = monotonic()
        counters_changed = signature != scan_counters.last_progress_signature
        progress_emit_interval = _progress_emit_interval_seconds(
            broad_scan_root_detected=exclusion_context.broad_scan_root_detected,
        )
        enough_time_elapsed = (
            now - scan_counters.last_progress_emitted_at
        ) >= progress_emit_interval
        completed_all = bool(
            scan_counters.source_exhausted
            and (
                analyzed_now == scan_counters.eligible_candidates_count
                if analysis_requested and use_process_analysis
                else completed == scan_counters.eligible_candidates_count
            )
        )
        if not force and not completed_all and (not counters_changed or not enough_time_elapsed):
            return

        scan_counters.last_progress_percent = percent
        scan_counters.last_progress_signature = signature
        scan_counters.last_progress_emitted_at = now
        analysis_text = ""
        if analysis_requested:
            analysis_text = (
                f" · analizados {_format_count(analyzed_now)}"
                f" · coincidencias {_format_count(occurrences_now)}"
            )
            if use_process_analysis:
                analysis_text += f" · lotes CPU {pending_batches}"

        progress_callback(
            percent,
            f"{stage_text} · carpetas {_format_count(walk_stats.scanned_count)} · "
            f"archivos {_format_count(scan_counters.files_seen_count)} · "
            f"candidatos {_format_count(scan_counters.eligible_candidates_count)} · "
            f"leídos {_format_count(completed)}"
            + analysis_text
            + f" · lectores activos {active} · cola {queued}",
        )

    def iter_eligible_candidates() -> Iterator[FileCandidate]:
        for directory_path, _depth in iter_safe_directories(
            root_path=root_path,
            skipped_directory_names=DEFAULT_SMARTFILTER_SKIPPED_DIRECTORY_NAMES,
            skipped_directory_keywords=ignored_folder_keywords,
            follow_symlinks=False,
            use_default_skipped_directory_names=not exclusion_context.broad_scan_safe_enabled,
            errors=walk_errors,
            stats=walk_stats,
            exclusion_policy=exclusion_context.policy,
            directory_excluded_callback=record_directory_exclusion,
        ):
            if _is_cancel_requested(cancel_requested):
                return
            for file_path in _iter_directory_files(directory_path, walk_errors):
                if _is_cancel_requested(cancel_requested):
                    return
                if _path_inside_ignored_folder(file_path, ignored_folder_paths) or _path_matches_exact(
                    file_path,
                    ignored_file_paths,
                ):
                    scan_counters.skipped_exact_path_count += 1
                    continue

                scan_counters.files_seen_count += 1
                candidate, error = _safe_file_candidate(
                    file_path,
                    source="filescan_core_folder_pipeline",
                )
                if error:
                    errors.append(_scan_error_to_text(error))
                    error_details.append(_scan_error_to_detail(error))
                    continue
                if not candidate:
                    continue

                allowed, reason = _candidate_allowed_for_scan(candidate, request, ignored_file_keywords)
                if allowed:
                    scan_counters.eligible_candidates_count += 1
                    in_flight = max(0, worker_stats.submitted_count - worker_stats.completed_count)
                    queued_count = max(0, in_flight - reader_workers_count)
                    emit_scan_progress(
                        completed=worker_stats.completed_count,
                        active=max(0, in_flight - queued_count),
                        queued=queued_count,
                    )
                    yield candidate
                elif reason == "archivo_temporal":
                    scan_counters.skipped_temporary_count += 1
                elif reason == "extension_no_soportada":
                    scan_counters.skipped_extension_count += 1
                elif reason == "keyword_archivo_ignorada":
                    scan_counters.skipped_file_keyword_count += 1

                if scan_counters.files_seen_count == 1 or scan_counters.files_seen_count % 25 == 0:
                    in_flight = max(0, worker_stats.submitted_count - worker_stats.completed_count)
                    queued_count = max(0, in_flight - reader_workers_count)
                    emit_scan_progress(
                        completed=worker_stats.completed_count,
                        active=max(0, in_flight - queued_count),
                        queued=queued_count,
                    )

        if not _is_cancel_requested(cancel_requested):
            scan_counters.source_exhausted = True
            in_flight = max(0, worker_stats.submitted_count - worker_stats.completed_count)
            queued_count = max(0, in_flight - reader_workers_count)
            emit_scan_progress(
                completed=worker_stats.completed_count,
                active=max(0, in_flight - queued_count),
                queued=queued_count,
                force=True,
            )

    def reader_worker(candidate: FileCandidate) -> _ReaderWorkResult:
        return _read_candidate_content(
            candidate,
            max_size_bytes=max_content_size,
            analyzer=thread_analyzer,
        )

    def reader_progress(event: Mapping[str, object]) -> None:
        emit_scan_progress(
            completed=int(event.get("completed", 0)),
            active=int(event.get("active", 0)),
            queued=int(event.get("queued", 0)),
        )

    def collect_process_batch_outcome(batch_outcome: AnalysisBatchOutcome) -> None:
        process_counters.batches_completed_count += 1
        process_counters.worker_elapsed_total += float(batch_outcome.elapsed_seconds or 0.0)
        if batch_outcome.worker_pid:
            process_counters.worker_pids.add(int(batch_outcome.worker_pid))

        for item_outcome in batch_outcome.items:
            if item_outcome.error_detail:
                detail = dict(item_outcome.error_detail)
                errors.append(
                    f"[{detail.get('error_type') or detail.get('code') or 'match_analysis_process_error'}] "
                    f"{detail.get('path') or ''}: {detail.get('message') or ''}"
                )
                error_details.append(detail)
                continue

            outcome = item_outcome.outcome or CandidateAnalysisOutcome()
            if outcome.results:
                ordered_analysis_results.append((item_outcome.sequence, outcome.results))
            process_counters.analyzed_count += outcome.analyzed_count
            process_counters.results_count += len(outcome.results)
            process_counters.occurrences_count += _count_result_occurrences(outcome.results)
            process_counters.no_match_count += outcome.no_match_count
            process_counters.skipped_by_discard_count += outcome.skipped_by_discard_count
            process_counters.unsupported_count += outcome.unsupported_extension_count

    def process_failed_batch(
        batch: tuple[AnalysisBatchItem, ...],
        error: BaseException,
    ) -> None:
        nonlocal process_pool_broken
        if isinstance(error, BrokenProcessPool) or type(error).__name__ == "BrokenProcessPool":
            process_pool_broken = True
        process_counters.batches_failed_count += 1
        detail = {
            "code": "analysis_process_batch_error",
            "error_type": "analysis_process_batch_error",
            "path": str(root_path),
            "stage": "match_analysis_process_batch",
            "message": str(error),
            "exception_type": type(error).__name__,
            "source": "smart_filter",
            "severity": "warning",
            "batch_items_count": len(batch),
        }
        errors.append(
            f"[analysis_process_batch_error] {root_path}: {type(error).__name__}: {error}"
        )
        error_details.append(detail)
        _raise_if_cancelled(cancel_requested)
        process_counters.fallback_batches_count += 1
        fallback_outcome = analyze_candidate_batch_locally(request, batch)
        collect_process_batch_outcome(fallback_outcome)

    def drain_process_batches(*, wait_for_all: bool = False) -> None:
        if not pending_analysis_futures:
            return
        _raise_if_cancelled(cancel_requested)
        if wait_for_all:
            completed_futures, _ = wait(
                tuple(pending_analysis_futures),
                timeout=0.10 if cancel_requested is not None else None,
            )
        else:
            completed_futures, _ = wait(
                tuple(pending_analysis_futures),
                timeout=0.10 if cancel_requested is not None else None,
                return_when=FIRST_COMPLETED,
            )
        if not completed_futures:
            _raise_if_cancelled(cancel_requested)
            return
        for future in completed_futures:
            batch = pending_analysis_futures.pop(future)
            try:
                collect_process_batch_outcome(future.result())
            except BaseException as exc:  # process crash / serialization / broken pool.
                process_failed_batch(batch, exc)
        emit_scan_progress(
            completed=worker_stats.completed_count,
            active=max(
                0,
                min(
                    reader_workers_count,
                    worker_stats.submitted_count - worker_stats.completed_count,
                ),
            ),
            queued=max(
                0,
                worker_stats.submitted_count
                - worker_stats.completed_count
                - reader_workers_count,
            ),
        )

    def flush_process_batch() -> None:
        nonlocal current_analysis_batch, current_analysis_batch_chars
        if not current_analysis_batch:
            return
        batch = tuple(current_analysis_batch)
        current_analysis_batch = []
        current_analysis_batch_chars = 0
        if process_pool_broken:
            process_counters.fallback_batches_count += 1
            collect_process_batch_outcome(analyze_candidate_batch_locally(request, batch))
            return
        if process_executor is None:
            raise RuntimeError("El pool de procesos CPU no está disponible.")
        performance_monitor.set_phase("read_and_analyze_overlap")
        try:
            future = process_executor.submit(analyze_candidate_batch, batch)
        except BaseException as exc:
            process_failed_batch(batch, exc)
            return
        pending_analysis_futures[future] = batch
        process_counters.batches_submitted_count += 1
        process_counters.peak_pending_batches_count = max(
            process_counters.peak_pending_batches_count,
            len(pending_analysis_futures),
        )
        while len(pending_analysis_futures) >= process_pending_limit:
            # Real backpressure: never let the producer outrun the configured
            # process budget. The old single drain attempt could time out and
            # let the queue grow far beyond its declared limit.
            drain_process_batches(wait_for_all=False)
            _raise_if_cancelled(cancel_requested)

    def enqueue_process_candidate(sequence: int, work_result: _ReaderWorkResult) -> None:
        nonlocal current_analysis_batch_chars
        enriched_candidate = _candidate_from_reader_work(work_result)
        item = AnalysisBatchItem(sequence=sequence, candidate=enriched_candidate)
        current_analysis_batch.append(item)
        current_analysis_batch_chars += max(
            0,
            int(work_result.reader_result.char_count or len(enriched_candidate.content_text)),
        )
        if (
            len(current_analysis_batch) >= PROCESS_BATCH_MAX_ITEMS
            or current_analysis_batch_chars >= PROCESS_BATCH_MAX_CONTENT_CHARS
        ):
            flush_process_batch()

    try:
        if use_process_analysis:
            process_pipeline_started_at = perf_counter()
            process_executor = ProcessPoolExecutor(
                max_workers=analysis_processes_count,
                mp_context=get_context("spawn"),
                initializer=initialize_analysis_process,
                initargs=(request,),
            )

        for task_result in iter_bounded_workers(
            items=iter_eligible_candidates(),
            worker=reader_worker,
            max_workers=reader_workers_count,
            queue_capacity=effective_reader_queue_capacity,
            preserve_input_order=False,
            progress_callback=reader_progress,
            cancel_requested=cancel_requested,
            stats=worker_stats,
            thread_name_prefix="smartfilter-reader",
        ):
            _raise_if_cancelled(cancel_requested)
            if not task_result.succeeded or task_result.value is None:
                content_counters.readers_executed_count += 1
                content_counters.reader_errors_count += 1
                content_counters.reader_worker_failed_count += 1
                errors.append(
                    f"[reader_worker_error] {task_result.item.full_path}: "
                    f"{task_result.error_type or 'Error'}: {task_result.error_message}"
                )
                error_details.append(
                    _reader_error_detail(
                        code="reader_worker_error",
                        path=task_result.item.full_path,
                        message=task_result.error_message,
                        stage="reader_worker",
                        exception_type=task_result.error_type,
                        severity="error",
                    )
                )
                continue

            work_result = task_result.value
            if not analysis_requested:
                ordered_reader_results.append((task_result.sequence, work_result))
                continue

            _collect_reader_work(
                work_result,
                candidates=None,
                counters=content_counters,
                errors=errors,
                error_details=error_details,
            )

            if use_process_analysis:
                enqueue_process_candidate(task_result.sequence, work_result)
                continue

            outcome = _collect_analysis_work(
                work_result,
                ordered_results=ordered_analysis_results,
                sequence=task_result.sequence,
                errors=errors,
                error_details=error_details,
            )
            match_analyzed_count += outcome.analyzed_count
            match_results_count += len(outcome.results)
            match_occurrences_count += _count_result_occurrences(outcome.results)
            match_no_match_count += outcome.no_match_count
            match_skipped_by_discard_count += outcome.skipped_by_discard_count
            match_unsupported_count += outcome.unsupported_extension_count
            match_worker_elapsed_total += work_result.analysis_elapsed_seconds

        _raise_if_cancelled(cancel_requested)

        if use_process_analysis:
            performance_monitor.set_phase("pipeline_drain")
            flush_process_batch()
            while pending_analysis_futures:
                drain_process_batches(wait_for_all=False)
                _raise_if_cancelled(cancel_requested)
            if process_pipeline_started_at is not None:
                process_pipeline_elapsed_seconds = perf_counter() - process_pipeline_started_at
        elif not analysis_requested:
            for _sequence, work_result in sorted(
                ordered_reader_results,
                key=lambda item: item[0],
            ):
                _collect_reader_work(
                    work_result,
                    candidates=candidates,
                    counters=content_counters,
                    errors=errors,
                    error_details=error_details,
                )
    except SearchCancelledError:
        if process_executor is not None:
            for future in tuple(pending_analysis_futures):
                future.cancel()
            process_executor.shutdown(wait=False, cancel_futures=True)
            process_executor = None
        raise
    finally:
        if process_executor is not None:
            process_executor.shutdown(wait=True, cancel_futures=False)
        performance_data = performance_monitor.stop()

    if use_process_analysis:
        match_analyzed_count = process_counters.analyzed_count
        match_results_count = process_counters.results_count
        match_occurrences_count = process_counters.occurrences_count
        match_no_match_count = process_counters.no_match_count
        match_skipped_by_discard_count = process_counters.skipped_by_discard_count
        match_unsupported_count = process_counters.unsupported_count
        match_worker_elapsed_total = process_counters.worker_elapsed_total

    results = _flatten_ordered_results(ordered_analysis_results)
    if progress_callback:
        if analysis_requested:
            backend_label = (
                f"CPU paralelo ({analysis_processes_count} procesos)"
                if use_process_analysis
                else "trabajadores integrados"
            )
            progress_callback(
                96,
                f"Lectura y análisis terminados con {backend_label}: "
                f"{scan_counters.eligible_candidates_count} candidato(s) · "
                f"{_count_result_occurrences(results)} coincidencia(s) en {len(results)} fila(s) · "
                f"pico cola={worker_stats.peak_queued_count}",
            )
        else:
            progress_callback(
                64,
                "Lectura paralela terminada: "
                f"{len(candidates)} candidato(s) · "
                f"{content_counters.readers_executed_count} reader(s) · "
                f"pico cola={worker_stats.peak_queued_count}",
            )

    errors.extend(_scan_error_to_text(error) for error in walk_errors)
    error_details.extend(_scan_error_to_detail(error) for error in walk_errors)
    errors, error_details, issue_rollup = _deduplicate_issues(errors, error_details)
    classified_skipped_count = (
        walk_stats.policy_skipped_count
        + walk_stats.link_or_reparse_skipped_count
        + walk_stats.name_skipped_count
        + walk_stats.keyword_skipped_count
        + walk_stats.revisited_skipped_count
    )
    unclassified_skipped_count = max(0, walk_stats.skipped_count - classified_skipped_count)

    if use_process_analysis:
        match_analysis_mode = "integrated_process_batch"
        analysis_backend = "spawn_process_pool"
    elif analysis_requested:
        match_analysis_mode = "integrated_worker"
        analysis_backend = "thread_pool_integrated"
    else:
        match_analysis_mode = "separate_pass"
        analysis_backend = "separate_pass"

    analysis_pid_set = {int(pid) for pid in process_counters.worker_pids}
    runtime_process_records = list(performance_data.get("analysis_processes") or [])
    performance_data["analysis_processes"] = [
        dict(item)
        for item in runtime_process_records
        if int(item.get("pid") or 0) in analysis_pid_set
    ]
    performance_data["other_child_processes"] = [
        dict(item)
        for item in runtime_process_records
        if int(item.get("pid") or 0) not in analysis_pid_set
    ]

    performance_payload = {
        "resource_policy": resource_policy.to_dict(),
        "runtime": performance_data,
        "pipeline": {
            "reader_workers": reader_workers_count,
            "reader_queue_capacity": effective_reader_queue_capacity,
            "analysis_processes": analysis_processes_count,
            "max_pending_batches": process_pending_limit,
            "peak_pending_batches": process_counters.peak_pending_batches_count,
            "pending_limit_respected": (
                process_counters.peak_pending_batches_count <= process_pending_limit
                if use_process_analysis else True
            ),
            "batches_submitted": process_counters.batches_submitted_count,
            "batches_completed": process_counters.batches_completed_count,
            "batches_failed": process_counters.batches_failed_count,
            "fallback_batches": process_counters.fallback_batches_count,
        },
    }
    runtime_cpu = dict(performance_data.get("cpu") or {})
    if (
        use_process_analysis
        and int(performance_data.get("samples_count") or 0) >= 5
        and float(runtime_cpu.get("children_average_cores") or 0.0) < 0.35
    ):
        low_cpu_detail = {
            "code": "cpu_parallel_low_utilization",
            "error_type": "cpu_parallel_low_utilization",
            "path": str(root_path),
            "stage": "performance_monitor",
            "message": "El análisis CPU paralelo tuvo una utilización promedio inusualmente baja.",
            "source": "smart_filter",
            "severity": "warning",
            "average_child_cpu_cores": runtime_cpu.get("children_average_cores", 0.0),
        }
        errors.append(
            "[cpu_parallel_low_utilization] "
            f"{root_path}: promedio={runtime_cpu.get('children_average_cores', 0.0)} núcleo(s)"
        )
        error_details.append(low_cpu_detail)
        errors, error_details, issue_rollup = _deduplicate_issues(errors, error_details)

    stats = ScanPipelineStats(
        mode=ANALYSIS_MODE_FOLDER,
        root_path=str(root_path),
        directories_scanned_count=walk_stats.scanned_count,
        directories_skipped_count=walk_stats.skipped_count,
        files_seen_count=scan_counters.files_seen_count,
        candidates_count=(
            scan_counters.eligible_candidates_count
            if analysis_requested
            else len(candidates)
        ),
        skipped_temporary_count=scan_counters.skipped_temporary_count,
        skipped_extension_count=scan_counters.skipped_extension_count,
        skipped_file_keyword_count=scan_counters.skipped_file_keyword_count,
        skipped_exact_path_count=scan_counters.skipped_exact_path_count,
        readers_executed_count=content_counters.readers_executed_count,
        reader_errors_count=content_counters.reader_errors_count,
        content_skipped_size_count=content_counters.content_skipped_size_count,
        content_text_chars_count=content_counters.content_text_chars_count,
        reader_workers_count=worker_stats.max_workers,
        reader_queue_capacity=worker_stats.queue_capacity,
        reader_peak_in_flight_count=worker_stats.peak_in_flight_count,
        reader_peak_queued_count=worker_stats.peak_queued_count,
        reader_pipeline_elapsed_seconds=worker_stats.elapsed_seconds,
        reader_succeeded_count=content_counters.reader_success_count,
        reader_failed_count=(
            content_counters.reader_controlled_error_count
            + content_counters.reader_worker_failed_count
        ),
        reader_controlled_error_count=content_counters.reader_controlled_error_count,
        reader_worker_failed_count=content_counters.reader_worker_failed_count,
        reader_skipped_count=content_counters.reader_skipped_count,
        reader_task_succeeded_count=worker_stats.succeeded_count,
        reader_task_failed_count=worker_stats.failed_count,
        reader_peak_active_count=min(
            worker_stats.max_workers,
            worker_stats.peak_in_flight_count,
        ),
        files_seen_per_second=(
            scan_counters.files_seen_count / worker_stats.elapsed_seconds
            if worker_stats.elapsed_seconds > 0
            else 0.0
        ),
        candidates_read_per_second=(
            content_counters.readers_executed_count / worker_stats.elapsed_seconds
            if worker_stats.elapsed_seconds > 0
            else 0.0
        ),
        match_analysis_mode=match_analysis_mode,
        analysis_backend=analysis_backend,
        analysis_processes_count=analysis_processes_count,
        analysis_batch_max_items=PROCESS_BATCH_MAX_ITEMS if use_process_analysis else 0,
        analysis_batch_max_content_chars=(
            PROCESS_BATCH_MAX_CONTENT_CHARS if use_process_analysis else 0
        ),
        analysis_batches_submitted_count=process_counters.batches_submitted_count,
        analysis_batches_completed_count=process_counters.batches_completed_count,
        analysis_batches_failed_count=process_counters.batches_failed_count,
        analysis_fallback_batches_count=process_counters.fallback_batches_count,
        analysis_peak_pending_batches_count=process_counters.peak_pending_batches_count,
        analysis_worker_pids=tuple(sorted(process_counters.worker_pids)),
        analysis_pipeline_elapsed_seconds=process_pipeline_elapsed_seconds,
        analysis_candidates_per_second=(
            match_analyzed_count / process_pipeline_elapsed_seconds
            if use_process_analysis and process_pipeline_elapsed_seconds > 0
            else 0.0
        ),
        analysis_payload_content_chars_count=(
            content_counters.content_text_chars_count if use_process_analysis else 0
        ),
        analysis_cancelled=bool(worker_stats.cancellation_requested),
        match_analyzed_candidates_count=match_analyzed_count,
        match_results_count=len(results),
        match_occurrences_count=_count_result_occurrences(results),
        match_no_match_count=match_no_match_count,
        match_skipped_by_discard_count=match_skipped_by_discard_count,
        match_unsupported_extension_count=match_unsupported_count,
        match_worker_elapsed_seconds_total=match_worker_elapsed_total,
        content_released_after_analysis_count=(
            content_counters.readers_executed_count if analysis_requested else 0
        ),
        retained_candidate_content_chars_count=(
            0 if analysis_requested else content_counters.content_text_chars_count
        ),
        scan_errors_count=issue_rollup.scan_issues_count,
        issues_count=issue_rollup.issues_count,
        warnings_count=issue_rollup.warnings_count,
        critical_errors_count=issue_rollup.critical_errors_count,
        duplicate_issue_occurrences_count=issue_rollup.duplicate_occurrences_count,
        policy_skipped_directories_count=walk_stats.policy_skipped_count,
        link_or_reparse_skipped_directories_count=walk_stats.link_or_reparse_skipped_count,
        name_skipped_directories_count=walk_stats.name_skipped_count,
        keyword_skipped_directories_count=walk_stats.keyword_skipped_count,
        revisited_skipped_directories_count=walk_stats.revisited_skipped_count,
        unclassified_skipped_directories_count=unclassified_skipped_count,
        broad_scan_root_detected=exclusion_context.broad_scan_root_detected,
        broad_scan_safe_enabled=exclusion_context.broad_scan_safe_enabled,
        automatic_exclusion_groups=exclusion_context.active_group_ids,
        automatic_excluded_directories_count=sum(
            count
            for group_id, count in excluded_by_group.items()
            if group_id != "manual_exact_paths"
        ),
        automatic_excluded_directories_by_group={
            option.group_id: excluded_by_group.get(option.group_id, 0)
            for option in BROAD_SCAN_OPTIONS
            if option.group_id in exclusion_context.active_group_ids
        },
        manual_excluded_directories_count=excluded_by_group.get("manual_exact_paths", 0),
        exclusion_samples=tuple(exclusion_samples),
        performance=performance_payload,
    )
    return ScanPipelineResult(
        candidates=candidates,
        results=results,
        analyzed_candidates_count=match_analyzed_count,
        no_match_count=match_no_match_count,
        skipped_by_discard_count=match_skipped_by_discard_count,
        unsupported_extension_count=match_unsupported_count,
        stats=stats,
        errors=errors,
        error_details=error_details,
    )
