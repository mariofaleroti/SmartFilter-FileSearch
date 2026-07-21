from __future__ import annotations

from pathlib import Path
from typing import Iterable

from smart_filter.domain.search_models import FileCandidate, SearchRequest
from smart_filter.domain.text_normalizer import contains_term, unique_clean_terms

TEMPORARY_OFFICE_PREFIXES = ("~$",)


def is_supported_extension(candidate: FileCandidate, request: SearchRequest) -> bool:
    if not request.extensions:
        return True
    return candidate.extension.lower() in {extension.lower() for extension in request.extensions}


def is_temporary_file(candidate: FileCandidate) -> bool:
    return candidate.file_name.startswith(TEMPORARY_OFFICE_PREFIXES)


def keyword_matches_path(path_text: str, keywords: Iterable[str] | None) -> bool:
    for keyword in keywords or []:
        if contains_term(path_text, keyword):
            return True
    return False


def candidate_is_technically_allowed(candidate: FileCandidate, request: SearchRequest) -> tuple[bool, str]:
    if is_temporary_file(candidate):
        return False, "archivo_temporal"
    if not is_supported_extension(candidate, request):
        return False, "extension_no_soportada"
    return True, "ok"


def build_path_candidate(path: str | Path, *, content_text: str = "", source: str = "path_preview") -> FileCandidate:
    return FileCandidate.from_path(path, content_text=content_text, source=source)


def clean_discard_terms(*groups: Iterable[str] | None) -> list[str]:
    merged: list[str] = []
    for group in groups:
        merged.extend(list(group or []))
    return unique_clean_terms(merged)
