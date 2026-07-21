from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from date_time_core import utc_now_iso
from json_contract_core import create_result_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine.search_engine import build_search_request, build_sample_candidates, search_candidates
from smart_filter.paths import ensure_project_directories
from smart_filter.ui.controllers.search_form_controller import build_initial_form_state


def build_step4_search_snapshot(state: SearchFormState | None = None) -> dict[str, Any]:
    if state is None:
        state = build_initial_form_state()
        if not state.search_text and not state.has_category:
            # Deterministic default so CLI/validator can prove the engine even
            # when the current settings have no remembered search.
            state = replace(
                state,
                path=state.path or "demo",
                search_text="soporte tecnico",
                source="step4_snapshot_default",
            )

    request = build_search_request(state)
    candidates = build_sample_candidates(request)
    summary = search_candidates(request, candidates)
    payload = summary.to_dict()
    payload["engine_scope"] = {
        "step": "Paso 4",
        "included_now": [
            "SearchRequest",
            "FileCandidate",
            "MatchEngine",
            "FileFilterEngine",
            "SearchEngine",
            "SearchResult",
            "SearchSummary",
        ],
        "deferred_to_next_steps": {
            "Paso 5": "FileScanCore alimentará candidatos reales desde carpetas de forma segura.",
            "Paso 6": "Los readers llenarán content_text con contenido real por formato.",
        },
    }
    return payload


def build_step4_search_contract(state: SearchFormState | None = None) -> dict[str, Any]:
    snapshot = build_step4_search_snapshot(state)
    counters = snapshot.get("counters", {})
    return create_result_contract(
        result_type="smartfilter_step4_search_engine_snapshot",
        tool_name=APP_NAME,
        module_name="Step4SearchEngineSnapshot",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": utc_now_iso(),
        },
        summary={
            "status": snapshot.get("status", "completed"),
            "analyzed_candidates_count": counters.get("analyzed_candidates_count", 0),
            "matched_candidates_count": counters.get("matched_candidates_count", 0),
            "match_occurrences_count": counters.get("match_occurrences_count", 0),
            "skipped_by_discard_count": counters.get("skipped_by_discard_count", 0),
            "no_match_count": counters.get("no_match_count", 0),
            "diagnostics_count": 0,
            "errors_count": len(snapshot.get("errors", [])),
        },
        report_brief={
            "title": "Paso 4 - Motor de búsqueda propio",
            "description": "Snapshot técnico del motor propio de Smart Filter: request, candidatos, coincidencias, descartes y resultados.",
            "recommendations": [
                "El recorrido seguro de carpetas queda para Paso 5 con FileScanCore.",
                "La lectura profunda de contenido por formato queda para Paso 6 con readers propios.",
            ],
        },
        data=snapshot,
        errors=[{"code": "SEARCH_ENGINE_ERROR", "message": error} for error in snapshot.get("errors", [])],
    )


def write_step4_search_snapshot(output_path: str | Path) -> Path:
    ensure_project_directories()
    return write_json_file(build_step4_search_contract(), output_path)
