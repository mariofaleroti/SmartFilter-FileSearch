from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.scan_exclusions import build_scan_exclusion_context
from smart_filter.domain.search_config import ANALYSIS_MODE_FOLDER
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.domain.search_models import SearchSummary
from smart_filter.engine.scan_pipeline import _deduplicate_issues
from smart_filter.engine.search_engine import build_search_request


def main() -> int:
    permission_base = {
        "code": "permission_denied",
        "error_type": "permission_denied",
        "path": "C:/ProgramData/protegido",
        "message": "Acceso denegado",
        "exception_type": "PermissionError",
        "source": "filescan_core",
        "severity": "warning",
    }
    raw_details = [
        {**permission_base, "stage": "file_enumeration"},
        {**permission_base, "stage": "directory_enumeration"},
        {
            "code": "reader_error",
            "error_type": "reader_error",
            "path": "C:/archivo.xlsx",
            "stage": "content_read",
            "message": "File is not a zip file",
            "exception_type": None,
            "source": "smart_filter",
            "severity": "warning",
        },
    ]
    raw_errors = ["uno", "dos", "tres"]
    errors, details, rollup = _deduplicate_issues(raw_errors, raw_details)

    if len(errors) != 2 or len(details) != 2:
        raise AssertionError((errors, details))
    if rollup.issues_count != 2 or rollup.duplicate_occurrences_count != 1:
        raise AssertionError(rollup)
    if rollup.scan_issues_count != 1 or rollup.warnings_count != 2:
        raise AssertionError(rollup)

    merged = next(item for item in details if item["error_type"] == "permission_denied")
    if merged.get("occurrences_count") != 2:
        raise AssertionError(merged)
    if set(merged.get("stages", [])) != {"file_enumeration", "directory_enumeration"}:
        raise AssertionError(merged)

    state = SearchFormState(
        mode=ANALYSIS_MODE_FOLDER,
        path="C:/",
        search_text="prueba",
        category="Ninguna",
        discard_filter="Ninguna",
        temporary_exclusion="",
        search_scope="Nombre y contenido",
        file_types=["Excel (.xlsx)"],
        source="issue_rollup_validator",
    )
    summary = SearchSummary(
        request=build_search_request(state),
        errors=errors,
        error_details=details,
    )
    if summary.status != "completed_with_warnings":
        raise AssertionError(summary.status)

    context = build_scan_exclusion_context(
        root_path="/",
        settings={
            "broad_scan_safe_enabled": True,
            "broad_scan_exclude_smartfilter_results": True,
            "output_folder_prefix": "Mis_Resultados",
        },
    )
    for output_path in (
        "/home/user/SmartFilter_Resultados_20260715_120000",
        "/home/user/SmartFilterCV_Resultados_20260623_105323",
        "/home/user/Mis_Resultados_20260715_120000",
    ):
        match = context.policy.match(output_path, root_path="/")
        if match is None or match.group_id != "smartfilter_generated_results":
            raise AssertionError((output_path, match))

    print("OK: incidencias deduplicadas, advertencias separadas y resultados anteriores excluibles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
