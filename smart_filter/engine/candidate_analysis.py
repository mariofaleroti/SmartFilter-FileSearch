from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from smart_filter.domain.search_config import CATEGORY_SEARCH_MODE_TARGET_FIELDS
from smart_filter.domain.search_models import FileCandidate, MatchDecision, SearchRequest, SearchResult
from smart_filter.domain.text_normalizer import normalize_text
from smart_filter.engine.category_scope import CategoryContentScope, extract_category_content_scope
from smart_filter.engine.file_filter_engine import candidate_is_technically_allowed
from smart_filter.engine.match_engine import build_match_source, should_search_content, should_search_name


@dataclass(frozen=True)
class _PreparedTerm:
    original: str
    normalized: str
    needle: str


@dataclass(frozen=True)
class CandidateAnalysisOutcome:
    results: tuple[SearchResult, ...] = ()
    analyzed_count: int = 0
    no_match_count: int = 0
    skipped_by_discard_count: int = 0
    unsupported_extension_count: int = 0


def _prepare_terms(terms: Iterable[object] | None) -> tuple[_PreparedTerm, ...]:
    prepared: list[_PreparedTerm] = []
    seen: set[str] = set()
    for term in terms or ():
        original = str(term or "").strip()
        normalized = normalize_text(original)
        if not original or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        prepared.append(_PreparedTerm(original, normalized, f" {normalized} "))
    return tuple(prepared)


def _find_prepared_terms(terms: tuple[_PreparedTerm, ...], normalized_target: str) -> list[str]:
    if not terms or not normalized_target:
        return []
    padded_target = f" {normalized_target} "
    return [term.original for term in terms if term.needle in padded_target]


def _unique_original_terms(terms: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = str(term or "").strip()
        normalized = normalize_text(clean)
        if not clean or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(clean)
    return result


class CandidateAnalyzer:
    """Compile one request once and evaluate many candidates efficiently.

    Matching rules remain Smart Filter policy. The scanner only supplies files;
    each worker reads, analyzes and then releases the full extracted text.
    """

    def __init__(self, request: SearchRequest) -> None:
        self.request = request
        self.search_name = should_search_name(request.search_scope)
        self.search_content = should_search_content(request.search_scope)
        self.search_terms = _prepare_terms([request.search_text] if request.has_text_filter else [])
        self.category_terms = _prepare_terms(request.category_terms)
        self.context_terms = _prepare_terms(request.context_terms)
        self.exclusion_terms = _prepare_terms(request.all_exclusion_terms)
        self.category_scope_enabled = (
            request.has_category_filter
            and request.category_search_mode == CATEGORY_SEARCH_MODE_TARGET_FIELDS
            and bool(request.category_target_fields)
        )

    def _evaluate(
        self,
        candidate: FileCandidate,
        normalized_name: str,
        normalized_content: str,
        normalized_category_content: str,
    ) -> MatchDecision:
        exclusion_name = _find_prepared_terms(self.exclusion_terms, normalized_name) if self.search_name else []
        exclusion_content = _find_prepared_terms(self.exclusion_terms, normalized_content) if self.search_content else []
        exclusion_matches = _unique_original_terms(exclusion_name + exclusion_content)
        if exclusion_matches:
            return MatchDecision(
                matched=False,
                skipped=True,
                skip_reason="discard_filter",
                match_source=build_match_source(bool(exclusion_name), bool(exclusion_content)),
                exclusion_terms=exclusion_matches,
                detail=f"Descartado por exclusión: {', '.join(exclusion_matches)}",
            )

        matched_terms: list[str] = []
        detail_parts: list[str] = []
        text_name: list[str] = []
        text_content: list[str] = []

        if self.request.has_text_filter:
            text_name = _find_prepared_terms(self.search_terms, normalized_name) if self.search_name else []
            text_content = _find_prepared_terms(self.search_terms, normalized_content) if self.search_content else []
            if not text_name and not text_content:
                return MatchDecision(matched=False, detail="No coincide con la palabra/frase indicada.")
            matched_terms.append(self.request.search_text)
            detail_parts.append(f"Texto: {self.request.search_text}")

        category_name: list[str] = []
        category_content: list[str] = []
        if self.request.has_category_filter:
            category_name = (
                _find_prepared_terms(self.category_terms, normalized_name)
                if self.search_name and not self.category_scope_enabled
                else []
            )
            category_content = (
                _find_prepared_terms(self.category_terms, normalized_category_content)
                if self.search_content
                else []
            )
            category_matches = _unique_original_terms(category_name + category_content)
            if not category_matches:
                return MatchDecision(matched=False, detail="No coincide con la categoría seleccionada.")
            matched_terms.extend(category_matches)
            category_detail = f"Categoría {self.request.category_name}: {', '.join(category_matches[:8])}"
            if len(category_matches) > 8:
                category_detail += f" +{len(category_matches) - 8}"
            if self.category_scope_enabled:
                fields = ", ".join(self.request.category_target_fields[:4])
                if len(self.request.category_target_fields) > 4:
                    fields += f" +{len(self.request.category_target_fields) - 4}"
                category_detail += f" (campos/secciones: {fields})"
            detail_parts.append(category_detail)

        context_name: list[str] = []
        context_content: list[str] = []
        if self.request.has_context_filter:
            context_name = _find_prepared_terms(self.context_terms, normalized_name) if self.search_name else []
            context_content = _find_prepared_terms(self.context_terms, normalized_content) if self.search_content else []
            context_matches = _unique_original_terms(context_name + context_content)
            if not context_matches:
                return MatchDecision(matched=False, detail="No coincide con el contexto requerido.")
            matched_terms.extend(context_matches)
            context_detail = f"Contexto: {', '.join(context_matches[:8])}"
            if len(context_matches) > 8:
                context_detail += f" +{len(context_matches) - 8}"
            detail_parts.append(context_detail)

        if not self.request.has_text_filter and not self.request.has_category_filter:
            return MatchDecision(matched=False, detail="La búsqueda no tiene criterio activo.")

        found_name = bool(text_name or category_name or context_name)
        found_content = bool(text_content or category_content or context_content)
        return MatchDecision(
            matched=True,
            match_source=build_match_source(found_name, found_content),
            matched_terms=_unique_original_terms(matched_terms),
            detail=" | ".join(detail_parts),
        )

    def _content_occurrences(
        self,
        candidate: FileCandidate,
        category_scope: CategoryContentScope,
    ) -> list[dict[str, object]]:
        if not candidate.content_text or not self.search_content:
            return []
        if not self.search_terms and not self.category_terms and not self.context_terms:
            return []

        lines = str(candidate.content_text or "").splitlines()
        if not lines and candidate.content_text:
            lines = [candidate.content_text]

        occurrences: list[dict[str, object]] = []
        for line_number, line_text in enumerate(lines, start=1):
            normalized_line = normalize_text(line_text)
            text_found = _find_prepared_terms(self.search_terms, normalized_line)

            category_target = (
                category_scope.text_for_line(line_number)
                if self.category_scope_enabled
                else line_text
            )
            category_found = _find_prepared_terms(
                self.category_terms,
                normalize_text(category_target),
            )
            context_found = _find_prepared_terms(self.context_terms, normalized_line)

            primary_found = _unique_original_terms(text_found + category_found)
            if (self.search_terms or self.category_terms) and not primary_found:
                continue
            if self.context_terms and not context_found:
                continue

            found_terms = _unique_original_terms(primary_found + context_found)
            if not found_terms:
                continue

            preview_source = line_text
            if self.category_scope_enabled and category_found and not text_found:
                preview_source = category_scope.preview_for_line(line_number) or line_text
            preview = " ".join(str(preview_source or "").strip().split())
            if len(preview) > 280:
                preview = f"{preview[:277]}..."

            match_parts: list[str] = []
            if text_found:
                match_parts.append(f"Texto: {' | '.join(text_found)}")
            if category_found:
                match_parts.append(f"Coincidencia: {' | '.join(category_found)}")
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

    def analyze(self, candidate: FileCandidate) -> CandidateAnalysisOutcome:
        allowed, reason = candidate_is_technically_allowed(candidate, self.request)
        if not allowed:
            return CandidateAnalysisOutcome(
                unsupported_extension_count=1 if reason == "extension_no_soportada" else 0,
            )

        normalized_name = normalize_text(candidate.file_name) if self.search_name else ""
        normalized_content = normalize_text(candidate.content_text) if self.search_content else ""
        category_scope = (
            extract_category_content_scope(candidate.content_text, self.request.category_target_fields)
            if self.category_scope_enabled and self.search_content
            else CategoryContentScope()
        )
        normalized_category_content = (
            normalize_text(category_scope.text)
            if self.category_scope_enabled
            else normalized_content
        )
        decision = self._evaluate(
            candidate,
            normalized_name,
            normalized_content,
            normalized_category_content,
        )
        if decision.skipped:
            return CandidateAnalysisOutcome(analyzed_count=1, skipped_by_discard_count=1)
        if not decision.matched:
            return CandidateAnalysisOutcome(analyzed_count=1, no_match_count=1)

        occurrences = self._content_occurrences(candidate, category_scope)
        if not occurrences and "Nombre" in decision.match_source:
            occurrences = [
                {
                    "line_number": None,
                    "location_label": "Nombre del archivo",
                    "preview_text": candidate.file_name,
                    "matched_terms": decision.matched_terms,
                    "matches": decision.detail,
                }
            ]
        if not occurrences:
            scoped_preview = category_scope.segments[0].text[:240] if category_scope.segments else ""
            occurrences = [
                {
                    "line_number": category_scope.segments[0].line_number if category_scope.segments else None,
                    "location_label": (
                        f"Línea {category_scope.segments[0].line_number}"
                        if category_scope.segments
                        else "Archivo"
                    ),
                    "preview_text": scoped_preview or (candidate.content_text[:240] if candidate.content_text else candidate.file_name),
                    "matched_terms": decision.matched_terms,
                    "matches": decision.detail,
                }
            ]

        compact_candidate = replace(candidate, content_text="")
        prepared_locations: list[dict[str, object]] = []
        for occurrence_number, occurrence in enumerate(occurrences, start=1):
            prepared_locations.append(
                {
                    "occurrence_number": occurrence_number,
                    "line_number": occurrence.get("line_number") if isinstance(occurrence.get("line_number"), int) else None,
                    "row_number": occurrence.get("row_number") if isinstance(occurrence.get("row_number"), int) else None,
                    "sheet_name": str(occurrence.get("sheet_name") or ""),
                    "location_label": str(occurrence.get("location_label") or "Archivo"),
                    "preview_text": str(occurrence.get("preview_text") or ""),
                    "matched_terms": list(occurrence.get("matched_terms") or []),
                    "matches": str(occurrence.get("matches") or "Coincidencia"),
                }
            )

        # When the category is the only primary criterion, the product question is
        # "which files belong to this theme?". Keep every location for the detail
        # and highlighted viewer, but show one clean table row per file.
        group_category_result = self.request.has_category_filter and not self.request.has_text_filter
        if group_category_result:
            all_terms = _unique_original_terms(
                list(decision.matched_terms)
                + [
                    term
                    for location in prepared_locations
                    for term in list(location.get("matched_terms") or [])
                ]
            )
            first = prepared_locations[0]
            occurrence_count = max(1, len(prepared_locations))
            first_location = str(first.get("location_label") or "Archivo")
            location_label = (
                f"{occurrence_count} ocurrencias · desde {first_location}"
                if occurrence_count > 1
                else first_location
            )
            matches = f"Coincidencia: {' | '.join(all_terms)}" if all_terms else decision.detail
            return CandidateAnalysisOutcome(
                results=(
                    SearchResult(
                        index=0,
                        candidate=compact_candidate,
                        match_source=decision.match_source,
                        matches=matches,
                        matched_terms=all_terms,
                        category_name=self.request.category_name,
                        discard_filter_name=self.request.discard_filter_name,
                        occurrence_number=None,
                        line_number=first.get("line_number") if isinstance(first.get("line_number"), int) else None,
                        row_number=first.get("row_number") if isinstance(first.get("row_number"), int) else None,
                        sheet_name=str(first.get("sheet_name") or ""),
                        location_label=location_label,
                        preview_text=str(first.get("preview_text") or ""),
                        occurrence_count=occurrence_count,
                        match_locations=[dict(item) for item in prepared_locations],
                        grouped_by_file=True,
                    ),
                ),
                analyzed_count=1,
            )

        results: list[SearchResult] = []
        for location in prepared_locations:
            results.append(
                SearchResult(
                    index=0,
                    candidate=compact_candidate,
                    match_source=decision.match_source,
                    matches=str(location.get("matches") or "Coincidencia"),
                    matched_terms=list(location.get("matched_terms") or []),
                    category_name=self.request.category_name,
                    discard_filter_name=self.request.discard_filter_name,
                    occurrence_number=int(location.get("occurrence_number") or 1),
                    line_number=location.get("line_number") if isinstance(location.get("line_number"), int) else None,
                    row_number=location.get("row_number") if isinstance(location.get("row_number"), int) else None,
                    sheet_name=str(location.get("sheet_name") or ""),
                    location_label=str(location.get("location_label") or "Archivo"),
                    preview_text=str(location.get("preview_text") or ""),
                    occurrence_count=1,
                    match_locations=[dict(location)],
                    grouped_by_file=False,
                )
            )
        return CandidateAnalysisOutcome(results=tuple(results), analyzed_count=1)
