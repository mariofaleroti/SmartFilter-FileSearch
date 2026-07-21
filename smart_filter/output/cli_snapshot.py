from __future__ import annotations

import shutil
from pathlib import Path

from logging_core import create_logger
from tool_runtime_core import create_runtime_context

from smart_filter.app_info import APP_VERSION
from smart_filter.domain.search_config import ANALYSIS_MODE_FOLDER
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine.search_engine import run_search
from smart_filter.output.result_contract import write_search_results_contract
from smart_filter.paths import OUTPUT_DIR, PROJECT_ROOT, RUNTIME_DIR, ensure_project_directories


def _prepare_step9_fixture() -> Path:
    fixture_root = RUNTIME_DIR / "temp" / "step9_cli_snapshot_fixture"
    if fixture_root.exists():
        shutil.rmtree(fixture_root, ignore_errors=True)
    fixture_root.mkdir(parents=True, exist_ok=True)
    (fixture_root / "soporte_redes.txt").write_text(
        "Caso de soporte tecnico con redes, impresoras, Windows y automatizacion.\n",
        encoding="utf-8",
    )
    (fixture_root / "inventario.txt").write_text(
        "Inventario sin coincidencia principal.\n",
        encoding="utf-8",
    )
    return fixture_root


def write_step9_cli_snapshot(output_path: str | Path | None = None) -> Path:
    ensure_project_directories()
    fixture_root = _prepare_step9_fixture()
    runtime = create_runtime_context(
        tool_name="SmartFilter",
        tool_version=APP_VERSION,
        base_dir=PROJECT_ROOT,
        output_dir=OUTPUT_DIR,
        logs_dir=OUTPUT_DIR / "logs",
        create_directories=True,
    )
    logger = create_logger(
        "SmartFilterCLI",
        log_path=runtime.get_log_path(f"smart_filter_{runtime.run_id}.log"),
        min_level="info",
        keep_entries=True,
    )
    logger.info("Generando snapshot CLI del Paso 9.", code="SMARTFILTER_STEP9_SNAPSHOT")
    state = SearchFormState(
        mode=ANALYSIS_MODE_FOLDER,
        path=str(fixture_root),
        search_text="soporte tecnico",
        category="Ninguna",
        discard_filter="Ninguna",
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        source="step9_cli_snapshot_fixture",
    )
    summary = run_search(state)
    target = Path(output_path or OUTPUT_DIR / "smartfilter_step9_cli_results_snapshot.json")
    return write_search_results_contract(
        summary=summary,
        runtime=runtime,
        cli_options={
            "source": "development_snapshot",
            "quiet": False,
            "verbose": 1,
            "debug": False,
        },
        output_path=target,
        logger=logger,
    )
