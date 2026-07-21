from __future__ import annotations

import re
import unicodedata
from typing import Iterable

_NON_MATCHING_RE = re.compile(r"[^a-z0-9#+]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: object) -> str:
    """Normalize text for accent-insensitive Smart Filter matching."""
    if value is None:
        return ""

    text = str(value).casefold().strip()
    if not text:
        return ""

    # Most machine-generated TXT/JSON/XML content is ASCII. Avoid the much more
    # expensive Unicode decomposition when it cannot change the result.
    if text.isascii():
        without_accents = text
    else:
        normalized = unicodedata.normalize("NFD", text)
        without_accents = "".join(
            character for character in normalized if unicodedata.category(character) != "Mn"
        )

    normalized_text = _NON_MATCHING_RE.sub(" ", without_accents)
    return _WHITESPACE_RE.sub(" ", normalized_text).strip()


def normalize_terms(terms: Iterable[object] | None) -> list[str]:
    normalized_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in terms or []:
        normalized_term = normalize_text(term)
        if not normalized_term or normalized_term in seen_terms:
            continue
        seen_terms.add(normalized_term)
        normalized_terms.append(normalized_term)
    return normalized_terms


def contains_term(target_text: object, term: object) -> bool:
    normalized_target = normalize_text(target_text)
    normalized_term = normalize_text(term)
    if not normalized_target or not normalized_term:
        return False
    return f" {normalized_term} " in f" {normalized_target} "


def find_terms_in_text(terms: Iterable[object] | None, target_text: object) -> list[str]:
    normalized_target = normalize_text(target_text)
    if not normalized_target:
        return []
    padded_target = f" {normalized_target} "
    found_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in terms or []:
        clean_term = str(term or "").strip()
        normalized_term = normalize_text(clean_term)
        if not normalized_term or normalized_term in seen_terms:
            continue
        if f" {normalized_term} " in padded_target:
            found_terms.append(clean_term)
            seen_terms.add(normalized_term)
    return found_terms


def unique_clean_terms(terms: Iterable[object] | None) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for term in terms or []:
        clean_term = str(term or "").strip()
        normalized_term = normalize_text(clean_term)
        if not clean_term or not normalized_term or normalized_term in seen:
            continue
        seen.add(normalized_term)
        items.append(clean_term)
    return items
