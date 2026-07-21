from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from smart_filter.domain.search_config import DEFAULT_TARGET_FIELDS
from smart_filter.domain.text_normalizer import normalize_text

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*(?:[.)])?|[IVXLCDM]+[.)]|[A-Z][.)])\s+",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^\s*[•●▪◦*]\s+")
_EXPLICIT_DELIMITER_RE = re.compile(r"\s*(?P<label>[^:=|\t]{1,100}?)\s*(?P<delimiter>[:=|\t])\s*(?P<value>.*)$")
_DASH_DELIMITER_RE = re.compile(r"\s*(?P<label>.{1,100}?)\s+-\s+(?P<value>.*)$")
_SENTENCE_ENDINGS = ".!?;"

# Límites frecuentes. No son los únicos: el detector también reconoce títulos
# genéricos, Markdown y numeración para cerrar secciones en informes y manuales.
_SECTION_BOUNDARY_FIELDS = {
    "datos personales",
    "contacto",
    "resumen",
    "perfil",
    "perfil laboral",
    "perfil profesional",
    "objetivo",
    "objetivo profesional",
    "experiencia",
    "experiencia laboral",
    "experiencia profesional",
    "formacion",
    "formacion academica",
    "educacion",
    "estudios",
    "habilidades",
    "competencias",
    "conocimientos",
    "idiomas",
    "certificaciones",
    "cursos",
    "referencias",
    "categoria",
    "categorias",
    "area",
    "areas",
    "rubro",
    "sector",
    "introduccion",
    "descripcion",
    "desarrollo",
    "resultados",
    "conclusion",
    "conclusiones",
    "observaciones",
    "incidencias",
    "acciones",
    "recomendaciones",
    "anexos",
}

_COMMON_FIELD_BOUNDARIES = {
    "nombre",
    "apellido",
    "email",
    "correo",
    "telefono",
    "celular",
    "direccion",
    "ciudad",
    "pais",
    "puesto",
    "puesto objetivo",
    "cargo",
    "empresa",
    "fecha",
    "desde",
    "hasta",
    "funciones",
    "tareas",
    "logros",
} | _SECTION_BOUNDARY_FIELDS

_SECTION_LIKE_FIELDS = {
    "resumen",
    "perfil",
    "perfil laboral",
    "perfil profesional",
    "objetivo",
    "objetivo profesional",
    "experiencia",
    "experiencia laboral",
    "experiencia profesional",
    "formacion",
    "formacion academica",
    "educacion",
    "estudios",
    "habilidades",
    "competencias",
    "conocimientos",
    "idiomas",
    "certificaciones",
    "cursos",
    "referencias",
    "introduccion",
    "descripcion",
    "desarrollo",
    "resultados",
    "conclusion",
    "conclusiones",
    "observaciones",
    "incidencias",
    "acciones",
    "recomendaciones",
    "anexos",
}

# Variantes controladas. Se evita la antigua regla de prefijos abiertos, que
# podía interpretar "Experiencia administrativa requerida" como encabezado.
_EQUIVALENT_FIELD_GROUPS = (
    {"experiencia", "experiencia laboral", "experiencia profesional"},
    {"perfil", "perfil laboral", "perfil profesional"},
    {"formacion", "formacion academica", "educacion", "estudios"},
    {"habilidades", "competencias", "conocimientos"},
    {"categoria", "categorias"},
    {"area", "areas", "rubro", "sector"},
    {"conclusion", "conclusiones"},
)
_EQUIVALENT_FIELDS: dict[str, frozenset[str]] = {}
for _group in _EQUIVALENT_FIELD_GROUPS:
    _frozen = frozenset(_group)
    for _name in _group:
        _EQUIVALENT_FIELDS[_name] = _frozen


@dataclass(frozen=True)
class CategoryScopeSegment:
    line_number: int
    text: str
    field_name: str


@dataclass(frozen=True)
class CategoryContentScope:
    text: str = ""
    segments: tuple[CategoryScopeSegment, ...] = ()

    @property
    def found(self) -> bool:
        return bool(self.text.strip())

    def text_for_line(self, line_number: int) -> str:
        return " ".join(
            segment.text
            for segment in self.segments
            if segment.line_number == line_number and segment.text.strip()
        ).strip()

    def preview_for_line(self, line_number: int) -> str:
        for segment in self.segments:
            if segment.line_number == line_number and segment.text.strip():
                return segment.text.strip()
        return ""


@dataclass(frozen=True)
class _FieldDefinition:
    original: str
    normalized: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class _ScopeConfig:
    targets: tuple[_FieldDefinition, ...]
    boundaries: tuple[_FieldDefinition, ...]
    boundary_names: frozenset[str]
    boundary_index: dict[str, tuple[_FieldDefinition, ...]]


@dataclass(frozen=True)
class _ParsedLine:
    original: str
    label: str
    label_normalized: str
    value: str
    explicit: bool
    decoration: str


TokenSpan = tuple[str, int, int]
Marker = tuple[int, int, str, str]


def _token_spans(text: str) -> list[TokenSpan]:
    tokens: list[TokenSpan] = []
    for match in _WORD_RE.finditer(text):
        normalized = normalize_text(match.group(0))
        if normalized:
            tokens.append((normalized, match.start(), match.end()))
    return tokens


def _make_field_definition(value: object) -> _FieldDefinition | None:
    original = str(value or "").strip()
    normalized = normalize_text(original)
    tokens = tuple(part for part in normalized.split() if part)
    if not original or not normalized or not tokens:
        return None
    return _FieldDefinition(original=original, normalized=normalized, tokens=tokens)


def _dedupe_field_definitions(values: Iterable[object]) -> tuple[_FieldDefinition, ...]:
    definitions: list[_FieldDefinition] = []
    seen: set[str] = set()
    for value in values:
        definition = _make_field_definition(value)
        if definition is None or definition.normalized in seen:
            continue
        seen.add(definition.normalized)
        definitions.append(definition)
    return tuple(definitions)


def _build_field_index(
    definitions: tuple[_FieldDefinition, ...],
) -> dict[str, tuple[_FieldDefinition, ...]]:
    grouped: dict[str, list[_FieldDefinition]] = {}
    for definition in definitions:
        grouped.setdefault(definition.tokens[0], []).append(definition)
    return {
        first_token: tuple(sorted(items, key=lambda item: len(item.tokens), reverse=True))
        for first_token, items in grouped.items()
    }


@lru_cache(maxsize=128)
def _compile_scope_config(raw_target_fields: tuple[str, ...]) -> _ScopeConfig:
    targets = _dedupe_field_definitions(raw_target_fields)
    boundaries = _dedupe_field_definitions(
        list(DEFAULT_TARGET_FIELDS)
        + sorted(_COMMON_FIELD_BOUNDARIES)
        + [target.original for target in targets]
    )
    return _ScopeConfig(
        targets=targets,
        boundaries=boundaries,
        boundary_names=frozenset(item.normalized for item in boundaries),
        boundary_index=_build_field_index(boundaries),
    )


def _strip_heading_decoration(value: str) -> tuple[str, str]:
    text = str(value or "").strip()
    decoration = ""
    for name, pattern in (
        ("markdown", _MARKDOWN_HEADING_RE),
        ("numbered", _NUMBERED_HEADING_RE),
        ("bullet", _BULLET_RE),
    ):
        match = pattern.match(text)
        if match:
            decoration = name
            text = text[match.end() :].strip()
            break
    return text, decoration


def _parse_line(value: str) -> _ParsedLine:
    original = str(value or "")
    stripped, decoration = _strip_heading_decoration(original)

    match = _EXPLICIT_DELIMITER_RE.fullmatch(stripped)
    if match:
        label = match.group("label").strip()
        return _ParsedLine(
            original=original,
            label=label,
            label_normalized=normalize_text(label),
            value=match.group("value").strip(),
            explicit=True,
            decoration=decoration,
        )

    dash_match = _DASH_DELIMITER_RE.fullmatch(stripped)
    if dash_match:
        label = dash_match.group("label").strip()
        return _ParsedLine(
            original=original,
            label=label,
            label_normalized=normalize_text(label),
            value=dash_match.group("value").strip(),
            explicit=True,
            decoration=decoration,
        )

    label = stripped.rstrip(":").strip()
    return _ParsedLine(
        original=original,
        label=label,
        label_normalized=normalize_text(label),
        value="",
        explicit=False,
        decoration=decoration,
    )


def _field_names_equivalent(target: str, candidate: str) -> bool:
    if target == candidate:
        return True
    group = _EQUIVALENT_FIELDS.get(target)
    return bool(group and candidate in group)


def _target_for_label(
    label_normalized: str,
    targets: tuple[_FieldDefinition, ...],
) -> _FieldDefinition | None:
    if not label_normalized:
        return None
    for target in targets:
        if _field_names_equivalent(target.normalized, label_normalized):
            return target
    return None


def _is_short_heading_text(value: str) -> bool:
    clean = " ".join(str(value or "").split())
    if not clean or len(clean) > 100:
        return False
    words = clean.split()
    return 1 <= len(words) <= 10


def _letters(value: str) -> str:
    return "".join(character for character in value if character.isalpha())


def _is_probable_heading(
    line: str,
    *,
    previous_blank: bool,
    next_blank: bool,
    config: _ScopeConfig,
) -> bool:
    parsed = _parse_line(line)
    clean = parsed.label.strip()
    if not _is_short_heading_text(clean):
        return False

    # Un campo con valor pertenece normalmente a la sección activa. Solo una
    # etiqueta de sección conocida debe cerrarla en formato "Sección: valor".
    if parsed.explicit and parsed.value:
        return parsed.label_normalized in _SECTION_BOUNDARY_FIELDS

    if parsed.label_normalized in config.boundary_names:
        return True
    if parsed.decoration in {"markdown", "numbered"}:
        return True
    if str(line or "").strip().endswith(":"):
        return True

    letters = _letters(clean)
    if len(letters) >= 2 and letters.isupper():
        return True

    # Un título normal solo se acepta cuando está visualmente aislado. Esto
    # evita convertir frases como "Experiencia administrativa requerida" en
    # una sección por comenzar con mayúscula.
    if previous_blank and next_blank and not clean.endswith(tuple(_SENTENCE_ENDINGS)):
        words = [word.strip("()[]{}.,:;") for word in clean.split()]
        titled = sum(1 for word in words if word[:1].isupper())
        return bool(words) and titled >= max(1, len(words) - 1)
    return False


def _extract_multiline(content: str, config: _ScopeConfig) -> list[CategoryScopeSegment]:
    lines = content.splitlines()
    if not lines:
        return []

    segments: list[CategoryScopeSegment] = []
    active_field: _FieldDefinition | None = None
    active_mode = ""  # section | scalar_pending

    for index, raw_line in enumerate(lines):
        line_number = index + 1
        line = str(raw_line or "")
        stripped = line.strip()
        previous_blank = index == 0 or not str(lines[index - 1] or "").strip()
        next_blank = index + 1 >= len(lines) or not str(lines[index + 1] or "").strip()
        parsed = _parse_line(line)
        matched_target = _target_for_label(parsed.label_normalized, config.targets)

        if matched_target is not None:
            if parsed.explicit and parsed.value:
                segments.append(
                    CategoryScopeSegment(line_number, parsed.value, matched_target.original)
                )
                active_field = None
                active_mode = ""
            else:
                active_field = matched_target
                active_mode = (
                    "section"
                    if (
                        matched_target.normalized in _SECTION_LIKE_FIELDS
                        or parsed.label_normalized in _SECTION_LIKE_FIELDS
                    )
                    else "scalar_pending"
                )
            continue

        if active_field is None:
            continue

        if not stripped:
            continue

        if _is_probable_heading(
            line,
            previous_blank=previous_blank,
            next_blank=next_blank,
            config=config,
        ):
            active_field = None
            active_mode = ""
            continue

        segments.append(CategoryScopeSegment(line_number, stripped, active_field.original))
        if active_mode == "scalar_pending":
            active_field = None
            active_mode = ""

    return segments


def _matches_definition_at(
    tokens: list[TokenSpan],
    token_index: int,
    definition: _FieldDefinition,
) -> bool:
    width = len(definition.tokens)
    if token_index + width > len(tokens):
        return False
    return tuple(item[0] for item in tokens[token_index : token_index + width]) == definition.tokens


def _first_alpha_is_upper(value: str) -> bool:
    for character in value:
        if character.isalpha():
            return character.isupper()
    return False


def _legacy_flat_markers(content: str, config: _ScopeConfig) -> list[Marker]:
    """Recognize old flattened CV-like text only when structure is abundant.

    This compatibility path deliberately requires at least three known labels.
    A normal sentence containing "Experiencia" is therefore never treated as a
    section merely because it starts with that word.
    """

    tokens = _token_spans(content)
    markers: list[Marker] = []
    for token_index, token in enumerate(tokens):
        for definition in config.boundary_index.get(token[0], ()):
            if not _matches_definition_at(tokens, token_index, definition):
                continue
            start = token[1]
            end = tokens[token_index + len(definition.tokens) - 1][2]
            phrase = content[start:end]
            before = content[:start]
            after = content[end:]
            at_start = not normalize_text(before)
            delimited = bool(after.lstrip()[:1] in ":=|\t")
            title_marker = _first_alpha_is_upper(phrase)
            if at_start or delimited or title_marker:
                markers.append((start, end, definition.original, definition.normalized))
                break

    deduped: list[Marker] = []
    occupied: set[int] = set()
    for marker in sorted(markers, key=lambda item: item[0]):
        if marker[0] in occupied:
            continue
        occupied.add(marker[0])
        deduped.append(marker)
    return deduped if len(deduped) >= 3 else []


def _strip_leading_delimiter(value: str) -> str:
    stripped = value.lstrip()
    if stripped[:1] in ":=|\t":
        stripped = stripped[1:].lstrip()
    return stripped.strip()


def _extract_flat(content: str, config: _ScopeConfig) -> list[CategoryScopeSegment]:
    all_markers = _legacy_flat_markers(content, config)
    segments: list[CategoryScopeSegment] = []
    if not all_markers:
        return segments

    for index, marker in enumerate(all_markers):
        _start, end, _marker_original, marker_normalized = marker
        matched_target = _target_for_label(marker_normalized, config.targets)
        if matched_target is None:
            continue

        section_like = (
            marker_normalized in _SECTION_LIKE_FIELDS
            or matched_target.normalized in _SECTION_LIKE_FIELDS
        )
        boundary_end = len(content)
        for following in all_markers[index + 1 :]:
            following_normalized = following[3]
            if section_like and following_normalized not in _SECTION_BOUNDARY_FIELDS:
                continue
            boundary_end = following[0]
            break

        scoped_text = _strip_leading_delimiter(content[end:boundary_end])
        if scoped_text:
            segments.append(CategoryScopeSegment(1, scoped_text, matched_target.original))

    return segments


def extract_category_content_scope(
    content: object,
    target_fields: Iterable[object] | None,
) -> CategoryContentScope:
    """Extract configured fields/sections without guessing from casual words.

    Supported structures:
    - exact standalone headings (including Markdown and numbered headings),
    - explicit label/value lines such as ``Experiencia: soporte técnico``,
    - canonical line-oriented output from structured readers,
    - legacy flattened CV-like text only when several known labels prove that a
      real document structure exists.

    It never falls back to the full document. If no real field or section is
    detected, the returned scope is empty.
    """

    raw_content = str(content or "")
    raw_targets = tuple(str(field or "").strip() for field in (target_fields or ()))
    config = _compile_scope_config(raw_targets)
    if not raw_content.strip() or not config.targets:
        return CategoryContentScope()

    segments = _extract_multiline(raw_content, config)
    if not segments and len(raw_content.splitlines()) <= 1:
        segments = _extract_flat(raw_content, config)

    clean_segments = tuple(segment for segment in segments if normalize_text(segment.text))
    scoped_text = "\n".join(segment.text for segment in clean_segments)
    return CategoryContentScope(text=scoped_text, segments=clean_segments)
