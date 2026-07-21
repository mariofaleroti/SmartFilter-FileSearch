from __future__ import annotations

from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.services.category_service import get_categories
from smart_filter.services.settings_service import get_settings
from smart_filter.paths import ensure_project_directories


def build_step8_windows_snapshot() -> dict[str, Any]:
    categories = get_categories()
    settings = get_settings()
    return {
        "status": "completed",
        "generated_at_utc": utc_now_iso(),
        "windows": {
            "categories": {
                "status": "ready",
                "window_type": "product_window",
                "sharedcode_base": "GuiCore.SecondaryWindow",
                "service": "CategoryService",
                "editable_fields": [
                    "title",
                    "description",
                    "enabled",
                    "terms",
                    "exclude_terms",
                    "discard_categories",
                    "search_mode",
                    "target_fields",
                ],
                "categories_count": len(categories),
                "terms_count": sum(len(category.get("terms", [])) for category in categories.values()),
            },
            "settings": {
                "status": "ready",
                "window_type": "product_window",
                "sharedcode_base": "GuiCore.SecondaryWindow + GuiPreferences",
                "service": "SettingsService",
                "settings_count": len(settings),
                "sections": ["search", "output", "highlight", "visual", "experience", "filters", "history"],
                "layout": "tabbed",
                "tabs": ["Búsqueda", "Rendimiento", "Salida", "Destacado", "Visual", "Experiencia", "Exclusiones"],
                "palette_preview": True,
                "palette_source": "GuiCore.ACCENT_COLOR_PALETTE + GuiCore.SURFACE_COLOR_PALETTE",
            },
            "help": {
                "status": "ready",
                "window_type": "product_window",
                "sharedcode_base": "GuiCore.SecondaryWindow",
                "content": "Guía de uso del producto nuevo.",
            },
            "about": {
                "status": "ready",
                "window_type": "product_window",
                "sharedcode_base": "GuiCore.SecondaryWindow",
                "content": "Identidad del producto y mapa de responsabilidades.",
            },
        },
        "step8_scope": {
            "sharedcode_used_now": {
                "GuiCore": "ventanas secundarias, controles, preferencias visuales y shell visual común.",
                "ConfigCore": "carga/escritura robusta de settings y categorías.",
                "JsonContractCore": "contratos estándar persistidos por los servicios.",
                "DateTimeCore": "timestamps de configuración, categorías y snapshot.",
            },
            "smartfilter_keeps": [
                "semántica de categorías inteligentes",
                "opciones reales del producto",
                "ayuda propia",
                "acerca de propio",
                "decisión de refrescar combos/estado de búsqueda tras cambios",
            ],
        },
    }


def build_step8_windows_contract() -> dict[str, Any]:
    snapshot = build_step8_windows_snapshot()
    windows = snapshot.get("windows", {})
    categories = windows.get("categories", {})
    settings = windows.get("settings", {})
    return create_result_contract(
        result_type="smartfilter_step8_product_windows_snapshot",
        tool_name=APP_NAME,
        module_name="Step8ProductWindowsSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": snapshot.get("status", "completed"),
            "product_windows_count": len(windows),
            "categories_count": categories.get("categories_count", 0),
            "settings_count": settings.get("settings_count", 0),
            "diagnostics_count": 0,
            "errors_count": 0,
        },
        report_brief={
            "title": "Paso 8 - Ventanas propias",
            "description": "Snapshot técnico de Categorías, Configuración, Ayuda y Acerca de como ventanas propias del producto.",
            "recommendations": [
                "Mantener las ventanas como identidad de Smart Filter, usando GuiCore solo como base visual.",
                "Seguir refrescando la GUI principal tras cambios de categorías/configuración.",
            ],
        },
        data=snapshot,
    )


def write_step8_windows_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_step8_windows_contract(), output_path)
