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
from smart_filter.readers.reader_registry import get_reader_capabilities


def _prepare_step6_fixture() -> Path:
    fixture_root = RUNTIME_DIR / "temp" / "step6_reader_fixture"
    if fixture_root.exists():
        shutil.rmtree(fixture_root, ignore_errors=True)
    fixture_root.mkdir(parents=True, exist_ok=True)

    (fixture_root / "nombre_neutro.txt").write_text(
        "Este archivo contiene la frase soporte tecnico dentro del contenido, no en el nombre.\n",
        encoding="utf-8",
    )
    (fixture_root / "datos.json").write_text(
        '{"perfil": "administracion", "detalle": "soporte tecnico y redes", "estado": "activo"}',
        encoding="utf-8",
    )
    (fixture_root / "pagina.html").write_text(
        "<html><head><style>.x{}</style></head><body><h1>Smart Filter</h1><p>soporte tecnico visible</p><script>ignorado()</script></body></html>",
        encoding="utf-8",
    )
    (fixture_root / "descartado_contenido.md").write_text(
        "soporte tecnico dentro del contenido, pero este documento debe descartarse por la palabra viejo.",
        encoding="utf-8",
    )
    return fixture_root


def build_step6_content_snapshot() -> dict[str, Any]:
    ensure_project_directories()
    fixture_root = _prepare_step6_fixture()
    state = SearchFormState(
        mode=ANALYSIS_MODE_FOLDER,
        path=str(fixture_root),
        search_text="soporte tecnico",
        category="Ninguna",
        discard_filter="Ninguna",
        temporary_exclusion="viejo",
        search_scope="Solo contenido",
        file_types=["Texto (.txt/.log/.md)", "Datos (.json/.xml)", "HTML (.html/.htm)"],
        source="step6_reader_snapshot_fixture",
    )
    summary = run_search(state)
    payload = summary.to_dict()
    payload["reader_pipeline_scope"] = {
        "step": "Paso 6",
        "sharedcode_used_now": {
            "FileScanCore": "recorre carpetas/archivos de forma segura y neutral.",
            "DateTimeCore": "timestamps del request/resumen.",
            "JsonContractCore": "envelope estándar del snapshot.",
        },
        "smartfilter_keeps": [
            "reader_registry por extensión",
            "lectores xlsx/pdf/docx/csv/text/json/xml/html",
            "decisión de contenido buscable",
            "manejo de errores de reader sin romper la búsqueda completa",
            "límite max_content_file_size desde SettingsService",
        ],
        "reader_capabilities": get_reader_capabilities(),
        "deferred_to_next_steps": {
            "Paso 7": "acciones reales sobre tabla: abrir, destacar, copiar y exportar.",
            "Paso 8": "ventanas propias completas de categorías/configuración/ayuda/acerca de.",
        },
    }
    return payload


def build_step6_content_contract() -> dict[str, Any]:
    snapshot = build_step6_content_snapshot()
    counters = snapshot.get("counters", {})
    scan_stats = snapshot.get("scan_stats", {})
    return create_result_contract(
        result_type="smartfilter_step6_reader_pipeline_snapshot",
        tool_name=APP_NAME,
        module_name="Step6ReaderPipelineSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": snapshot.get("status", "completed"),
            "files_seen_count": scan_stats.get("files_seen_count", 0),
            "candidates_count": scan_stats.get("candidates_count", 0),
            "readers_executed_count": scan_stats.get("readers_executed_count", 0),
            "reader_errors_count": scan_stats.get("reader_errors_count", 0),
            "content_text_chars_count": scan_stats.get("content_text_chars_count", 0),
            "analyzed_candidates_count": counters.get("analyzed_candidates_count", 0),
            "matched_candidates_count": counters.get("matched_candidates_count", 0),
            "match_occurrences_count": counters.get("match_occurrences_count", 0),
            "skipped_by_discard_count": counters.get("skipped_by_discard_count", 0),
            "diagnostics_count": 0,
            "errors_count": len(snapshot.get("errors", [])),
        },
        report_brief={
            "title": "Paso 6 - Readers reales de contenido",
            "description": "Snapshot técnico del pipeline con contenido real: FileScanCore alimenta candidatos y Smart Filter extrae texto por formato antes de aplicar el motor.",
            "recommendations": [
                "Mantener readers como lógica propia de Smart Filter, no como responsabilidad de SharedCode.",
                "Conservar manejo defensivo: un archivo ilegible no debe romper toda la búsqueda.",
            ],
        },
        data=snapshot,
        errors=[{"code": "READER_PIPELINE_ERROR", "message": error} for error in snapshot.get("errors", [])],
    )


def write_step6_content_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_step6_content_contract(), output_path)
