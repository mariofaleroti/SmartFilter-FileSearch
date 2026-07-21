from __future__ import annotations

from dataclasses import dataclass, field
from os.path import normcase, normpath
from pathlib import Path
from typing import Any, Iterable

from date_time_core import local_now_iso, utc_now_iso

from smart_filter.domain.search_form_state import SearchFormState


@dataclass(frozen=True)
class FileCandidate:
    """File-like input consumed by Smart Filter's own matching engine.

    Step 4 intentionally does not own deep filesystem traversal. In Step 5,
    FileScanCore will feed these candidates from a safe scanner pipeline.
    """

    full_path: str
    file_name: str
    extension: str
    folder_path: str
    content_text: str = ""
    source: str = "manual_candidate"
    size_bytes: int | None = None
    content_reader: str = "not_loaded"
    content_status: str = "not_loaded"
    content_error: str = ""
    content_chars: int = 0

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        content_text: str = "",
        source: str = "path_preview",
        content_reader: str = "not_loaded",
        content_status: str = "not_loaded",
        content_error: str = "",
    ) -> "FileCandidate":
        item = Path(path)
        content = str(content_text or "")
        return cls(
            full_path=str(item),
            file_name=item.name or str(item),
            extension=item.suffix.lower(),
            folder_path=str(item.parent),
            content_text=content,
            source=source,
            size_bytes=item.stat().st_size if item.exists() and item.is_file() else None,
            content_reader=content_reader,
            content_status=content_status,
            content_error=content_error,
            content_chars=len(content),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_path": self.full_path,
            "file_name": self.file_name,
            "extension": self.extension,
            "folder_path": self.folder_path,
            "content_text_preview": self.content_text[:240],
            "source": self.source,
            "size_bytes": self.size_bytes,
            "content_reader": self.content_reader,
            "content_status": self.content_status,
            "content_error": self.content_error,
            "content_chars": self.content_chars,
        }


@dataclass(frozen=True)
class SearchRequest:
    form_state: SearchFormState
    search_text: str = ""
    category_name: str = "Ninguna"
    category_terms: list[str] = field(default_factory=list)
    context_terms: list[str] = field(default_factory=list)
    category_exclude_terms: list[str] = field(default_factory=list)
    discard_filter_name: str = "Ninguna"
    discard_terms: list[str] = field(default_factory=list)
    temporary_exclusion_terms: list[str] = field(default_factory=list)
    search_scope: str = "Nombre y contenido"
    file_types: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    category_search_mode: str = "Todo el contenido"
    category_target_fields: list[str] = field(default_factory=list)
    generated_at_utc: str = field(default_factory=utc_now_iso)
    generated_at_local: str = field(default_factory=local_now_iso)

    @property
    def has_text_filter(self) -> bool:
        return bool(self.search_text.strip())

    @property
    def has_category_filter(self) -> bool:
        return bool(self.category_terms)

    @property
    def has_context_filter(self) -> bool:
        return bool(self.context_terms)

    @property
    def has_discard_filter(self) -> bool:
        return bool(self.discard_terms or self.category_exclude_terms or self.temporary_exclusion_terms)

    @property
    def all_exclusion_terms(self) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        for group in (self.category_exclude_terms, self.discard_terms, self.temporary_exclusion_terms):
            for term in group:
                clean_term = str(term or "").strip()
                lookup = clean_term.casefold()
                if not clean_term or lookup in seen:
                    continue
                seen.add(lookup)
                terms.append(clean_term)
        return terms

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_state": self.form_state.to_dict(),
            "search_text": self.search_text,
            "category_name": self.category_name,
            "category_terms_count": len(self.category_terms),
            "category_terms_sample": self.category_terms[:8],
            "context_terms": list(self.context_terms),
            "category_exclude_terms": list(self.category_exclude_terms),
            "discard_filter_name": self.discard_filter_name,
            "discard_terms": list(self.discard_terms),
            "temporary_exclusion_terms": list(self.temporary_exclusion_terms),
            "search_scope": self.search_scope,
            "file_types": list(self.file_types),
            "extensions": list(self.extensions),
            "category_search_mode": self.category_search_mode,
            "category_target_fields": list(self.category_target_fields),
            "generated_at_local": self.generated_at_local,
            "generated_at_utc": self.generated_at_utc,
        }


@dataclass(frozen=True)
class MatchDecision:
    matched: bool
    skipped: bool = False
    skip_reason: str = ""
    match_source: str = "Sin coincidencia"
    matched_terms: list[str] = field(default_factory=list)
    exclusion_terms: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "match_source": self.match_source,
            "matched_terms": list(self.matched_terms),
            "exclusion_terms": list(self.exclusion_terms),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SearchResult:
    index: int
    candidate: FileCandidate
    match_source: str
    matches: str
    matched_terms: list[str] = field(default_factory=list)
    status: str = "Coincidencia"
    category_name: str = "Ninguna"
    discard_filter_name: str = "Ninguna"
    occurrence_number: int | None = None
    line_number: int | None = None
    row_number: int | None = None
    sheet_name: str = ""
    location_label: str = ""
    preview_text: str = ""
    occurrence_count: int = 1
    match_locations: list[dict[str, Any]] = field(default_factory=list)
    grouped_by_file: bool = False

    @property
    def file_name(self) -> str:
        return self.candidate.file_name

    @property
    def extension(self) -> str:
        return self.candidate.extension

    @property
    def full_path(self) -> str:
        return self.candidate.full_path

    @property
    def folder_path(self) -> str:
        return self.candidate.folder_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "file_name": self.file_name,
            "extension": self.extension,
            "folder_path": self.folder_path,
            "full_path": self.full_path,
            "match_source": self.match_source,
            "matches": self.matches,
            "matched_terms": list(self.matched_terms),
            "category_name": self.category_name,
            "discard_filter_name": self.discard_filter_name,
            "candidate_source": self.candidate.source,
            "content_reader": self.candidate.content_reader,
            "content_status": self.candidate.content_status,
            "content_chars": self.candidate.content_chars,
            "occurrence_number": self.occurrence_number,
            "line_number": self.line_number,
            "row_number": self.row_number,
            "sheet_name": self.sheet_name,
            "location_label": self.location_label,
            "preview_text": self.preview_text,
            "occurrence_count": max(1, int(self.occurrence_count or 1)),
            "match_locations": [dict(item) for item in self.match_locations],
            "grouped_by_file": bool(self.grouped_by_file),
        }

    def to_table_row(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "file_name": self.file_name,
            "file_type": self.extension or "sin extensión",
            "location": self.location_label or "Archivo",
            "match": self.matches,
            "occurrence_count": max(1, int(self.occurrence_count or 1)),
            "grouped_by_file": bool(self.grouped_by_file),
            "terms": " | ".join(self.matched_terms),
            "preview": self.preview_text,
            "category": self.category_name,
            "discard": self.discard_filter_name,
            "source": self.match_source,
            "reader": self.candidate.content_reader,
            "content_status": self.candidate.content_status,
            "folder_path": self.folder_path,
            "path": self.full_path,
        }


def count_unique_result_candidates(results: Iterable[SearchResult]) -> int:
    """Count matched file candidates without confusing them with occurrences."""

    unique_paths: set[str] = set()
    fallback_indexes: set[int] = set()
    for result in results:
        raw_path = str(result.full_path or "").strip()
        if raw_path:
            unique_paths.add(normcase(normpath(raw_path)))
        else:
            fallback_indexes.add(int(result.index))
    return len(unique_paths) + len(fallback_indexes)


@dataclass(frozen=True)
class SearchSummary:
    request: SearchRequest
    results: list[SearchResult] = field(default_factory=list)
    analyzed_candidates_count: int = 0
    matched_candidates_count: int = 0
    no_match_count: int = 0
    skipped_by_discard_count: int = 0
    unsupported_extension_count: int = 0
    errors: list[str] = field(default_factory=list)
    error_details: list[dict[str, Any]] = field(default_factory=list)
    scan_stats: dict[str, Any] = field(default_factory=dict)
    generated_at_utc: str = field(default_factory=utc_now_iso)
    generated_at_local: str = field(default_factory=local_now_iso)

    @property
    def warnings_count(self) -> int:
        return sum(1 for detail in self.error_details if detail.get("severity") == "warning")

    @property
    def match_occurrences_count(self) -> int:
        """Number of real match locations, even when category rows are grouped."""

        return sum(max(1, int(result.occurrence_count or 1)) for result in self.results)

    @property
    def display_results_count(self) -> int:
        """Number of rows shown in the results table."""

        return len(self.results)

    @property
    def critical_errors_count(self) -> int:
        detailed_errors = sum(1 for detail in self.error_details if detail.get("severity") == "error")
        legacy_unclassified = sum(1 for detail in self.error_details if not detail.get("severity"))
        if not self.error_details and self.errors:
            legacy_unclassified = len(self.errors)
        return detailed_errors + legacy_unclassified

    @property
    def status(self) -> str:
        if self.critical_errors_count:
            return "completed_with_errors"
        if self.warnings_count:
            return "completed_with_warnings"
        return "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "generated_at_local": self.generated_at_local,
            "generated_at_utc": self.generated_at_utc,
            "request": self.request.to_dict(),
            "results": [result.to_dict() for result in self.results],
            "counters": {
                "analyzed_candidates_count": self.analyzed_candidates_count,
                "matched_candidates_count": self.matched_candidates_count,
                "match_occurrences_count": self.match_occurrences_count,
                "display_results_count": self.display_results_count,
                "no_match_count": self.no_match_count,
                "skipped_by_discard_count": self.skipped_by_discard_count,
                "unsupported_extension_count": self.unsupported_extension_count,
                "issues_count": len(self.errors),
                "warnings_count": self.warnings_count,
                "critical_errors_count": self.critical_errors_count,
                "errors_count": self.critical_errors_count,
            },
            "scan_stats": dict(self.scan_stats),
            "errors": list(self.errors),
            "error_details": [dict(detail) for detail in self.error_details],
        }
