from __future__ import annotations

from smart_filter.domain.search_config import CATEGORY_SEARCH_MODE_TARGET_FIELDS, DEFAULT_SEARCH_SCOPE_OPTION
from smart_filter.domain.search_models import FileCandidate, MatchDecision, SearchRequest
from smart_filter.domain.text_normalizer import contains_term, find_terms_in_text, unique_clean_terms
from smart_filter.engine.category_scope import extract_category_content_scope

SEARCH_SCOPE_NAME_ONLY = "Solo nombre"
SEARCH_SCOPE_CONTENT_ONLY = "Solo contenido"
SEARCH_SCOPE_NAME_AND_CONTENT = DEFAULT_SEARCH_SCOPE_OPTION


def should_search_name(search_scope: str) -> bool:
    return search_scope in {SEARCH_SCOPE_NAME_AND_CONTENT, SEARCH_SCOPE_NAME_ONLY}


def should_search_content(search_scope: str) -> bool:
    return search_scope in {SEARCH_SCOPE_NAME_AND_CONTENT, SEARCH_SCOPE_CONTENT_ONLY}


def build_match_source(found_in_name: bool, found_in_content: bool) -> str:
    if found_in_name and found_in_content:
        return "Nombre y contenido"
    if found_in_name:
        return "Nombre"
    if found_in_content:
        return "Contenido"
    return "Sin coincidencia"


def _find_filter_in_candidate(term: str, candidate: FileCandidate, *, search_name: bool, search_content: bool) -> tuple[bool, bool]:
    found_in_name = search_name and contains_term(candidate.file_name, term)
    found_in_content = search_content and contains_term(candidate.content_text, term)
    return found_in_name, found_in_content


def _find_terms_in_candidate(terms: list[str], candidate: FileCandidate, *, search_name: bool, search_content: bool) -> tuple[list[str], list[str]]:
    matches_in_name = find_terms_in_text(terms, candidate.file_name) if search_name else []
    matches_in_content = find_terms_in_text(terms, candidate.content_text) if search_content else []
    return matches_in_name, matches_in_content


def evaluate_candidate(candidate: FileCandidate, request: SearchRequest) -> MatchDecision:
    """Evaluate one file candidate using Smart Filter product semantics.

    This engine is deliberately independent from GUI and scanning. Step 5 will
    feed it real candidates from FileScanCore; Step 6 will enrich candidates with
    reader-extracted content.
    """
    search_name = should_search_name(request.search_scope)
    search_content = should_search_content(request.search_scope)

    exclusion_matches_name, exclusion_matches_content = _find_terms_in_candidate(
        request.all_exclusion_terms,
        candidate,
        search_name=search_name,
        search_content=search_content,
    )
    exclusion_terms = unique_clean_terms(exclusion_matches_name + exclusion_matches_content)
    if exclusion_terms:
        return MatchDecision(
            matched=False,
            skipped=True,
            skip_reason="discard_filter",
            match_source=build_match_source(bool(exclusion_matches_name), bool(exclusion_matches_content)),
            exclusion_terms=exclusion_terms,
            detail=f"Descartado por exclusión: {', '.join(exclusion_terms)}",
        )

    text_found_in_name = False
    text_found_in_content = False
    matched_terms: list[str] = []
    detail_parts: list[str] = []

    if request.has_text_filter:
        text_found_in_name, text_found_in_content = _find_filter_in_candidate(
            request.search_text,
            candidate,
            search_name=search_name,
            search_content=search_content,
        )
        if text_found_in_name or text_found_in_content:
            matched_terms.append(request.search_text)
            detail_parts.append(f"Texto: {request.search_text}")
        else:
            return MatchDecision(matched=False, detail="No coincide con la palabra/frase indicada.")

    category_matches_name: list[str] = []
    category_matches_content: list[str] = []

    if request.has_category_filter:
        category_scope_enabled = (
            request.category_search_mode == CATEGORY_SEARCH_MODE_TARGET_FIELDS
            and bool(request.category_target_fields)
        )
        if category_scope_enabled:
            scoped_content = extract_category_content_scope(
                candidate.content_text,
                request.category_target_fields,
            ).text
            category_matches_name = []
            category_matches_content = (
                find_terms_in_text(request.category_terms, scoped_content)
                if search_content
                else []
            )
        else:
            category_matches_name, category_matches_content = _find_terms_in_candidate(
                request.category_terms,
                candidate,
                search_name=search_name,
                search_content=search_content,
            )
        category_matches = unique_clean_terms(category_matches_name + category_matches_content)
        if not category_matches:
            return MatchDecision(matched=False, detail="No coincide con la categoría seleccionada.")
        matched_terms.extend(category_matches)
        category_detail = f"Categoría {request.category_name}: {', '.join(category_matches[:8])}"
        if len(category_matches) > 8:
            category_detail += f" +{len(category_matches) - 8}"
        if category_scope_enabled:
            fields = ", ".join(request.category_target_fields[:4])
            if len(request.category_target_fields) > 4:
                fields += f" +{len(request.category_target_fields) - 4}"
            category_detail += f" (campos/secciones: {fields})"
        detail_parts.append(category_detail)

    context_matches_name: list[str] = []
    context_matches_content: list[str] = []
    if request.has_context_filter:
        context_matches_name, context_matches_content = _find_terms_in_candidate(
            request.context_terms,
            candidate,
            search_name=search_name,
            search_content=search_content,
        )
        context_matches = unique_clean_terms(context_matches_name + context_matches_content)
        if not context_matches:
            return MatchDecision(matched=False, detail="No coincide con el contexto requerido.")
        matched_terms.extend(context_matches)
        context_detail = f"Contexto: {', '.join(context_matches[:8])}"
        if len(context_matches) > 8:
            context_detail += f" +{len(context_matches) - 8}"
        detail_parts.append(context_detail)

    if not request.has_text_filter and not request.has_category_filter:
        return MatchDecision(matched=False, detail="La búsqueda no tiene criterio activo.")

    found_in_name = text_found_in_name or bool(category_matches_name) or bool(context_matches_name)
    found_in_content = text_found_in_content or bool(category_matches_content) or bool(context_matches_content)
    return MatchDecision(
        matched=True,
        match_source=build_match_source(found_in_name, found_in_content),
        matched_terms=unique_clean_terms(matched_terms),
        detail=" | ".join(detail_parts),
    )
