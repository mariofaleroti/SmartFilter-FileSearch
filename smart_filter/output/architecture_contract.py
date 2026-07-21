from __future__ import annotations

from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.domain.architecture_map import SMARTFILTER_OWNERSHIP, get_sharedcode_feed_rows
from smart_filter.paths import ensure_project_directories


def build_architecture_contract() -> dict[str, Any]:
    rows = get_sharedcode_feed_rows()
    return create_result_contract(
        result_type="smartfilter_sharedcode_architecture_mockup",
        tool_name=APP_NAME,
        module_name="ArchitectureMockup",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": "design_mockup",
            "sharedcode_feeds_count": len(rows),
            "smartfilter_owned_responsibilities_count": len(SMARTFILTER_OWNERSHIP),
            "diagnostics_count": 0,
            "errors_count": 0,
        },
        report_brief={
            "title": "Mockup de alimentación por SharedCode",
            "description": "Mapa inicial de cómo Smart Filter será alimentado por cores comunes sin perder lógica propia.",
        },
        data={
            "sharedcode_feeds": rows,
            "smartfilter_keeps_ownership": list(SMARTFILTER_OWNERSHIP),
            "migration_blocks": [
                "Paso 1: GUI base con GuiCore + mockup técnico.",
                "Paso 2: Settings/Categories con ConfigCore, JsonContractCore y DateTimeCore.",
                "Paso 3: GUI principal real sobre GuiCore con servicios reales.",
                "Paso 4: Motor propio de Smart Filter: matching, filtros y resultados.",
                "Paso 5: FileScanCore + pipeline de escaneo seguro.",
                "Paso 6: Lectores de archivos.",
                "Paso 7: Tabla, resultados y acciones reales.",
                "Paso 8: Ventanas propias: categorías, configuración, ayuda y acerca de.",
                "Paso 9: CLI + JSON estándar con CliCore, ToolRuntimeCore, LoggingCore y JsonContractCore.",
                "Paso 10: Release limpio con ReleaseCore.",
            ],
        },
    )


def write_architecture_contract(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_architecture_contract(), output_path)
