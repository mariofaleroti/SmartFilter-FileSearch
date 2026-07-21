from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Callable, Iterable

from smart_filter.domain.search_config import DEFAULT_CATEGORY_NAME, get_extensions_for_file_type
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.domain.search_models import (
    FileCandidate,
    SearchRequest,
    SearchResult,
    SearchSummary,
    count_unique_result_candidates,
)
from smart_filter.engine.candidate_analysis import CandidateAnalyzer
from smart_filter.engine.file_filter_engine import candidate_is_technically_allowed, clean_discard_terms
from smart_filter.engine.match_engine import evaluate_candidate
from smart_filter.domain.text_normalizer import find_terms_in_text, unique_clean_terms
from smart_filter.engine.scan_pipeline import scan_file_candidates
from smart_filter.services.category_service import get_category_rule, get_category_terms
from smart_filter.services.settings_service import get_settings
from smart_filter.domain.discard_filters import extract_saved_discard_term

ProgressCallback = Callable[[int | None, str], None]
CancelRequestedCallback = Callable[[], bool]


def resolve_extensions(file_types: Iterable[str]) -> list[str]:
    extensions: list[str] = []
    seen: set[str] = set()
    for file_type in file_types:
        for extension in get_extensions_for_file_type(file_type):
            normalized = extension.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            extensions.append(normalized)
    return extensions




def _split_context_terms(value: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in str(value or "").replace(";", ",").replace("|", ",").split(","):
        clean = raw.strip()
        lookup = clean.casefold()
        if not clean or lookup in seen:
            continue
        seen.add(lookup)
        terms.append(clean)
    return terms

def _get_discard_terms_from_filter(discard_filter: str, selected_category: str) -> list[str]:
    if not discard_filter or discard_filter == DEFAULT_CATEGORY_NAME:
        return []

    saved_term = extract_saved_discard_term(discard_filter)
    if saved_term:
        return [saved_term]

    if discard_filter != selected_category:
        return get_category_terms(discard_filter)

    return []


def build_search_request(state: SearchFormState) -> SearchRequest:
    category_rule = get_category_rule(state.category)
    settings = get_settings()

    temporary_terms = [state.temporary_exclusion] if state.temporary_exclusion else []
    discard_terms = _get_discard_terms_from_filter(state.discard_filter, state.category)

    # Las categorías pueden traer categorías de descarte asociadas. Se resuelven
    # como términos, pero la gestión visual completa queda para Paso 8.
    linked_discard_terms: list[str] = []
    for discard_category in category_rule.get("discard_categories", []) or []:
        linked_discard_terms.extend(get_category_terms(discard_category))

    ignored_file_terms = []
    raw_ignored_files = str(settings.get("ignored_file_keywords", "") or "")
    if raw_ignored_files:
        ignored_file_terms.extend(part.strip() for part in raw_ignored_files.replace(";", ",").split(",") if part.strip())

    return SearchRequest(
        form_state=state,
        search_text=state.search_text,
        category_name=state.category,
        category_terms=list(category_rule.get("terms", [])),
        context_terms=_split_context_terms(state.context_filter),
        category_exclude_terms=list(category_rule.get("exclude_terms", [])),
        discard_filter_name=state.discard_filter,
        discard_terms=clean_discard_terms(discard_terms, linked_discard_terms, ignored_file_terms),
        temporary_exclusion_terms=clean_discard_terms(temporary_terms),
        search_scope=state.search_scope,
        file_types=list(state.file_types),
        extensions=resolve_extensions(state.file_types),
        category_search_mode=str(category_rule.get("search_mode", "Todo el contenido")),
        category_target_fields=list(category_rule.get("target_fields", [])),
    )


def build_sample_candidates(request: SearchRequest) -> list[FileCandidate]:
    """Deterministic synthetic candidates kept for Step 4 compatibility tests."""
    primary_term = request.search_text or (request.category_terms[0] if request.category_terms else "soporte tecnico")
    category_term = request.category_terms[0] if request.category_terms else primary_term
    exclusion_term = request.all_exclusion_terms[0] if request.all_exclusion_terms else "descartado"
    extension = request.extensions[0] if request.extensions else ".txt"

    return [
        FileCandidate(
            full_path=f"demo/{primary_term.replace(' ', '_')}{extension}",
            file_name=f"{primary_term} - candidato valido {category_term}{extension}",
            extension=extension,
            folder_path="demo",
            content_text=f"Documento de prueba con experiencia en {primary_term}, {category_term} y soporte operativo.",
            source="step4_engine_sample_match",
        ),
        FileCandidate(
            full_path=f"demo/{exclusion_term.replace(' ', '_')}{extension}",
            file_name=f"{primary_term} - {category_term} - {exclusion_term}{extension}",
            extension=extension,
            folder_path="demo",
            content_text=f"Documento que coincide con {primary_term} y {category_term}, pero debe descartarse por {exclusion_term}.",
            source="step4_engine_sample_discard",
        ),
        FileCandidate(
            full_path=f"demo/sin_coincidencia{extension}",
            file_name=f"sin coincidencia{extension}",
            extension=extension,
            folder_path="demo",
            content_text="Contenido neutro para comprobar que el motor no devuelve falsos positivos.",
            source="step4_engine_sample_no_match",
        ),
    ]


def _primary_occurrence_terms(request: SearchRequest) -> list[str]:
    terms: list[str] = []
    if request.has_text_filter:
        terms.append(request.search_text)
    if request.has_category_filter:
        terms.extend(request.category_terms)
    return unique_clean_terms(terms)


def _line_occurrences_for_candidate(candidate: FileCandidate, request: SearchRequest, matched_terms: list[str]) -> list[dict[str, object]]:
    if not candidate.content_text or request.search_scope not in {"Nombre y contenido", "Solo contenido"}:
        return []

    primary_terms = _primary_occurrence_terms(request)
    context_terms = unique_clean_terms(request.context_terms)
    if not primary_terms and not context_terms:
        return []

    occurrences: list[dict[str, object]] = []
    lines = str(candidate.content_text or "").splitlines()
    if not lines and candidate.content_text:
        lines = [candidate.content_text]

    for line_number, line_text in enumerate(lines, start=1):
        primary_found = find_terms_in_text(primary_terms, line_text) if primary_terms else []
        context_found = find_terms_in_text(context_terms, line_text) if context_terms else []
        if primary_terms and not primary_found:
            continue
        if context_terms and not context_found:
            continue

        found_terms = unique_clean_terms(primary_found + context_found)
        if not found_terms:
            continue

        preview = " ".join(str(line_text or "").strip().split())
        if len(preview) > 280:
            preview = f"{preview[:277]}..."

        match_parts: list[str] = []
        if primary_found:
            match_parts.append(f"Coincidencia: {' | '.join(primary_found)}")
        if context_found:
            match_parts.append(f"Contexto: {' | '.join(context_found)}")

        occurrences.append(
            {
                "line_number": line_number,
                "location_label": f"Línea {line_number}",
                "preview_text": preview,
                "matched_terms": found_terms,
                "matches": " · ".join(match_parts) or f"Texto: {' | '.join(found_terms)}",
            }
        )

    return occurrences


def _name_occurrence_for_candidate(candidate: FileCandidate, request: SearchRequest, matched_terms: list[str], detail: str) -> dict[str, object]:
    return {
        "line_number": None,
        "location_label": "Nombre del archivo",
        "preview_text": candidate.file_name,
        "matched_terms": matched_terms,
        "matches": detail,
    }


def _build_result_from_occurrence(
    *,
    index: int,
    candidate: FileCandidate,
    request: SearchRequest,
    match_source: str,
    occurrence: dict[str, object],
    occurrence_number: int | None = None,
) -> SearchResult:
    return SearchResult(
        index=index,
        candidate=candidate,
        match_source=match_source,
        matches=str(occurrence.get("matches") or "Coincidencia"),
        matched_terms=list(occurrence.get("matched_terms") or []),
        category_name=request.category_name,
        discard_filter_name=request.discard_filter_name,
        occurrence_number=occurrence_number,
        line_number=occurrence.get("line_number") if isinstance(occurrence.get("line_number"), int) else None,
        location_label=str(occurrence.get("location_label") or "Archivo"),
        preview_text=str(occurrence.get("preview_text") or ""),
    )


def search_candidates(
    request: SearchRequest,
    candidates: Iterable[FileCandidate],
    *,
    scan_stats: dict[str, object] | None = None,
    scan_errors: Iterable[str] | None = None,
    scan_error_details: Iterable[dict[str, object]] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> SearchSummary:
    """Compatibility path for callers that already provide loaded candidates."""

    analyzer = CandidateAnalyzer(request)
    candidate_list = list(candidates)
    total_candidates = len(candidate_list)
    results: list[SearchResult] = []
    analyzed = no_match = skipped_by_discard = unsupported = 0
    errors: list[str] = list(scan_errors or [])
    error_details: list[dict[str, object]] = [dict(detail) for detail in (scan_error_details or [])]

    if progress_callback:
        progress_callback(65, f"Analizando coincidencias: 0/{total_candidates} candidato(s)")
    progress_interval = max(1, total_candidates // 40) if total_candidates else 1

    for processed_index, candidate in enumerate(candidate_list, start=1):
        try:
            outcome = analyzer.analyze(candidate)
            analyzed += outcome.analyzed_count
            no_match += outcome.no_match_count
            skipped_by_discard += outcome.skipped_by_discard_count
            unsupported += outcome.unsupported_extension_count
            for result in outcome.results:
                results.append(replace(result, index=len(results) + 1))
        except Exception as exc:  # pragma: no cover - defensive GUI boundary.
            errors.append(f"[match_analysis_error] {candidate.full_path}: {exc}")
            error_details.append(
                {
                    "code": "match_analysis_error",
                    "error_type": "match_analysis_error",
                    "path": str(candidate.full_path),
                    "stage": "match_analysis",
                    "message": str(exc),
                    "exception_type": type(exc).__name__,
                    "source": "smart_filter",
                    "severity": "error",
                }
            )
        finally:
            if progress_callback and total_candidates and (
                processed_index == total_candidates or processed_index % progress_interval == 0
            ):
                percent = 65 + int((processed_index / total_candidates) * 30)
                progress_callback(
                    min(95, percent),
                    f"Analizando coincidencias: {processed_index}/{total_candidates} · "
                    f"resultados={len(results)} · descartados={skipped_by_discard}",
                )

    if progress_callback:
        progress_callback(96, f"Preparando tabla: {len(results)} resultado(s) · {len(errors)} incidencia(s)")

    return SearchSummary(
        request=request,
        results=results,
        analyzed_candidates_count=analyzed,
        matched_candidates_count=count_unique_result_candidates(results),
        no_match_count=no_match,
        skipped_by_discard_count=skipped_by_discard,
        unsupported_extension_count=unsupported,
        errors=errors,
        error_details=error_details,
        scan_stats=dict(scan_stats or {}),
    )


def run_search(
    state: SearchFormState,
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_requested: CancelRequestedCallback | None = None,
) -> SearchSummary:
    """Run scan, read and matching as one bounded streaming pipeline."""

    total_started_at = perf_counter()
    if progress_callback:
        progress_callback(2, "Preparando solicitud de búsqueda...")
    request = build_search_request(state)
    if progress_callback:
        progress_callback(5, "Solicitud lista · iniciando escaneo...")

    integrated_started_at = perf_counter()
    scan_result = scan_file_candidates(
        request,
        analyze_during_read=True,
        progress_callback=progress_callback,
        cancel_requested=cancel_requested,
    )
    integrated_elapsed_seconds = perf_counter() - integrated_started_at
    total_elapsed_seconds = perf_counter() - total_started_at

    technical_stats = scan_result.stats.to_dict() if scan_result.stats else {}
    technical_stats.update(
        {
            "execution_pipeline_mode": (
                "integrated_scan_read_process_match"
                if technical_stats.get("analysis_backend") == "spawn_process_pool"
                else "integrated_scan_read_match"
            ),
            "match_analysis_integrated": True,
            "scan_read_match_elapsed_seconds": round(integrated_elapsed_seconds, 6),
            # Compatibility key: it now includes matching performed by workers.
            "scan_and_read_elapsed_seconds": round(integrated_elapsed_seconds, 6),
            "scan_and_read_includes_match_analysis": True,
            "match_analysis_elapsed_seconds": 0.0,
            "match_analysis_separate_pass_eliminated": True,
            "match_analysis_worker_elapsed_seconds_total": round(
                float(technical_stats.get("match_worker_elapsed_seconds_total", 0.0) or 0.0),
                6,
            ),
            "total_search_elapsed_seconds": round(total_elapsed_seconds, 6),
            "analyzed_candidates_per_second": round(
                scan_result.analyzed_candidates_count / integrated_elapsed_seconds,
                3,
            )
            if integrated_elapsed_seconds > 0
            else 0.0,
        }
    )

    summary = SearchSummary(
        request=request,
        results=scan_result.results,
        analyzed_candidates_count=scan_result.analyzed_candidates_count,
        matched_candidates_count=count_unique_result_candidates(scan_result.results),
        no_match_count=scan_result.no_match_count,
        skipped_by_discard_count=scan_result.skipped_by_discard_count,
        unsupported_extension_count=scan_result.unsupported_extension_count,
        errors=scan_result.errors,
        error_details=scan_result.error_details,
        scan_stats=technical_stats,
    )

    if progress_callback:
        progress_callback(
            100,
            f"Búsqueda completa: {summary.match_occurrences_count} resultado(s) en "
            f"{summary.matched_candidates_count} archivo(s) · "
            f"{len(summary.errors)} incidencia(s)",
        )
    return summary


# Compatibility alias for the Step 4 naming used by earlier GUI code/tests.
def run_search_preview(state: SearchFormState) -> SearchSummary:
    return run_search(state)
