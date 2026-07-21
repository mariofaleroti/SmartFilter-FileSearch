from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.domain.search_config import ANALYSIS_MODE_FOLDER
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine.search_engine import run_search
from smart_filter.paths import RUNTIME_DIR, ensure_project_directories
from smart_filter.services.result_action_service import build_paths_clipboard_text, export_results


def _prepare_step7_fixture() -> Path:
    fixture_root = RUNTIME_DIR / "temp" / "step7_actions_fixture"
    if fixture_root.exists():
        shutil.rmtree(fixture_root, ignore_errors=True)
    fixture_root.mkdir(parents=True, exist_ok=True)

    (fixture_root / "soporte_tecnico.txt").write_text(
        "Caso de soporte tecnico con redes, impresoras y Windows.\n",
        encoding="utf-8",
    )
    (fixture_root / "sin_coincidencia.txt").write_text(
        "Contenido neutro para validar tabla y acciones.\n",
        encoding="utf-8",
    )
    return fixture_root


def build_step7_actions_snapshot() -> dict[str, Any]:
    ensure_project_directories()
    fixture_root = _prepare_step7_fixture()
    state = SearchFormState(
        mode=ANALYSIS_MODE_FOLDER,
        path=str(fixture_root),
        search_text="soporte tecnico",
        category="Ninguna",
        discard_filter="Ninguna",
        temporary_exclusion="",
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        source="step7_actions_snapshot_fixture",
    )
    summary = run_search(state)
    export_outcome = export_results(summary)
    selected_results = summary.results[:1]
    return {
        "status": "completed_with_errors" if export_outcome.errors else summary.status,
        "generated_at_utc": utc_now_iso(),
        "search": summary.to_dict(),
        "actions": {
            "selected_results_count": len(selected_results),
            "paths_clipboard_preview": build_paths_clipboard_text(selected_results),
            "export_outcome": export_outcome.to_dict(),
            "available_gui_actions": [
                "abrir_original",
                "abrir_carpeta",
                "abrir_copia_destacada",
                "copiar_ruta",
                "copiar_archivos",
                "exportar_csv_json",
            ],
        },
        "step7_scope": {
            "sharedcode_used_now": {
                "GuiCore": "tabla, tooltips, selección múltiple, progreso y shell visual.",
                "DateTimeCore": "timestamps de carpetas/exportaciones/snapshot.",
                "JsonContractCore": "contrato estándar del snapshot.",
                "FileScanCore": "recorrido seguro antes de acciones.",
            },
            "smartfilter_keeps": [
                "interpretación de resultados",
                "apertura de original",
                "vista destacada temporal",
                "exportación de resultados",
                "copiado de rutas",
                "selección múltiple y acciones de producto",
            ],
        },
    }


def build_step7_actions_contract() -> dict[str, Any]:
    snapshot = build_step7_actions_snapshot()
    action_data = snapshot.get("actions", {})
    export_outcome = action_data.get("export_outcome", {})
    search = snapshot.get("search", {})
    counters = search.get("counters", {})
    return create_result_contract(
        result_type="smartfilter_step7_results_actions_snapshot",
        tool_name=APP_NAME,
        module_name="Step7ResultsActionsSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": snapshot.get("status", "completed"),
            "matched_candidates_count": counters.get("matched_candidates_count", 0),
            "match_occurrences_count": counters.get("match_occurrences_count", 0),
            "selected_results_count": action_data.get("selected_results_count", 0),
            "exported_count": export_outcome.get("exported_count", 0),
            "actions_available_count": len(action_data.get("available_gui_actions", [])),
            "diagnostics_count": 0,
            "errors_count": len(export_outcome.get("errors", [])) + len(search.get("errors", [])),
        },
        report_brief={
            "title": "Paso 7 - Tabla, resultados y acciones reales",
            "description": "Snapshot técnico de acciones reales sobre resultados: abrir, destacar y exportar.",
            "recommendations": [
                "Mantener las acciones como lógica propia de Smart Filter.",
                "Usar el hilo de trabajo para búsquedas reales y evitar congelar la GUI.",
            ],
        },
        data=snapshot,
        errors=[{"code": "STEP7_ACTION_ERROR", "message": error} for error in export_outcome.get("errors", [])],
    )


def write_step7_actions_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_step7_actions_contract(), output_path)
