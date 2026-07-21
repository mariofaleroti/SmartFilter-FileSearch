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


def _prepare_step5_fixture() -> Path:
    fixture_root = RUNTIME_DIR / "temp" / "step5_scan_fixture"
    if fixture_root.exists():
        shutil.rmtree(fixture_root, ignore_errors=True)
    (fixture_root / "subcarpeta").mkdir(parents=True, exist_ok=True)
    (fixture_root / "node_modules").mkdir(parents=True, exist_ok=True)

    (fixture_root / "soporte_tecnico_candidato.txt").write_text("Pendiente de readers Paso 6. Coincidencia por nombre.\n", encoding="utf-8")
    (fixture_root / "descartado_soporte_tecnico.txt").write_text("Debe descartarse por nombre.\n", encoding="utf-8")
    (fixture_root / "subcarpeta" / "soporte_tecnico_redes.md").write_text("Otro candidato por nombre.\n", encoding="utf-8")
    (fixture_root / "node_modules" / "soporte_tecnico_ignorado.txt").write_text("FileScanCore default skip.\n", encoding="utf-8")
    (fixture_root / "archivo_no_soportado.exe").write_text("No debe ser candidato por extensión.\n", encoding="utf-8")
    return fixture_root


def build_step5_scan_snapshot() -> dict[str, Any]:
    ensure_project_directories()
    fixture_root = _prepare_step5_fixture()
    state = SearchFormState(
        mode=ANALYSIS_MODE_FOLDER,
        path=str(fixture_root),
        search_text="soporte tecnico",
        category="Ninguna",
        discard_filter="Ninguna",
        temporary_exclusion="descartado",
        search_scope="Solo nombre",
        file_types=["Texto (.txt/.log/.md)"],
        source="step5_scan_snapshot_fixture",
    )
    summary = run_search(state)
    payload = summary.to_dict()
    payload["scan_pipeline_scope"] = {
        "step": "Paso 5",
        "sharedcode_used_now": {
            "FileScanCore": "iter_safe_directories recorre carpetas sin seguir symlinks/reparse points y aplica exclusiones técnicas.",
            "DateTimeCore": "timestamps del request/resumen.",
            "JsonContractCore": "envelope estándar del snapshot.",
        },
        "smartfilter_keeps": [
            "extensiones soportadas",
            "archivos temporales",
            "keywords ignoradas de archivo",
            "filtros de descarte",
            "coincidencias por nombre/contenido",
        ],
        "deferred_to_next_steps": {
            "Paso 6": "Los readers llenarán content_text con contenido real por formato.",
            "Paso 7": "Acciones reales sobre tabla: abrir, destacar, copiar y exportar.",
        },
    }
    return payload


def build_step5_scan_contract() -> dict[str, Any]:
    snapshot = build_step5_scan_snapshot()
    counters = snapshot.get("counters", {})
    scan_stats = snapshot.get("scan_stats", {})
    return create_result_contract(
        result_type="smartfilter_step5_scan_pipeline_snapshot",
        tool_name=APP_NAME,
        module_name="Step5ScanPipelineSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": snapshot.get("status", "completed"),
            "directories_scanned_count": scan_stats.get("directories_scanned_count", 0),
            "files_seen_count": scan_stats.get("files_seen_count", 0),
            "candidates_count": scan_stats.get("candidates_count", 0),
            "analyzed_candidates_count": counters.get("analyzed_candidates_count", 0),
            "matched_candidates_count": counters.get("matched_candidates_count", 0),
            "match_occurrences_count": counters.get("match_occurrences_count", 0),
            "skipped_by_discard_count": counters.get("skipped_by_discard_count", 0),
            "diagnostics_count": 0,
            "errors_count": len(snapshot.get("errors", [])),
        },
        report_brief={
            "title": "Paso 5 - FileScanCore + pipeline de escaneo",
            "description": "Snapshot técnico del pipeline real: FileScanCore alimenta candidatos reales y Smart Filter aplica su motor propio.",
            "recommendations": [
                "Mantener FileScanCore neutral: camina carpetas, no interpreta archivos.",
                "Conectar readers propios en Paso 6 para completar búsquedas por contenido real.",
            ],
        },
        data=snapshot,
        errors=[{"code": "SCAN_PIPELINE_ERROR", "message": error} for error in snapshot.get("errors", [])],
    )


def write_step5_scan_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_step5_scan_contract(), output_path)
