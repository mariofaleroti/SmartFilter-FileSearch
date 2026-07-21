from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from config_core import load_config, write_json_file
from date_time_core import create_timestamp_pair, utc_now_iso
from gui_core import GuiPreferences
from json_contract_core import create_contract

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.factory_defaults import load_factory_contract_data
from smart_filter.domain.search_config import (
    ALL_FILE_TYPE_OPTION,
    ANALYSIS_MODE_FILE,
    ANALYSIS_MODE_FOLDER,
    ANALYSIS_MODE_OPTIONS,
    APP_FONT_FAMILY_OPTIONS,
    APP_FONT_SIZE_OPTIONS,
    DEFAULT_CATEGORY_NAME,
    DEFAULT_FILE_TYPE_OPTION,
    DEFAULT_SEARCH_SCOPE_OPTION,
    HIGHLIGHT_CELL_COLOR_OPTIONS,
    HIGHLIGHT_CELL_COLOR_PALETTES,
    HIGHLIGHT_TEXT_COLOR_HEX,
    HIGHLIGHT_TEXT_COLOR_OPTIONS,
    MAX_CONTENT_FILE_SIZE_BYTES,
    MAX_CONTENT_FILE_SIZE_OPTIONS,
    OPEN_RESULT_MODE_OPTIONS,
    RESULTS_DENSITY_OPTIONS,
    SEARCH_FILE_TYPE_OPTIONS,
    SEARCH_SCOPE_OPTIONS,
    get_all_supported_extensions,
    get_individual_search_file_type_options,
    get_search_file_type_options,
)
from smart_filter.domain.scan_exclusions import (
    BROAD_SCAN_DEFAULTS,
    BROAD_SCAN_ENABLED_KEY,
    BROAD_SCAN_OPTIONS,
)
from smart_filter.engine.resource_policy import (
    DEFAULT_MANUAL_ANALYSIS_PROCESSES,
    DEFAULT_MANUAL_MAX_PENDING_BATCHES,
    DEFAULT_MANUAL_READER_WORKERS,
    DEFAULT_MANUAL_RESERVED_CORES,
    DEFAULT_PERFORMANCE_MONITOR_ENABLED,
    DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS,
    DEFAULT_PERFORMANCE_TIMELINE_ENABLED,
    DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS,
    DEFAULT_PROCESSING_MODE,
    DEFAULT_RESOURCE_PROFILE,
    PROCESSING_MODE_OPTIONS,
    RESOURCE_PROFILE_OPTIONS,
)
from smart_filter.paths import FACTORY_SETTINGS_PATH, SETTINGS_PATH, ensure_project_directories

DEFAULT_THEME_OPTION = "Oscuro"
DISABLED_SURFACE_THEME_VALUES = {"bosque", "forest", "verde", "green"}
DEFAULT_ALLOWED_SURFACE_THEME = "onyx"
DEFAULT_OUTPUT_FOLDER_PREFIX = "SmartFilter_Resultados"
DEFAULT_MAX_CONTENT_FILE_SIZE_OPTION = "Sin límite"
DEFAULT_HIGHLIGHT_SEARCH_TERMS_ON_OPEN = True
DEFAULT_HIGHLIGHT_CELL_COLOR_OPTION = "Amarillo"
DEFAULT_HIGHLIGHT_TEXT_COLOR_OPTION = "Rojo"
DEFAULT_OPEN_RESULT_MODE_OPTION = "Abrir vista destacada HTML"
DEFAULT_RESULTS_DENSITY_OPTION = "Normal"
DEFAULT_APP_FONT_FAMILY_OPTION = "Segoe UI"
DEFAULT_APP_FONT_SIZE_OPTION = "Normal"
DEFAULT_METRICS_SHOW_BEFORE_SEARCH = False
DEFAULT_METRICS_SIZE_OPTION = "Compacto"
DEFAULT_METRICS_STYLE_OPTION = "Estado"
DEFAULT_CUSTOM_ACCENT_ENABLED = False
DEFAULT_CUSTOM_ACCENT_HEX = "#1f6aa5"
DEFAULT_CUSTOM_SURFACE_ENABLED = False
DEFAULT_CUSTOM_SURFACE_HEX = "#1b2430"
CUSTOM_ACCENT_ALLOWED_HEX = {
    "#1f6aa5",
    "#0891b2",
    "#4f46e5",
    "#7c3aed",
    "#c026d3",
    "#dc2626",
    "#ea580c",
    "#d97706",
}
METRICS_SIZE_OPTIONS = ["Compacto", "Normal", "Grande"]
METRICS_STYLE_OPTIONS = ["Neutro", "Color principal", "Estado"]
DEFAULT_REMEMBER_LAST_USE = True
DEFAULT_SAVE_SEARCH_HISTORY = False
DEFAULT_REMEMBER_LAST_ANALYSIS_MODE = True
DEFAULT_REMEMBER_LAST_LOCATION = False
DEFAULT_REMEMBER_LAST_SEARCH_SETTINGS = False
MAX_SEARCH_HISTORY_ITEMS = 12
MAX_SAVED_DISCARD_TERMS = 100

THEME_OPTIONS = ["Oscuro", "Claro", "Sistema"]

_THEME_TO_GUI_APPEARANCE = {
    "Oscuro": "dark",
    "Claro": "light",
    "Sistema": "system",
    "dark": "dark",
    "light": "light",
    "system": "system",
}

_GUI_APPEARANCE_TO_THEME = {
    "dark": "Oscuro",
    "light": "Claro",
    "system": "Sistema",
}


def _normalize_open_result_mode(value: object) -> str:
    """Migrate historical highlighted-copy labels to the HTML viewer mode."""

    clean = str(value or "").strip()
    aliases = {
        "Abrir copia destacada": "Abrir vista destacada HTML",
        "Abrir destacado": "Abrir vista destacada HTML",
        "Vista destacada": "Abrir vista destacada HTML",
    }
    return aliases.get(clean, clean)


def _new_runtime(source: str = "Smart Filter factory defaults") -> dict[str, Any]:
    updated_at_utc, updated_at_local = create_timestamp_pair()
    return {
        "created_at_utc": updated_at_utc,
        "updated_at_utc": updated_at_utc,
        "updated_at_local": updated_at_local,
        "source": source,
    }


def build_default_settings_data() -> dict[str, Any]:
    visual_preferences = GuiPreferences(
        appearance_mode="dark",
        color_theme="blue",
        surface_theme="onyx",
        font_family=DEFAULT_APP_FONT_FAMILY_OPTION,
        font_size=DEFAULT_APP_FONT_SIZE_OPTION,
        table_density=DEFAULT_RESULTS_DENSITY_OPTION,
    ).to_dict()
    visual_preferences.update(
        {
            "custom_accent_enabled": DEFAULT_CUSTOM_ACCENT_ENABLED,
            "custom_accent_hex": DEFAULT_CUSTOM_ACCENT_HEX,
            "custom_surface_enabled": DEFAULT_CUSTOM_SURFACE_ENABLED,
            "custom_surface_hex": DEFAULT_CUSTOM_SURFACE_HEX,
        }
    )

    return {
        "visual": visual_preferences,
        "metrics": {
            "show_before_search": DEFAULT_METRICS_SHOW_BEFORE_SEARCH,
            "size": DEFAULT_METRICS_SIZE_OPTION,
            "style": DEFAULT_METRICS_STYLE_OPTION,
        },
        "search": {
            "default_analysis_mode": ANALYSIS_MODE_FOLDER,
            "default_file_type": DEFAULT_FILE_TYPE_OPTION,
            "default_file_types": [DEFAULT_FILE_TYPE_OPTION],
            "default_search_scope": DEFAULT_SEARCH_SCOPE_OPTION,
            "default_category": DEFAULT_CATEGORY_NAME,
            "max_content_file_size": DEFAULT_MAX_CONTENT_FILE_SIZE_OPTION,
            "supported_file_types": get_search_file_type_options(),
            "supported_extensions": get_all_supported_extensions(),
        },
        "performance": {
            "processing_mode": DEFAULT_PROCESSING_MODE,
            "resource_profile": DEFAULT_RESOURCE_PROFILE,
            "manual_analysis_processes": DEFAULT_MANUAL_ANALYSIS_PROCESSES,
            "manual_reader_workers": DEFAULT_MANUAL_READER_WORKERS,
            "manual_reserved_cores": DEFAULT_MANUAL_RESERVED_CORES,
            "manual_max_pending_batches": DEFAULT_MANUAL_MAX_PENDING_BATCHES,
            "performance_monitor_enabled": DEFAULT_PERFORMANCE_MONITOR_ENABLED,
            "performance_timeline_enabled": DEFAULT_PERFORMANCE_TIMELINE_ENABLED,
            "performance_sample_interval_seconds": DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS,
            "performance_timeline_interval_seconds": DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS,
        },
        "output": {
            "auto_open_output_folder": True,
            "output_folder_prefix": DEFAULT_OUTPUT_FOLDER_PREFIX,
            "create_csv_report_on_save": True,
            "preserve_folder_structure_on_save": False,
        },
        "highlight": {
            "highlight_search_terms_on_open": DEFAULT_HIGHLIGHT_SEARCH_TERMS_ON_OPEN,
            "highlight_cell_color": DEFAULT_HIGHLIGHT_CELL_COLOR_OPTION,
            "highlight_text_color": DEFAULT_HIGHLIGHT_TEXT_COLOR_OPTION,
            "open_result_mode": DEFAULT_OPEN_RESULT_MODE_OPTION,
        },
        "experience": {
            "remember_last_use": DEFAULT_REMEMBER_LAST_USE,
            "save_search_history": DEFAULT_SAVE_SEARCH_HISTORY,
            "remember_last_analysis_mode": DEFAULT_REMEMBER_LAST_ANALYSIS_MODE,
            "remember_last_location": DEFAULT_REMEMBER_LAST_LOCATION,
            "remember_last_search_settings": DEFAULT_REMEMBER_LAST_SEARCH_SETTINGS,
        },
        "state": {
            "last_analysis_mode": ANALYSIS_MODE_FOLDER,
            "last_folder": "",
            "last_file": "",
            "last_search_text": "",
            "last_context_filter": "",
            "last_category": DEFAULT_CATEGORY_NAME,
            "last_discard_filter": DEFAULT_CATEGORY_NAME,
            "last_file_type": DEFAULT_FILE_TYPE_OPTION,
            "last_file_types": [DEFAULT_FILE_TYPE_OPTION],
            "last_search_scope": DEFAULT_SEARCH_SCOPE_OPTION,
        },
        "filters": {
            "ignored_folder_keywords": "",
            "ignored_file_keywords": "",
            "ignored_folder_paths": [],
            "ignored_file_paths": [],
            "saved_discard_terms": [],
            **BROAD_SCAN_DEFAULTS,
        },
        "history": {
            "search_history": [],
        },
        "runtime": _new_runtime(),
    }


def _clone_compiled_defaults() -> dict[str, Any]:
    return deepcopy(build_default_settings_data())


def _clone_defaults() -> dict[str, Any]:
    return load_factory_contract_data(
        FACTORY_SETTINGS_PATH,
        expected_config_type="smartfilter_settings",
        fallback_data=_clone_compiled_defaults(),
    )


def get_default_settings() -> dict[str, Any]:
    """Return the flat settings view kept for Smart Filter product code."""
    return to_flat_settings(_clone_defaults())


def get_default_settings_data() -> dict[str, Any]:
    """Return the canonical nested settings data stored in the JSON contract."""
    return sanitize_settings_data(_clone_defaults())


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        clean = value.strip().casefold()
        if clean in {"true", "1", "yes", "si", "sí", "y"}:
            return True
        if clean in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def sanitize_text_setting(value: Any) -> str:
    return str(value or "").strip()


def _coerce_int_range(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def sanitize_hex_color(value: Any, default: str = DEFAULT_CUSTOM_ACCENT_HEX) -> str:
    clean = sanitize_text_setting(value).lstrip("#")
    if len(clean) == 3 and all(character in "0123456789abcdefABCDEF" for character in clean):
        clean = "".join(character * 2 for character in clean)
    if len(clean) == 6 and all(character in "0123456789abcdefABCDEF" for character in clean):
        return f"#{clean.lower()}"
    return default


def sanitize_custom_accent_hex(value: Any) -> str:
    # El modo avanzado permite cualquier color HEX válido elegido desde el selector nativo.
    # La lista histórica de colores fijos queda solo como referencia/fallback, no como restricción.
    return sanitize_hex_color(value, DEFAULT_CUSTOM_ACCENT_HEX)


def sanitize_output_folder_prefix(output_folder_prefix: Any) -> str:
    clean_prefix = sanitize_text_setting(output_folder_prefix)
    invalid_characters = '<>:"/\\|?*'

    for character in invalid_characters:
        clean_prefix = clean_prefix.replace(character, "_")

    return clean_prefix or DEFAULT_OUTPUT_FOLDER_PREFIX


def sanitize_search_history(search_history: Any) -> list[str]:
    if not isinstance(search_history, list):
        return []

    clean_history: list[str] = []
    seen_items: set[str] = set()

    for item in search_history:
        clean_item = sanitize_text_setting(item)
        lookup_key = clean_item.casefold()

        if not clean_item or lookup_key in seen_items:
            continue

        clean_history.append(clean_item)
        seen_items.add(lookup_key)

        if len(clean_history) >= MAX_SEARCH_HISTORY_ITEMS:
            break

    return clean_history


def sanitize_saved_discard_terms(saved_discard_terms: Any) -> list[str]:
    if isinstance(saved_discard_terms, str):
        raw_items = [saved_discard_terms]
    elif isinstance(saved_discard_terms, list):
        raw_items = saved_discard_terms
    else:
        raw_items = []

    clean_terms: list[str] = []
    seen_items: set[str] = set()

    for item in raw_items:
        clean_item = sanitize_text_setting(item)
        lookup_key = clean_item.casefold()

        if not clean_item or lookup_key in seen_items:
            continue

        clean_terms.append(clean_item)
        seen_items.add(lookup_key)

        if len(clean_terms) >= MAX_SAVED_DISCARD_TERMS:
            break

    return clean_terms


def sanitize_path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(";", "\n").replace(",", "\n").splitlines()
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []

    clean_paths: list[str] = []
    seen_items: set[str] = set()
    for item in raw_items:
        clean_item = sanitize_text_setting(item)
        lookup = clean_item.casefold()
        if not clean_item or lookup in seen_items:
            continue
        clean_paths.append(clean_item)
        seen_items.add(lookup)
    return clean_paths


def sanitize_file_type_selection(file_types: Any, fallback: list[str] | None = None) -> list[str]:
    valid_file_types = get_search_file_type_options()
    individual_file_types = get_individual_search_file_type_options()

    if fallback is None:
        fallback = [DEFAULT_FILE_TYPE_OPTION]

    if isinstance(file_types, str):
        raw_items = [file_types]
    elif isinstance(file_types, list):
        raw_items = file_types
    else:
        raw_items = fallback

    clean_items: list[str] = []
    seen_items: set[str] = set()

    for item in raw_items:
        clean_item = sanitize_text_setting(item)

        if clean_item not in valid_file_types:
            continue

        if clean_item == ALL_FILE_TYPE_OPTION:
            return [ALL_FILE_TYPE_OPTION]

        if clean_item in seen_items:
            continue

        clean_items.append(clean_item)
        seen_items.add(clean_item)

    if not clean_items:
        return sanitize_file_type_selection(fallback, [DEFAULT_FILE_TYPE_OPTION])

    if set(clean_items) == set(individual_file_types):
        return [ALL_FILE_TYPE_OPTION]

    return clean_items


def _sanitize_visual(visual: Mapping[str, Any] | None) -> dict[str, Any]:
    values = dict(visual or {})
    if "theme" in values and "appearance_mode" not in values:
        values["appearance_mode"] = _THEME_TO_GUI_APPEARANCE.get(str(values.get("theme")), "dark")
    if str(values.get("surface_theme") or "").strip().casefold() in DISABLED_SURFACE_THEME_VALUES:
        values["surface_theme"] = DEFAULT_ALLOWED_SURFACE_THEME

    custom_accent_enabled = _coerce_bool(values.get("custom_accent_enabled"), DEFAULT_CUSTOM_ACCENT_ENABLED)
    custom_accent_hex = sanitize_custom_accent_hex(values.get("custom_accent_hex"))

    preferences = GuiPreferences.from_mapping(values).to_dict()
    if str(preferences.get("surface_theme") or "").strip().casefold() in DISABLED_SURFACE_THEME_VALUES:
        preferences["surface_theme"] = DEFAULT_ALLOWED_SURFACE_THEME
    custom_surface_enabled = _coerce_bool(values.get("custom_surface_enabled"), DEFAULT_CUSTOM_SURFACE_ENABLED)
    custom_surface_hex = sanitize_hex_color(values.get("custom_surface_hex"), DEFAULT_CUSTOM_SURFACE_HEX)
    preferences["custom_accent_enabled"] = custom_accent_enabled
    preferences["custom_accent_hex"] = custom_accent_hex
    preferences["custom_surface_enabled"] = custom_surface_enabled
    preferences["custom_surface_hex"] = custom_surface_hex
    return preferences


def _select_allowed(value: Any, allowed: list[str], default: str) -> str:
    clean = sanitize_text_setting(value)
    return clean if clean in allowed else default


def sanitize_settings_data(settings_data: Mapping[str, Any] | None) -> dict[str, Any]:
    base = _clone_defaults()
    source = dict(settings_data or {})

    if source:
        for section_name in ("visual", "metrics", "search", "performance", "output", "highlight", "experience", "state", "filters", "history", "runtime"):
            if isinstance(source.get(section_name), Mapping):
                base[section_name].update(dict(source[section_name]))

    base["visual"] = _sanitize_visual(base.get("visual"))

    metrics = base["metrics"]
    metrics["show_before_search"] = _coerce_bool(metrics.get("show_before_search"), DEFAULT_METRICS_SHOW_BEFORE_SEARCH)
    metrics["size"] = _select_allowed(metrics.get("size"), METRICS_SIZE_OPTIONS, DEFAULT_METRICS_SIZE_OPTION)
    if str(metrics.get("style") or "").strip().casefold() == "acento":
        metrics["style"] = "Color principal"
    metrics["style"] = _select_allowed(metrics.get("style"), METRICS_STYLE_OPTIONS, DEFAULT_METRICS_STYLE_OPTION)

    search = base["search"]
    search["default_analysis_mode"] = _select_allowed(
        search.get("default_analysis_mode"), ANALYSIS_MODE_OPTIONS, ANALYSIS_MODE_FOLDER
    )
    search["default_file_types"] = sanitize_file_type_selection(search.get("default_file_types"))
    search["default_file_type"] = search["default_file_types"][0]
    search["default_search_scope"] = _select_allowed(
        search.get("default_search_scope"), SEARCH_SCOPE_OPTIONS, DEFAULT_SEARCH_SCOPE_OPTION
    )
    search["default_category"] = sanitize_text_setting(search.get("default_category")) or DEFAULT_CATEGORY_NAME
    search["max_content_file_size"] = _select_allowed(
        search.get("max_content_file_size"), MAX_CONTENT_FILE_SIZE_OPTIONS, DEFAULT_MAX_CONTENT_FILE_SIZE_OPTION
    )
    search["supported_file_types"] = get_search_file_type_options()
    search["supported_extensions"] = get_all_supported_extensions()

    performance = base["performance"]
    performance["processing_mode"] = _select_allowed(
        performance.get("processing_mode"), PROCESSING_MODE_OPTIONS, DEFAULT_PROCESSING_MODE
    )
    performance["resource_profile"] = _select_allowed(
        performance.get("resource_profile"), RESOURCE_PROFILE_OPTIONS, DEFAULT_RESOURCE_PROFILE
    )
    performance["manual_analysis_processes"] = _coerce_int_range(
        performance.get("manual_analysis_processes"), DEFAULT_MANUAL_ANALYSIS_PROCESSES, 1, 8
    )
    performance["manual_reader_workers"] = _coerce_int_range(
        performance.get("manual_reader_workers"), DEFAULT_MANUAL_READER_WORKERS, 1, 8
    )
    performance["manual_reserved_cores"] = _coerce_int_range(
        performance.get("manual_reserved_cores"), DEFAULT_MANUAL_RESERVED_CORES, 1, 64
    )
    performance["manual_max_pending_batches"] = _coerce_int_range(
        performance.get("manual_max_pending_batches"), DEFAULT_MANUAL_MAX_PENDING_BATCHES, 1, 32
    )
    performance["performance_monitor_enabled"] = _coerce_bool(
        performance.get("performance_monitor_enabled"), DEFAULT_PERFORMANCE_MONITOR_ENABLED
    )
    performance["performance_timeline_enabled"] = _coerce_bool(
        performance.get("performance_timeline_enabled"), DEFAULT_PERFORMANCE_TIMELINE_ENABLED
    )
    try:
        sample_interval = float(performance.get("performance_sample_interval_seconds") or DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        sample_interval = DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS
    performance["performance_sample_interval_seconds"] = max(0.5, min(5.0, sample_interval))
    try:
        timeline_interval = float(performance.get("performance_timeline_interval_seconds") or DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        timeline_interval = DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS
    performance["performance_timeline_interval_seconds"] = max(5.0, min(60.0, timeline_interval))

    output = base["output"]
    output["auto_open_output_folder"] = _coerce_bool(output.get("auto_open_output_folder"), True)
    output["output_folder_prefix"] = sanitize_output_folder_prefix(output.get("output_folder_prefix"))
    output["create_csv_report_on_save"] = _coerce_bool(output.get("create_csv_report_on_save"), True)
    output["preserve_folder_structure_on_save"] = _coerce_bool(output.get("preserve_folder_structure_on_save"), False)

    highlight = base["highlight"]
    highlight["highlight_search_terms_on_open"] = _coerce_bool(
        highlight.get("highlight_search_terms_on_open"), DEFAULT_HIGHLIGHT_SEARCH_TERMS_ON_OPEN
    )
    highlight["highlight_cell_color"] = _select_allowed(
        highlight.get("highlight_cell_color"), HIGHLIGHT_CELL_COLOR_OPTIONS, DEFAULT_HIGHLIGHT_CELL_COLOR_OPTION
    )
    highlight["highlight_text_color"] = _select_allowed(
        highlight.get("highlight_text_color"), HIGHLIGHT_TEXT_COLOR_OPTIONS, DEFAULT_HIGHLIGHT_TEXT_COLOR_OPTION
    )
    highlight["open_result_mode"] = _select_allowed(
        _normalize_open_result_mode(highlight.get("open_result_mode")),
        OPEN_RESULT_MODE_OPTIONS,
        DEFAULT_OPEN_RESULT_MODE_OPTION,
    )

    experience = base["experience"]
    remember_last_use = _coerce_bool(experience.get("remember_last_use"), DEFAULT_REMEMBER_LAST_USE)
    experience["remember_last_use"] = remember_last_use
    experience["save_search_history"] = _coerce_bool(experience.get("save_search_history"), remember_last_use)
    experience["remember_last_analysis_mode"] = _coerce_bool(
        experience.get("remember_last_analysis_mode"), remember_last_use
    )
    experience["remember_last_location"] = _coerce_bool(experience.get("remember_last_location"), remember_last_use)
    experience["remember_last_search_settings"] = _coerce_bool(
        experience.get("remember_last_search_settings"), remember_last_use
    )

    state = base["state"]
    state["last_analysis_mode"] = _select_allowed(
        state.get("last_analysis_mode"), ANALYSIS_MODE_OPTIONS, ANALYSIS_MODE_FOLDER
    )
    state["last_folder"] = sanitize_text_setting(state.get("last_folder"))
    state["last_file"] = sanitize_text_setting(state.get("last_file"))
    state["last_search_text"] = sanitize_text_setting(state.get("last_search_text"))
    state["last_context_filter"] = sanitize_text_setting(state.get("last_context_filter"))
    state["last_category"] = sanitize_text_setting(state.get("last_category")) or DEFAULT_CATEGORY_NAME
    state["last_discard_filter"] = sanitize_text_setting(state.get("last_discard_filter")) or DEFAULT_CATEGORY_NAME
    state["last_file_types"] = sanitize_file_type_selection(
        state.get("last_file_types"), search.get("default_file_types", [DEFAULT_FILE_TYPE_OPTION])
    )
    state["last_file_type"] = state["last_file_types"][0]
    state["last_search_scope"] = _select_allowed(
        state.get("last_search_scope"), SEARCH_SCOPE_OPTIONS, search["default_search_scope"]
    )

    filters = base["filters"]
    filters["ignored_folder_keywords"] = sanitize_text_setting(filters.get("ignored_folder_keywords"))
    filters["ignored_file_keywords"] = sanitize_text_setting(filters.get("ignored_file_keywords"))
    filters["ignored_folder_paths"] = sanitize_path_list(filters.get("ignored_folder_paths"))
    filters["ignored_file_paths"] = sanitize_path_list(filters.get("ignored_file_paths"))
    filters["saved_discard_terms"] = sanitize_saved_discard_terms(filters.get("saved_discard_terms"))
    filters[BROAD_SCAN_ENABLED_KEY] = _coerce_bool(
        filters.get(BROAD_SCAN_ENABLED_KEY), BROAD_SCAN_DEFAULTS[BROAD_SCAN_ENABLED_KEY]
    )
    for option in BROAD_SCAN_OPTIONS:
        filters[option.setting_key] = _coerce_bool(
            filters.get(option.setting_key), option.default_enabled
        )

    history = base["history"]
    history["search_history"] = sanitize_search_history(history.get("search_history"))

    runtime = base["runtime"]
    if not sanitize_text_setting(runtime.get("created_at_utc")):
        runtime["created_at_utc"] = utc_now_iso()
    runtime["updated_at_utc"] = utc_now_iso()
    runtime.setdefault("source", "Smart Filter factory defaults")

    return base


def to_flat_settings(settings_data: Mapping[str, Any]) -> dict[str, Any]:
    data = sanitize_settings_data(settings_data)
    visual = data["visual"]
    metrics = data["metrics"]
    search = data["search"]
    performance = data["performance"]
    output = data["output"]
    highlight = data["highlight"]
    experience = data["experience"]
    state = data["state"]
    filters = data["filters"]
    history = data["history"]

    appearance_mode = str(visual.get("appearance_mode") or "dark")
    theme = _GUI_APPEARANCE_TO_THEME.get(appearance_mode, DEFAULT_THEME_OPTION)

    return {
        "default_file_type": search["default_file_type"],
        "default_file_types": list(search["default_file_types"]),
        "default_search_scope": search["default_search_scope"],
        "processing_mode": performance["processing_mode"],
        "resource_profile": performance["resource_profile"],
        "manual_analysis_processes": performance["manual_analysis_processes"],
        "manual_reader_workers": performance["manual_reader_workers"],
        "manual_reserved_cores": performance["manual_reserved_cores"],
        "manual_max_pending_batches": performance["manual_max_pending_batches"],
        "performance_monitor_enabled": performance["performance_monitor_enabled"],
        "performance_timeline_enabled": performance["performance_timeline_enabled"],
        "performance_sample_interval_seconds": performance["performance_sample_interval_seconds"],
        "performance_timeline_interval_seconds": performance["performance_timeline_interval_seconds"],
        "auto_open_output_folder": output["auto_open_output_folder"],
        "theme": theme,
        "output_folder_prefix": output["output_folder_prefix"],
        "create_csv_report_on_save": output["create_csv_report_on_save"],
        "preserve_folder_structure_on_save": output["preserve_folder_structure_on_save"],
        "max_content_file_size": search["max_content_file_size"],
        "highlight_search_terms_on_open": highlight["highlight_search_terms_on_open"],
        "highlight_cell_color": highlight["highlight_cell_color"],
        "highlight_text_color": highlight["highlight_text_color"],
        "open_result_mode": highlight["open_result_mode"],
        "results_density": visual["table_density"],
        "app_font_family": visual["font_family"],
        "app_font_size": visual["font_size"],
        "custom_accent_enabled": bool(visual.get("custom_accent_enabled", DEFAULT_CUSTOM_ACCENT_ENABLED)),
        "custom_accent_hex": sanitize_custom_accent_hex(visual.get("custom_accent_hex")),
        "custom_surface_enabled": bool(visual.get("custom_surface_enabled", DEFAULT_CUSTOM_SURFACE_ENABLED)),
        "custom_surface_hex": sanitize_hex_color(visual.get("custom_surface_hex"), DEFAULT_CUSTOM_SURFACE_HEX),
        "show_metrics_before_search": metrics["show_before_search"],
        "metric_card_size": metrics["size"],
        "metric_card_style": metrics["style"],
        "remember_last_use": experience["remember_last_use"],
        "save_search_history": experience["save_search_history"],
        "remember_last_analysis_mode": experience["remember_last_analysis_mode"],
        "remember_last_location": experience["remember_last_location"],
        "remember_last_search_settings": experience["remember_last_search_settings"],
        "last_analysis_mode": state["last_analysis_mode"],
        "last_folder": state["last_folder"],
        "last_file": state["last_file"],
        "last_search_text": state["last_search_text"],
        "last_context_filter": state["last_context_filter"],
        "last_category": state["last_category"],
        "last_discard_filter": state["last_discard_filter"],
        "last_file_type": state["last_file_type"],
        "last_file_types": list(state["last_file_types"]),
        "last_search_scope": state["last_search_scope"],
        "search_history": list(history["search_history"]),
        "ignored_folder_keywords": filters["ignored_folder_keywords"],
        "ignored_file_keywords": filters["ignored_file_keywords"],
        "ignored_folder_paths": list(filters["ignored_folder_paths"]),
        "ignored_file_paths": list(filters["ignored_file_paths"]),
        "saved_discard_terms": list(filters["saved_discard_terms"]),
        BROAD_SCAN_ENABLED_KEY: bool(filters[BROAD_SCAN_ENABLED_KEY]),
        **{option.setting_key: bool(filters[option.setting_key]) for option in BROAD_SCAN_OPTIONS},
    }


def from_flat_settings(flat_settings: Mapping[str, Any], *, base_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = sanitize_settings_data(base_data or _clone_defaults())
    settings = dict(flat_settings or {})

    data["visual"].update(
        GuiPreferences(
            appearance_mode=_THEME_TO_GUI_APPEARANCE.get(str(settings.get("theme") or DEFAULT_THEME_OPTION), "dark"),
            color_theme=str(data["visual"].get("color_theme") or "blue"),
            surface_theme=str(data["visual"].get("surface_theme") or "onyx"),
            font_family=str(settings.get("app_font_family") or data["visual"].get("font_family") or DEFAULT_APP_FONT_FAMILY_OPTION),
            font_size=str(settings.get("app_font_size") or data["visual"].get("font_size") or DEFAULT_APP_FONT_SIZE_OPTION),
            table_density=str(settings.get("results_density") or data["visual"].get("table_density") or DEFAULT_RESULTS_DENSITY_OPTION),
        ).to_dict()
    )
    data["visual"]["custom_accent_enabled"] = settings.get(
        "custom_accent_enabled",
        data["visual"].get("custom_accent_enabled", DEFAULT_CUSTOM_ACCENT_ENABLED),
    )
    data["visual"]["custom_accent_hex"] = sanitize_custom_accent_hex(
        settings.get(
            "custom_accent_hex",
            data["visual"].get("custom_accent_hex", DEFAULT_CUSTOM_ACCENT_HEX),
        )
    )
    data["visual"]["custom_surface_enabled"] = settings.get(
        "custom_surface_enabled",
        data["visual"].get("custom_surface_enabled", DEFAULT_CUSTOM_SURFACE_ENABLED),
    )
    data["visual"]["custom_surface_hex"] = sanitize_hex_color(
        settings.get(
            "custom_surface_hex",
            data["visual"].get("custom_surface_hex", DEFAULT_CUSTOM_SURFACE_HEX),
        ),
        DEFAULT_CUSTOM_SURFACE_HEX,
    )

    data["metrics"].update(
        {
            "show_before_search": settings.get("show_metrics_before_search", data["metrics"].get("show_before_search")),
            "size": settings.get("metric_card_size", data["metrics"].get("size")),
            "style": settings.get("metric_card_style", data["metrics"].get("style")),
        }
    )

    data["search"].update(
        {
            "default_file_type": settings.get("default_file_type", data["search"].get("default_file_type")),
            "default_file_types": settings.get("default_file_types", data["search"].get("default_file_types")),
            "default_search_scope": settings.get("default_search_scope", data["search"].get("default_search_scope")),
            "default_category": settings.get("default_category", data["search"].get("default_category")),
            "max_content_file_size": settings.get("max_content_file_size", data["search"].get("max_content_file_size")),
        }
    )
    data["performance"].update(
        {
            "processing_mode": settings.get("processing_mode", data["performance"].get("processing_mode")),
            "resource_profile": settings.get("resource_profile", data["performance"].get("resource_profile")),
            "manual_analysis_processes": settings.get("manual_analysis_processes", data["performance"].get("manual_analysis_processes")),
            "manual_reader_workers": settings.get("manual_reader_workers", data["performance"].get("manual_reader_workers")),
            "manual_reserved_cores": settings.get("manual_reserved_cores", data["performance"].get("manual_reserved_cores")),
            "manual_max_pending_batches": settings.get("manual_max_pending_batches", data["performance"].get("manual_max_pending_batches")),
            "performance_monitor_enabled": settings.get("performance_monitor_enabled", data["performance"].get("performance_monitor_enabled")),
            "performance_timeline_enabled": settings.get("performance_timeline_enabled", data["performance"].get("performance_timeline_enabled")),
            "performance_sample_interval_seconds": settings.get("performance_sample_interval_seconds", data["performance"].get("performance_sample_interval_seconds")),
            "performance_timeline_interval_seconds": settings.get("performance_timeline_interval_seconds", data["performance"].get("performance_timeline_interval_seconds")),
        }
    )
    data["output"].update(
        {
            "auto_open_output_folder": settings.get("auto_open_output_folder", data["output"].get("auto_open_output_folder")),
            "output_folder_prefix": settings.get("output_folder_prefix", data["output"].get("output_folder_prefix")),
            "create_csv_report_on_save": settings.get("create_csv_report_on_save", data["output"].get("create_csv_report_on_save")),
            "preserve_folder_structure_on_save": settings.get(
                "preserve_folder_structure_on_save", data["output"].get("preserve_folder_structure_on_save")
            ),
        }
    )
    data["highlight"].update(
        {
            "highlight_search_terms_on_open": settings.get(
                "highlight_search_terms_on_open", data["highlight"].get("highlight_search_terms_on_open")
            ),
            "highlight_cell_color": settings.get("highlight_cell_color", data["highlight"].get("highlight_cell_color")),
            "highlight_text_color": settings.get("highlight_text_color", data["highlight"].get("highlight_text_color")),
            "open_result_mode": settings.get("open_result_mode", data["highlight"].get("open_result_mode")),
        }
    )
    data["experience"].update(
        {
            "remember_last_use": settings.get("remember_last_use", data["experience"].get("remember_last_use")),
            "save_search_history": settings.get("save_search_history", data["experience"].get("save_search_history")),
            "remember_last_analysis_mode": settings.get(
                "remember_last_analysis_mode", data["experience"].get("remember_last_analysis_mode")
            ),
            "remember_last_location": settings.get("remember_last_location", data["experience"].get("remember_last_location")),
            "remember_last_search_settings": settings.get(
                "remember_last_search_settings", data["experience"].get("remember_last_search_settings")
            ),
        }
    )
    data["state"].update(
        {
            "last_analysis_mode": settings.get("last_analysis_mode", data["state"].get("last_analysis_mode")),
            "last_folder": settings.get("last_folder", data["state"].get("last_folder")),
            "last_file": settings.get("last_file", data["state"].get("last_file")),
            "last_search_text": settings.get("last_search_text", data["state"].get("last_search_text")),
            "last_context_filter": settings.get("last_context_filter", data["state"].get("last_context_filter")),
            "last_category": settings.get("last_category", data["state"].get("last_category")),
            "last_discard_filter": settings.get("last_discard_filter", data["state"].get("last_discard_filter")),
            "last_file_type": settings.get("last_file_type", data["state"].get("last_file_type")),
            "last_file_types": settings.get("last_file_types", data["state"].get("last_file_types")),
            "last_search_scope": settings.get("last_search_scope", data["state"].get("last_search_scope")),
        }
    )
    data["filters"].update(
        {
            "ignored_folder_keywords": settings.get("ignored_folder_keywords", data["filters"].get("ignored_folder_keywords")),
            "ignored_file_keywords": settings.get("ignored_file_keywords", data["filters"].get("ignored_file_keywords")),
            "ignored_folder_paths": settings.get("ignored_folder_paths", data["filters"].get("ignored_folder_paths")),
            "ignored_file_paths": settings.get("ignored_file_paths", data["filters"].get("ignored_file_paths")),
            "saved_discard_terms": settings.get("saved_discard_terms", data["filters"].get("saved_discard_terms")),
            BROAD_SCAN_ENABLED_KEY: settings.get(
                BROAD_SCAN_ENABLED_KEY, data["filters"].get(BROAD_SCAN_ENABLED_KEY)
            ),
            **{
                option.setting_key: settings.get(
                    option.setting_key, data["filters"].get(option.setting_key)
                )
                for option in BROAD_SCAN_OPTIONS
            },
        }
    )
    data["history"].update({"search_history": settings.get("search_history", data["history"].get("search_history"))})

    return sanitize_settings_data(data)


def _build_settings_summary(settings_data: Mapping[str, Any]) -> dict[str, Any]:
    flat_settings = to_flat_settings(settings_data)
    return {
        "status": "active",
        "total_settings": len(flat_settings),
        "sections_count": 9,
        "search_history_count": len(flat_settings.get("search_history", [])),
        "saved_discard_terms_count": len(flat_settings.get("saved_discard_terms", [])),
        "diagnostics_count": 0,
        "errors_count": 0,
    }


def build_settings_contract(settings_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = sanitize_settings_data(settings_data or _clone_defaults())
    data["runtime"]["updated_at_utc"] = utc_now_iso()
    contract = create_contract(
        file_type="config",
        subtype_key="config_type",
        subtype_value="smartfilter_settings",
        tool_name=APP_NAME,
        module_name="SettingsService",
        extra_meta={
            "tool_version": APP_VERSION,
            "updated_at_utc": data["runtime"]["updated_at_utc"],
        },
        summary=_build_settings_summary(data),
        report_brief={
            "title": "Configuración de Smart Filter",
            "description": "Preferencias de Smart Filter persistidas con contrato estándar y separadas de la plantilla de fábrica.",
        },
        data=data,
    )
    return contract


def write_settings_data(settings_data: Mapping[str, Any]) -> dict[str, Any]:
    ensure_project_directories()
    data = sanitize_settings_data(settings_data)
    write_json_file(build_settings_contract(data), SETTINGS_PATH)
    return data


def _write_default_settings() -> None:
    write_settings_data(_clone_defaults())


def ensure_settings_file() -> None:
    if SETTINGS_PATH.exists():
        return
    _write_default_settings()


def load_settings_result():
    ensure_settings_file()
    return load_config(
        SETTINGS_PATH,
        defaults=_clone_defaults(),
        required_paths=("visual", "metrics", "search", "output", "highlight", "experience", "state", "filters", "history", "runtime"),
        type_rules={
            "visual": dict,
            "metrics": dict,
            "search": dict,
            "output": dict,
            "highlight": dict,
            "experience": dict,
            "state": dict,
            "filters": dict,
            "history": dict,
            "runtime": dict,
        },
        contract_mode=True,
        validate_standard_contract=True,
        require_contract_validator=True,
    )


def load_settings() -> dict[str, Any]:
    result = load_settings_result()
    if not result.is_valid:
        return get_default_settings_data()
    return sanitize_settings_data(result.config)


def load_settings_report() -> dict[str, Any]:
    result = load_settings_result()
    if result.raw_content and isinstance(result.raw_content, dict) and result.is_valid:
        return result.raw_content
    return build_settings_contract(load_settings())


def get_settings() -> dict[str, Any]:
    return to_flat_settings(load_settings())


def write_settings(settings: Mapping[str, Any]) -> dict[str, Any]:
    if any(key in settings for key in ("visual", "metrics", "search", "performance", "output", "highlight", "experience", "state")):
        data = sanitize_settings_data(settings)
    else:
        data = from_flat_settings(settings, base_data=load_settings())
    write_settings_data(data)
    return to_flat_settings(data)


def update_settings_values(partial_settings: Mapping[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if isinstance(partial_settings, Mapping):
        settings.update(dict(partial_settings))
    return write_settings(settings)


def get_metric_card_size_options() -> list[str]:
    return list(METRICS_SIZE_OPTIONS)


def get_metric_card_style_options() -> list[str]:
    return list(METRICS_STYLE_OPTIONS)


def load_gui_preferences() -> GuiPreferences:
    return GuiPreferences.from_mapping(load_settings().get("visual", {}))


def save_gui_preferences(preferences: GuiPreferences) -> None:
    data = load_settings()
    current_visual = dict(data.get("visual", {}))
    custom_accent_enabled = current_visual.get("custom_accent_enabled", DEFAULT_CUSTOM_ACCENT_ENABLED)
    custom_accent_hex = sanitize_custom_accent_hex(current_visual.get("custom_accent_hex", DEFAULT_CUSTOM_ACCENT_HEX))
    custom_surface_enabled = current_visual.get("custom_surface_enabled", DEFAULT_CUSTOM_SURFACE_ENABLED)
    custom_surface_hex = sanitize_hex_color(current_visual.get("custom_surface_hex", DEFAULT_CUSTOM_SURFACE_HEX), DEFAULT_CUSTOM_SURFACE_HEX)
    data["visual"] = preferences.to_dict()
    data["visual"]["custom_accent_enabled"] = custom_accent_enabled
    data["visual"]["custom_accent_hex"] = custom_accent_hex
    data["visual"]["custom_surface_enabled"] = custom_surface_enabled
    data["visual"]["custom_surface_hex"] = custom_surface_hex
    write_settings_data(data)


def add_search_history_entry(search_text: Any) -> dict[str, Any]:
    clean_search_text = sanitize_text_setting(search_text)
    if not clean_search_text:
        return get_settings()

    settings = get_settings()
    if not settings.get("save_search_history", DEFAULT_SAVE_SEARCH_HISTORY):
        return settings

    current_history = sanitize_search_history(settings.get("search_history", []))
    normalized_value = clean_search_text.casefold()
    new_history = [clean_search_text]

    for item in current_history:
        if item.casefold() == normalized_value:
            continue
        new_history.append(item)
        if len(new_history) >= MAX_SEARCH_HISTORY_ITEMS:
            break

    settings["search_history"] = new_history
    return write_settings(settings)


def clear_search_history() -> dict[str, Any]:
    settings = get_settings()
    settings["search_history"] = []
    return write_settings(settings)


def add_saved_discard_terms(discard_terms: Any) -> dict[str, Any]:
    settings = get_settings()
    current_terms = sanitize_saved_discard_terms(settings.get("saved_discard_terms", []))
    seen_terms = {term.casefold() for term in current_terms}

    if isinstance(discard_terms, str):
        candidate_terms = [discard_terms]
    else:
        candidate_terms = discard_terms or []

    for term in candidate_terms:
        clean_term = sanitize_text_setting(term)
        lookup_key = clean_term.casefold()
        if not clean_term or lookup_key in seen_terms:
            continue
        current_terms.append(clean_term)
        seen_terms.add(lookup_key)
        if len(current_terms) >= MAX_SAVED_DISCARD_TERMS:
            break

    settings["saved_discard_terms"] = current_terms
    return write_settings(settings)


def remove_saved_discard_term(discard_term: Any) -> dict[str, Any]:
    clean_discard_term = sanitize_text_setting(discard_term).casefold()
    if not clean_discard_term:
        return get_settings()

    settings = get_settings()
    settings["saved_discard_terms"] = [
        term for term in sanitize_saved_discard_terms(settings.get("saved_discard_terms", []))
        if term.casefold() != clean_discard_term
    ]
    return write_settings(settings)


def clear_saved_discard_terms() -> dict[str, Any]:
    settings = get_settings()
    settings["saved_discard_terms"] = []
    return write_settings(settings)


def reset_settings() -> dict[str, Any]:
    return write_settings_data(_clone_defaults()) and get_settings()


def save_settings(
    default_file_type: str,
    default_search_scope: str,
    auto_open_output_folder: bool,
    theme: str,
    output_folder_prefix: str,
    create_csv_report_on_save: bool,
    preserve_folder_structure_on_save: bool,
    max_content_file_size: str,
    highlight_search_terms_on_open: bool,
    highlight_cell_color: str,
    highlight_text_color: str,
    open_result_mode: str = DEFAULT_OPEN_RESULT_MODE_OPTION,
    results_density: str = DEFAULT_RESULTS_DENSITY_OPTION,
    app_font_family: str = DEFAULT_APP_FONT_FAMILY_OPTION,
    app_font_size: str = DEFAULT_APP_FONT_SIZE_OPTION,
    custom_accent_enabled: bool = DEFAULT_CUSTOM_ACCENT_ENABLED,
    custom_accent_hex: str = DEFAULT_CUSTOM_ACCENT_HEX,
    custom_surface_enabled: bool = DEFAULT_CUSTOM_SURFACE_ENABLED,
    custom_surface_hex: str = DEFAULT_CUSTOM_SURFACE_HEX,
    show_metrics_before_search: bool = DEFAULT_METRICS_SHOW_BEFORE_SEARCH,
    metric_card_size: str = DEFAULT_METRICS_SIZE_OPTION,
    metric_card_style: str = DEFAULT_METRICS_STYLE_OPTION,
    save_search_history: bool = DEFAULT_SAVE_SEARCH_HISTORY,
    remember_last_analysis_mode: bool = DEFAULT_REMEMBER_LAST_ANALYSIS_MODE,
    remember_last_location: bool = DEFAULT_REMEMBER_LAST_LOCATION,
    remember_last_search_settings: bool = DEFAULT_REMEMBER_LAST_SEARCH_SETTINGS,
    remember_last_use: bool | None = None,
    ignored_folder_keywords: str = "",
    ignored_file_keywords: str = "",
    ignored_folder_paths: list[str] | None = None,
    ignored_file_paths: list[str] | None = None,
    broad_scan_safe_enabled: bool = BROAD_SCAN_DEFAULTS[BROAD_SCAN_ENABLED_KEY],
    broad_scan_exclude_system: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_system"],
    broad_scan_exclude_temp_cache: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_temp_cache"],
    broad_scan_exclude_dev_dependencies: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_dev_dependencies"],
    broad_scan_exclude_build_outputs: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_build_outputs"],
    broad_scan_exclude_smartfilter_results: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_smartfilter_results"],
    broad_scan_exclude_installed_apps: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_installed_apps"],
    broad_scan_exclude_shared_system_data: bool = BROAD_SCAN_DEFAULTS["broad_scan_exclude_shared_system_data"],
    processing_mode: str = DEFAULT_PROCESSING_MODE,
    resource_profile: str = DEFAULT_RESOURCE_PROFILE,
    manual_analysis_processes: int = DEFAULT_MANUAL_ANALYSIS_PROCESSES,
    manual_reader_workers: int = DEFAULT_MANUAL_READER_WORKERS,
    manual_reserved_cores: int = DEFAULT_MANUAL_RESERVED_CORES,
    manual_max_pending_batches: int = DEFAULT_MANUAL_MAX_PENDING_BATCHES,
    performance_monitor_enabled: bool = DEFAULT_PERFORMANCE_MONITOR_ENABLED,
    performance_timeline_enabled: bool = DEFAULT_PERFORMANCE_TIMELINE_ENABLED,
    performance_sample_interval_seconds: float = DEFAULT_PERFORMANCE_SAMPLE_INTERVAL_SECONDS,
    performance_timeline_interval_seconds: float = DEFAULT_PERFORMANCE_TIMELINE_INTERVAL_SECONDS,
) -> dict[str, Any]:
    current_settings = get_settings()
    updated_settings = {
            **current_settings,
            "default_file_type": default_file_type,
            "default_file_types": [default_file_type],
            "default_search_scope": default_search_scope,
            "auto_open_output_folder": auto_open_output_folder,
            "theme": theme,
            "processing_mode": processing_mode,
            "resource_profile": resource_profile,
            "manual_analysis_processes": manual_analysis_processes,
            "manual_reader_workers": manual_reader_workers,
            "manual_reserved_cores": manual_reserved_cores,
            "manual_max_pending_batches": manual_max_pending_batches,
            "performance_monitor_enabled": performance_monitor_enabled,
            "performance_timeline_enabled": performance_timeline_enabled,
            "performance_sample_interval_seconds": performance_sample_interval_seconds,
            "performance_timeline_interval_seconds": performance_timeline_interval_seconds,
            "output_folder_prefix": output_folder_prefix,
            "create_csv_report_on_save": create_csv_report_on_save,
            "preserve_folder_structure_on_save": preserve_folder_structure_on_save,
            "max_content_file_size": max_content_file_size,
            "highlight_search_terms_on_open": highlight_search_terms_on_open,
            "highlight_cell_color": highlight_cell_color,
            "highlight_text_color": highlight_text_color,
            "open_result_mode": open_result_mode,
            "results_density": results_density,
            "app_font_family": app_font_family,
            "app_font_size": app_font_size,
            "custom_accent_enabled": custom_accent_enabled,
            "custom_accent_hex": sanitize_custom_accent_hex(custom_accent_hex),
            "custom_surface_enabled": custom_surface_enabled,
            "custom_surface_hex": sanitize_hex_color(custom_surface_hex, DEFAULT_CUSTOM_SURFACE_HEX),
            "show_metrics_before_search": show_metrics_before_search,
            "metric_card_size": metric_card_size,
            "metric_card_style": metric_card_style,
            "save_search_history": save_search_history,
            "remember_last_analysis_mode": remember_last_analysis_mode,
            "remember_last_location": remember_last_location,
            "remember_last_search_settings": remember_last_search_settings,
            "remember_last_use": (
                remember_last_use
                if remember_last_use is not None
                else (
                    save_search_history
                    or remember_last_analysis_mode
                    or remember_last_location
                    or remember_last_search_settings
                )
            ),
            "ignored_folder_keywords": ignored_folder_keywords,
            "ignored_file_keywords": ignored_file_keywords,
            "ignored_folder_paths": sanitize_path_list(ignored_folder_paths),
            "ignored_file_paths": sanitize_path_list(ignored_file_paths),
            BROAD_SCAN_ENABLED_KEY: bool(broad_scan_safe_enabled),
            "broad_scan_exclude_system": bool(broad_scan_exclude_system),
            "broad_scan_exclude_temp_cache": bool(broad_scan_exclude_temp_cache),
            "broad_scan_exclude_dev_dependencies": bool(broad_scan_exclude_dev_dependencies),
            "broad_scan_exclude_build_outputs": bool(broad_scan_exclude_build_outputs),
            "broad_scan_exclude_smartfilter_results": bool(broad_scan_exclude_smartfilter_results),
            "broad_scan_exclude_installed_apps": bool(broad_scan_exclude_installed_apps),
            "broad_scan_exclude_shared_system_data": bool(broad_scan_exclude_shared_system_data),
        }

    if not remember_last_location:
        updated_settings["last_folder"] = ""
        updated_settings["last_file"] = ""

    if not remember_last_search_settings:
        updated_settings["last_search_text"] = ""
        updated_settings["last_context_filter"] = ""
        updated_settings["last_category"] = DEFAULT_CATEGORY_NAME
        updated_settings["last_discard_filter"] = DEFAULT_CATEGORY_NAME
        updated_settings["last_file_type"] = default_file_type or DEFAULT_FILE_TYPE_OPTION
        updated_settings["last_file_types"] = [default_file_type or DEFAULT_FILE_TYPE_OPTION]
        updated_settings["last_search_scope"] = default_search_scope or DEFAULT_SEARCH_SCOPE_OPTION

    if not remember_last_analysis_mode:
        updated_settings["last_analysis_mode"] = ANALYSIS_MODE_FOLDER

    return write_settings(updated_settings)


def get_resource_profile_options() -> list[str]:
    return list(RESOURCE_PROFILE_OPTIONS)


def get_processing_mode_options() -> list[str]:
    return list(PROCESSING_MODE_OPTIONS)


def get_theme_options() -> list[str]:
    return list(THEME_OPTIONS)


def get_max_content_file_size_options() -> list[str]:
    return list(MAX_CONTENT_FILE_SIZE_OPTIONS)


def get_highlight_cell_color_options() -> list[str]:
    return list(HIGHLIGHT_CELL_COLOR_OPTIONS)


def get_highlight_text_color_options() -> list[str]:
    return list(HIGHLIGHT_TEXT_COLOR_OPTIONS)


def get_open_result_mode_options() -> list[str]:
    return list(OPEN_RESULT_MODE_OPTIONS)


def get_results_density_options() -> list[str]:
    return list(RESULTS_DENSITY_OPTIONS)


def get_app_font_family_options() -> list[str]:
    return list(APP_FONT_FAMILY_OPTIONS)


def get_app_font_size_options() -> list[str]:
    return list(APP_FONT_SIZE_OPTIONS)


def get_max_content_file_size_bytes(max_content_file_size_option: str) -> int | None:
    return MAX_CONTENT_FILE_SIZE_BYTES.get(max_content_file_size_option)


def get_highlight_cell_color_palette(highlight_cell_color_option: str) -> dict[str, str | None]:
    return HIGHLIGHT_CELL_COLOR_PALETTES.get(highlight_cell_color_option, HIGHLIGHT_CELL_COLOR_PALETTES[DEFAULT_HIGHLIGHT_CELL_COLOR_OPTION])


def get_highlight_text_color_hex(highlight_text_color_option: str) -> str | None:
    return HIGHLIGHT_TEXT_COLOR_HEX.get(highlight_text_color_option, HIGHLIGHT_TEXT_COLOR_HEX[DEFAULT_HIGHLIGHT_TEXT_COLOR_OPTION])
