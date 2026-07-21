from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from date_time_core import local_now_iso, utc_now_iso

from smart_filter.domain.search_config import (
    ANALYSIS_MODE_FILE,
    ANALYSIS_MODE_FOLDER,
    ANALYSIS_MODE_OPTIONS,
    DEFAULT_CATEGORY_NAME,
    DEFAULT_FILE_TYPE_OPTION,
    DEFAULT_SEARCH_SCOPE_OPTION,
    get_extensions_for_file_type,
    get_search_file_type_options,
    get_search_scope_options,
)
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.domain.discard_filters import SAVED_DISCARD_PREFIX, extract_saved_discard_term
from smart_filter.services.category_service import (
    get_category_exclude_terms,
    get_category_names,
    get_category_rule,
    get_category_terms,
)
from smart_filter.services.settings_service import add_search_history_entry, get_settings, update_settings_values



def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_mode(value: Any) -> str:
    text = _clean_text(value)
    return text if text in ANALYSIS_MODE_OPTIONS else ANALYSIS_MODE_FOLDER


def normalize_scope(value: Any) -> str:
    text = _clean_text(value)
    return text if text in get_search_scope_options() else DEFAULT_SEARCH_SCOPE_OPTION


def normalize_category(value: Any, *, include_disabled: bool = False) -> str:
    text = _clean_text(value) or DEFAULT_CATEGORY_NAME
    valid = set(get_category_names(include_disabled=include_disabled))
    return text if text in valid else DEFAULT_CATEGORY_NAME


def normalize_file_type_selection(values: Any) -> list[str]:
    options = get_search_file_type_options()
    valid = set(options)

    if isinstance(values, str):
        raw_values = [values]
    elif isinstance(values, (list, tuple, set)):
        raw_values = list(values)
    else:
        raw_values = []

    selected: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = _clean_text(item)
        if text not in valid or text in seen:
            continue
        selected.append(text)
        seen.add(text)

    return selected or [DEFAULT_FILE_TYPE_OPTION]


def build_discard_filter_options(selected_category: Any = DEFAULT_CATEGORY_NAME) -> list[str]:
    settings = get_settings()
    selected = normalize_category(selected_category)
    options = [DEFAULT_CATEGORY_NAME]

    for category_name in get_category_names():
        if category_name == DEFAULT_CATEGORY_NAME or category_name == selected:
            continue
        options.append(category_name)

    for term in settings.get("saved_discard_terms", []) or []:
        clean_term = _clean_text(term)
        if clean_term:
            options.append(f"{SAVED_DISCARD_PREFIX}{clean_term}")

    return options


def normalize_discard_filter(value: Any, selected_category: Any = DEFAULT_CATEGORY_NAME) -> str:
    text = _clean_text(value) or DEFAULT_CATEGORY_NAME
    valid_options = set(build_discard_filter_options(selected_category))
    if text in valid_options:
        return text
    if text.startswith(SAVED_DISCARD_PREFIX):
        return text
    return DEFAULT_CATEGORY_NAME



def build_initial_form_state() -> SearchFormState:
    settings = get_settings()
    remember_last_analysis_mode = bool(settings.get("remember_last_analysis_mode", True))
    remember_last_location = bool(settings.get("remember_last_location", True))
    remember_last_search_settings = bool(settings.get("remember_last_search_settings", True))

    mode = normalize_mode(settings.get("last_analysis_mode")) if remember_last_analysis_mode else ANALYSIS_MODE_FOLDER
    remembered_path = settings.get("last_file") if mode == ANALYSIS_MODE_FILE else settings.get("last_folder")
    path = _clean_text(remembered_path) if remember_last_location else ""

    if remember_last_search_settings:
        search_text = _clean_text(settings.get("last_search_text"))
        context_filter = _clean_text(settings.get("last_context_filter"))
        category = normalize_category(settings.get("last_category"))
        discard_filter = normalize_discard_filter(settings.get("last_discard_filter"), category)
        search_scope = normalize_scope(settings.get("last_search_scope"))
        file_types = normalize_file_type_selection(settings.get("last_file_types") or settings.get("last_file_type"))
    else:
        search_text = ""
        context_filter = ""
        category = DEFAULT_CATEGORY_NAME
        discard_filter = DEFAULT_CATEGORY_NAME
        search_scope = DEFAULT_SEARCH_SCOPE_OPTION
        file_types = normalize_file_type_selection(settings.get("default_file_types") or settings.get("default_file_type"))

    return SearchFormState(
        mode=mode,
        path=path,
        search_text=search_text,
        context_filter=context_filter,
        category=category,
        discard_filter=discard_filter,
        temporary_exclusion="",
        search_scope=search_scope,
        file_types=file_types,
        remember_last_location=remember_last_location,
        save_search_history=bool(settings.get("save_search_history", True)),
        remember_last_search_settings=remember_last_search_settings,
        source="settings",
    )


def coerce_form_state(values: Mapping[str, Any]) -> SearchFormState:
    category = normalize_category(values.get("category"))
    return SearchFormState(
        mode=normalize_mode(values.get("mode")),
        path=_clean_text(values.get("path")),
        search_text=_clean_text(values.get("search_text")),
        context_filter=_clean_text(values.get("context_filter")),
        category=category,
        discard_filter=normalize_discard_filter(values.get("discard_filter"), category),
        temporary_exclusion=_clean_text(values.get("temporary_exclusion")),
        search_scope=normalize_scope(values.get("search_scope")),
        file_types=normalize_file_type_selection(values.get("file_types")),
        remember_last_location=bool(values.get("remember_last_location", True)),
        save_search_history=bool(values.get("save_search_history", True)),
        remember_last_search_settings=bool(values.get("remember_last_search_settings", True)),
        source=_clean_text(values.get("source")) or "gui",
    )


def get_file_type_summary(file_types: list[str]) -> str:
    normalized = normalize_file_type_selection(file_types)
    if len(normalized) == 1:
        return normalized[0]
    return f"{len(normalized)} tipos seleccionados"


def get_extensions_summary(file_types: list[str]) -> str:
    extensions: list[str] = []
    seen: set[str] = set()
    for file_type in normalize_file_type_selection(file_types):
        for extension in get_extensions_for_file_type(file_type):
            if extension not in seen:
                extensions.append(extension)
                seen.add(extension)
    return ", ".join(extensions) if extensions else "Sin extensiones"


def validate_form_state(state: SearchFormState) -> list[str]:
    messages: list[str] = []
    if not state.has_path:
        messages.append("Seleccionar una carpeta o archivo para preparar la búsqueda.")
    if not state.has_search_criteria:
        messages.append("Indicar una palabra/frase o elegir una categoría.")
    if state.mode == ANALYSIS_MODE_FILE and state.path and not Path(state.path).suffix:
        messages.append("El modo archivo individual espera una ruta de archivo.")
    return messages


def persist_recent_form_state(state: SearchFormState) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    if state.remember_last_search_settings:
        updates.update(
            {
                "last_analysis_mode": state.mode,
                "last_search_text": state.search_text,
                "last_context_filter": state.context_filter,
                "last_category": state.category,
                "last_discard_filter": state.discard_filter,
                "last_search_scope": state.search_scope,
                "last_file_type": get_file_type_summary(state.file_types),
                "last_file_types": list(state.file_types),
            }
        )

    if state.remember_last_location:
        if state.mode == ANALYSIS_MODE_FILE:
            updates["last_file"] = state.path
        else:
            updates["last_folder"] = state.path

    settings = update_settings_values(updates) if updates else get_settings()

    if state.save_search_history and state.search_text:
        settings = add_search_history_entry(state.search_text)

    return settings


def build_gui_summary_rows(state: SearchFormState) -> list[dict[str, Any]]:
    category_terms = get_category_terms(state.category) if state.has_category else []
    category_rule = get_category_rule(state.category) if state.has_category else {}
    category_exclude_terms = get_category_exclude_terms(state.category) if state.has_category else []
    saved_discard_term = extract_saved_discard_term(state.discard_filter)

    rows = [
        {
            "index": 1,
            "section": "Origen",
            "field": "Modo",
            "value": state.mode,
            "sharedcode": "GuiCore",
            "next_engine_step": "El selector visual ya entrega modo carpeta/archivo al controlador.",
            "status": "Listo GUI",
        },
        {
            "index": 2,
            "section": "Origen",
            "field": "Ruta",
            "value": state.path or "Sin ruta seleccionada",
            "sharedcode": "GuiCore PathPicker",
            "next_engine_step": "FileScanCore ya recorre esta ruta en el Paso 5.",
            "status": "FileScanCore listo",
        },
        {
            "index": 3,
            "section": "Criterio",
            "field": "Palabra/frase",
            "value": state.search_text or "Sin texto libre",
            "sharedcode": "ConfigCore + DateTimeCore",
            "next_engine_step": "MatchEngine propio aplica coincidencias sobre candidatos reales.",
            "status": "Listo GUI",
        },
        {
            "index": 4,
            "section": "Criterio",
            "field": "Contexto requerido",
            "value": state.context_filter or "Sin contexto adicional",
            "sharedcode": "ConfigCore + MatchEngine",
            "next_engine_step": "Cuando se indica, exige que la coincidencia también contenga ese contexto.",
            "status": "Listo GUI",
        },
        {
            "index": 4,
            "section": "Categoría",
            "field": state.category,
            "value": f"{len(category_terms)} términos" if category_terms else "Sin categoría activa",
            "sharedcode": "CategoryService sobre ConfigCore",
            "next_engine_step": "La lógica semántica sigue siendo propia de Smart Filter.",
            "status": "Datos reales",
        },
        {
            "index": 5,
            "section": "Categoría",
            "field": "Modo categoría",
            "value": category_rule.get("search_mode", "No aplica"),
            "sharedcode": "JsonContractCore",
            "next_engine_step": "El contrato ya conserva modo y campos objetivo.",
            "status": "Datos reales",
        },
        {
            "index": 6,
            "section": "Descarte",
            "field": "Filtro elegido",
            "value": state.discard_filter,
            "sharedcode": "SettingsService + CategoryService",
            "next_engine_step": "FileFilterEngine propio aplica exclusiones sobre candidatos reales.",
            "status": "Listo GUI",
        },
        {
            "index": 7,
            "section": "Descarte",
            "field": "Exclusión temporal",
            "value": saved_discard_term or state.temporary_exclusion or f"{len(category_exclude_terms)} exclusiones de categoría",
            "sharedcode": "ConfigCore",
            "next_engine_step": "Las exclusiones puntuales se mantienen como lógica Smart Filter.",
            "status": "Listo GUI",
        },
        {
            "index": 8,
            "section": "Archivos",
            "field": "Tipos",
            "value": state.file_type_summary,
            "sharedcode": "GuiCore + SearchConfig propio",
            "next_engine_step": f"Extensiones preparadas: {get_extensions_summary(state.file_types)}",
            "status": "Listo GUI",
        },
        {
            "index": 9,
            "section": "Persistencia",
            "field": "Preferencias recientes",
            "value": f"Recordar ruta={state.remember_last_location} · historial={state.save_search_history}",
            "sharedcode": "ConfigCore + DateTimeCore",
            "next_engine_step": f"Estado calculado: {local_now_iso()}",
            "status": "Listo GUI",
        },
    ]
    return rows


def build_result_placeholder_rows(state: SearchFormState) -> list[dict[str, Any]]:
    criteria = state.search_text or (state.category if state.has_category else "Definir palabra/frase o categoría")
    if state.context_filter:
        criteria = f"{criteria} + contexto"

    path_status = "Origen seleccionado" if state.path else "Seleccionar origen"
    action_hint = "Ejecutar búsqueda"
    if not state.search_text and not state.has_category:
        action_hint = "Definir criterio primero"

    return [
        {
            "index": 1,
            "status": "Listo",
            "file_name": "1. Elegir origen",
            "file_type": state.file_type_summary,
            "location": "Panel izquierdo",
            "match": path_status,
            "terms": "Carpeta o archivo",
            "preview": "Preparar ruta de análisis.",
            "category": state.category,
            "reader": "Guía",
            "path": state.path or "-",
        },
        {
            "index": 2,
            "status": "Criterio",
            "file_name": "2. Definir búsqueda",
            "file_type": state.file_type_summary,
            "location": "Buscar en",
            "match": criteria,
            "terms": state.search_scope,
            "preview": "Usar texto, categoría o contexto opcional.",
            "category": state.category,
            "reader": "Guía",
            "path": "-",
        },
        {
            "index": 3,
            "status": "Acción",
            "file_name": "3. Buscar o importar",
            "file_type": "JSON/CSV",
            "location": "Botones / Menú",
            "match": action_hint,
            "terms": "Importar análisis anterior",
            "preview": "Buscar crea resultados nuevos; Importar recupera exportaciones.",
            "category": "-",
            "reader": "Guía",
            "path": "-",
        },
    ]


def build_step3_snapshot() -> dict[str, Any]:
    state = build_initial_form_state()
    return {
        "generated_at_utc": utc_now_iso(),
        "form_state": state.to_dict(),
        "summary_rows": build_gui_summary_rows(state),
        "result_placeholder_rows": build_result_placeholder_rows(state),
        "gui_sections": [
            "Origen",
            "Criterios",
            "Filtros y exclusiones",
            "Tipos de archivo",
            "Acciones",
            "Resumen operativo",
            "Tabla de resultados",
        ],
    }
