from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from smart_filter.domain.search_config import DEFAULT_CATEGORY_NAME, DEFAULT_SEARCH_SCOPE_OPTION, DEFAULT_FILE_TYPE_OPTION


@dataclass(frozen=True)
class SearchFormState:
    """Estado visual de la búsqueda principal de Smart Filter.

    Este objeto pertenece al producto. GuiCore solo entrega controles visuales;
    Smart Filter decide qué significan modo, categoría, filtro de descarte,
    exclusiones y tipos de archivo.
    """

    mode: str = "Carpeta"
    path: str = ""
    search_text: str = ""
    context_filter: str = ""
    category: str = DEFAULT_CATEGORY_NAME
    discard_filter: str = DEFAULT_CATEGORY_NAME
    temporary_exclusion: str = ""
    search_scope: str = DEFAULT_SEARCH_SCOPE_OPTION
    file_types: list[str] = field(default_factory=lambda: [DEFAULT_FILE_TYPE_OPTION])
    remember_last_location: bool = True
    save_search_history: bool = True
    remember_last_search_settings: bool = True
    source: str = "gui"

    @property
    def has_text(self) -> bool:
        return bool(self.search_text.strip())

    @property
    def has_category(self) -> bool:
        return bool(self.category.strip()) and self.category != DEFAULT_CATEGORY_NAME

    @property
    def has_context_filter(self) -> bool:
        return bool(self.context_filter.strip())

    @property
    def has_path(self) -> bool:
        return bool(self.path.strip())

    @property
    def has_discard_filter(self) -> bool:
        return bool(self.discard_filter.strip()) and self.discard_filter != DEFAULT_CATEGORY_NAME

    @property
    def has_temporary_exclusion(self) -> bool:
        return bool(self.temporary_exclusion.strip())

    @property
    def has_search_criteria(self) -> bool:
        return self.has_text or self.has_category

    @property
    def file_type_summary(self) -> str:
        if not self.file_types:
            return "Sin selección"
        if len(self.file_types) == 1:
            return self.file_types[0]
        return f"{len(self.file_types)} tipos seleccionados"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "path": self.path,
            "search_text": self.search_text,
            "context_filter": self.context_filter,
            "category": self.category,
            "discard_filter": self.discard_filter,
            "temporary_exclusion": self.temporary_exclusion,
            "search_scope": self.search_scope,
            "file_types": list(self.file_types),
            "file_type_summary": self.file_type_summary,
            "remember_last_location": self.remember_last_location,
            "save_search_history": self.save_search_history,
            "remember_last_search_settings": self.remember_last_search_settings,
            "source": self.source,
            "has_path": self.has_path,
            "has_search_criteria": self.has_search_criteria,
        }
