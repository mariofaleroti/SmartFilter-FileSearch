from __future__ import annotations

from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.paths import ensure_project_directories
from smart_filter.services.category_service import get_category_names, load_category_document
from smart_filter.services.settings_service import get_settings, load_settings_report


def build_config_snapshot_contract() -> dict[str, Any]:
    settings = get_settings()
    settings_report = load_settings_report()
    category_document = load_category_document()
    category_names = get_category_names(include_disabled=True)

    return create_result_contract(
        result_type="smartfilter_step2_config_snapshot",
        tool_name=APP_NAME,
        module_name="Step2ConfigSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": "step2_ready",
            "settings_total": len(settings),
            "categories_total": int(category_document.get("summary", {}).get("total_categories", 0)),
            "enabled_categories": int(category_document.get("summary", {}).get("enabled_categories", 0)),
            "diagnostics_count": 0,
            "errors_count": 0,
        },
        report_brief={
            "title": "Paso 2 - SettingsService y CategoryService",
            "description": "Snapshot técnico de configuración y categorías reales cargadas desde los servicios nuevos.",
        },
        data={
            "settings_contract_meta": settings_report.get("meta", {}),
            "settings_summary": settings_report.get("summary", {}),
            "settings_flat_keys": sorted(settings.keys()),
            "category_contract_meta": category_document.get("meta", {}),
            "category_summary": category_document.get("summary", {}),
            "category_names": category_names,
            "sharedcode_usage": {
                "ConfigCore": "load_config + write_json_file para lectura/escritura robusta.",
                "JsonContractCore": "create_contract/create_result_contract para envelope estándar.",
                "DateTimeCore": "utc_now_iso/create_timestamp_pair para timestamps consistentes.",
                "GuiCore": "GuiPreferences para normalización visual.",
            },
        },
    )


def write_config_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_config_snapshot_contract(), output_path)
