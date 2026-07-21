from __future__ import annotations

from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.paths import ensure_project_directories
from smart_filter.ui.controllers.search_form_controller import build_step3_snapshot


def build_gui_snapshot_contract() -> dict[str, Any]:
    snapshot = build_step3_snapshot()
    return create_result_contract(
        result_type="smartfilter_step3_gui_snapshot",
        tool_name=APP_NAME,
        module_name="Step3GuiSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": "step3_ready",
            "gui_sections_count": len(snapshot.get("gui_sections", [])),
            "summary_rows_count": len(snapshot.get("summary_rows", [])),
            "placeholder_rows_count": len(snapshot.get("result_placeholder_rows", [])),
            "diagnostics_count": 0,
            "errors_count": 0,
        },
        report_brief={
            "title": "Paso 3 - GUI principal real sobre GuiCore",
            "description": "Snapshot técnico de la interfaz principal reconstruida sobre GuiCore y alimentada por los servicios reales del Paso 2.",
        },
        data={
            **snapshot,
            "sharedcode_usage": {
                "GuiCore": "Ventana principal, sidebar, secciones, controles, progreso, tabla, diálogos y preferencias visuales.",
                "ConfigCore": "Persistencia de últimos filtros/ruta/historial mediante SettingsService.",
                "JsonContractCore": "Snapshots técnicos y contratos estándar.",
                "DateTimeCore": "Timestamps de snapshot y estado visual.",
                "FileScanCore": "Reservado para el Paso 5; la GUI ya entrega ruta/modo/tipos al futuro pipeline.",
            },
            "smartfilter_keeps": [
                "Semántica de búsqueda",
                "Categorías inteligentes",
                "Filtros de descarte",
                "Exclusiones puntuales",
                "Selección múltiple de tipos",
                "Tabla/acciones de resultados",
            ],
        },
    )


def write_gui_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_gui_snapshot_contract(), output_path)
