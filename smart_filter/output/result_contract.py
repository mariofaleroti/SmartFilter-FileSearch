from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from date_time_core import create_timestamp_pair
from json_contract_core import create_diagnostic_entry, create_error_entry, create_result_contract, write_json_file
from logging_core import SharedLogger
from tool_runtime_core import ToolRuntimeContext

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.domain.search_models import SearchSummary


def _runtime_meta(runtime: ToolRuntimeContext, *, finished_at_utc: str, finished_at_local: str) -> dict[str, Any]:
    meta = runtime.to_meta(module_name="SmartFilterCLI", file_type="result")
    # JsonContractCore owns meta.tool_name/tool_version. Keep runtime-specific
    # metadata only, avoiding a duplicate normalized runtime tool_name.
    meta.pop("tool_name", None)
    meta.pop("tool_version", None)
    meta.pop("module_name", None)
    meta.pop("file_type", None)
    meta["run_id"] = runtime.run_id
    meta["started_at_utc"] = runtime.started_at_utc_iso
    meta["started_at_local"] = runtime.started_at_local_iso
    meta["finished_at_utc"] = finished_at_utc
    meta["finished_at_local"] = finished_at_local
    meta["local_timezone"] = runtime.local_timezone_name
    meta["local_utc_offset"] = runtime.local_utc_offset
    return meta


def _summary_counters(summary: SearchSummary) -> dict[str, Any]:
    return {
        "analyzed_candidates_count": summary.analyzed_candidates_count,
        "matched_candidates_count": summary.matched_candidates_count,
        "match_occurrences_count": summary.match_occurrences_count,
        "no_match_count": summary.no_match_count,
        "skipped_by_discard_count": summary.skipped_by_discard_count,
        "unsupported_extension_count": summary.unsupported_extension_count,
        "issues_count": len(summary.errors),
        "warnings_count": summary.warnings_count,
        "critical_errors_count": summary.critical_errors_count,
        "errors_count": summary.critical_errors_count,
    }


def _error_entries(
    messages: Iterable[str],
    details: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    message_list = [str(message or "").strip() for message in messages if str(message or "").strip()]
    detail_list = [dict(detail) for detail in (details or [])]
    entries: list[dict[str, Any]] = []

    for detail in detail_list:
        raw_code = str(detail.get("code") or detail.get("error_type") or "search_error")
        code = "SMARTFILTER_" + raw_code.upper().replace(" ", "_")
        message = str(detail.get("message") or raw_code)
        context = {
            key: detail.get(key)
            for key in ("path", "stage", "stages", "exception_type", "source", "error_type", "severity", "occurrences_count")
            if detail.get(key) not in (None, "")
        }
        entries.append(create_error_entry(code, message, context=context))

    # Compatibility fallback for older summaries that only contain plain strings.
    for message in message_list[len(detail_list):]:
        entries.append(create_error_entry("SMARTFILTER_SEARCH_ERROR", message))
    return entries


def _error_breakdown(details: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for detail in details:
        key = str(detail.get("error_type") or detail.get("code") or "unknown_error")
        breakdown[key] = breakdown.get(key, 0) + 1
    return dict(sorted(breakdown.items()))


def build_search_results_contract(
    *,
    summary: SearchSummary,
    runtime: ToolRuntimeContext,
    cli_options: Mapping[str, Any],
    json_output_path: str | Path | None = None,
    logger: SharedLogger | None = None,
) -> dict[str, Any]:
    """Build the standard ecosystem JSON for real Smart Filter CLI runs."""
    finished_at_utc, finished_at_local = create_timestamp_pair()
    counters = _summary_counters(summary)
    scan_stats = dict(summary.scan_stats or {})
    logger_diagnostics = logger.get_diagnostics(include_info=True, include_debug=True) if logger else []
    logger_errors = logger.get_errors() if logger else []
    warning_details = [
        detail for detail in summary.error_details if detail.get("severity") == "warning"
    ]
    critical_details = [
        detail for detail in summary.error_details if detail.get("severity") != "warning"
    ]
    search_errors = _error_entries(
        summary.errors if not summary.error_details else [],
        critical_details,
    )
    search_warnings = [
        create_diagnostic_entry(
            "WARNING",
            "SMARTFILTER_" + str(detail.get("code") or detail.get("error_type") or "SEARCH_WARNING").upper(),
            str(detail.get("message") or detail.get("code") or "Advertencia de búsqueda"),
            context={
                key: detail.get(key)
                for key in ("path", "stage", "stages", "exception_type", "source", "error_type", "occurrences_count")
                if detail.get(key) not in (None, "", [])
            },
        )
        for detail in warning_details
    ]
    all_diagnostics = [*logger_diagnostics, *search_warnings]
    all_errors = [*search_errors, *logger_errors]

    status = summary.status
    if all_errors and status != "completed_with_errors":
        status = "completed_with_errors"

    return create_result_contract(
        result_type="smartfilter_search_results",
        tool_name=APP_NAME,
        module_name="SmartFilterCLI",
        extra_meta={
            "tool_version": APP_VERSION,
            **_runtime_meta(runtime, finished_at_utc=finished_at_utc, finished_at_local=finished_at_local),
        },
        summary={
            "status": status,
            "matched_results_count": summary.match_occurrences_count,
            "matched_candidates_count": summary.matched_candidates_count,
            "match_occurrences_count": summary.match_occurrences_count,
            "analyzed_candidates_count": summary.analyzed_candidates_count,
            "files_seen_count": scan_stats.get("files_seen_count", 0),
            "directories_scanned_count": scan_stats.get("directories_scanned_count", 0),
            "reader_errors_count": scan_stats.get("reader_errors_count", 0),
            "reader_succeeded_count": scan_stats.get("reader_succeeded_count", 0),
            "reader_controlled_error_count": scan_stats.get("reader_controlled_error_count", 0),
            "reader_worker_failed_count": scan_stats.get("reader_worker_failed_count", 0),
            "content_skipped_size_count": scan_stats.get("content_skipped_size_count", 0),
            "broad_scan_safe_enabled": scan_stats.get("broad_scan_safe_enabled", False),
            "automatic_excluded_directories_count": scan_stats.get(
                "automatic_excluded_directories_count", 0
            ),
            "diagnostics_count": len(all_diagnostics),
            "warnings_count": summary.warnings_count,
            "critical_errors_count": len(all_errors),
            "errors_count": len(all_errors),
            "scan_and_read_elapsed_seconds": scan_stats.get("scan_and_read_elapsed_seconds", 0.0),
            "total_search_elapsed_seconds": scan_stats.get("total_search_elapsed_seconds", 0.0),
            "execution_pipeline_mode": scan_stats.get("execution_pipeline_mode", "legacy_separate_match"),
            "cpu_average_cores": (scan_stats.get("performance", {}).get("runtime", {}).get("cpu", {}).get("smartfilter_average_cores", 0.0)),
            "cpu_peak_cores": (scan_stats.get("performance", {}).get("runtime", {}).get("cpu", {}).get("smartfilter_peak_cores", 0.0)),
            "memory_peak_mb": (scan_stats.get("performance", {}).get("runtime", {}).get("memory", {}).get("total_peak_mb", 0.0)),
            "resource_profile": (scan_stats.get("performance", {}).get("resource_policy", {}).get("resource_profile", "")),
            "error_types": _error_breakdown(summary.error_details),
        },
        report_brief={
            "title": "Smart Filter - Resultados de búsqueda",
            "description": "Resultado estándar de Smart Filter para ejecución CLI/ecosistema.",
            "recommendations": [
                "Consumir data.search.results para integraciones técnicas.",
                "Consumir data.search.table_rows para renderes tabulares simples.",
                "Revisar diagnostics cuando summary.status sea completed_with_warnings.",
                "Revisar errors cuando summary.status sea completed_with_errors.",
            ],
        },
        data={
            "runtime": runtime.to_dict(),
            "cli_options": dict(cli_options),
            "output": {
                "json_output_path": str(json_output_path) if json_output_path is not None else None,
                "log_path": str(runtime.get_log_path(f"smart_filter_{runtime.run_id}.log")),
            },
            "request": summary.request.to_dict(),
            "performance": dict(scan_stats.get("performance") or {}),
            "search": {
                "status": status,
                "generated_at_local": summary.generated_at_local,
                "generated_at_utc": summary.generated_at_utc,
                "timing": {
                    "execution_pipeline_mode": scan_stats.get("execution_pipeline_mode", "legacy_separate_match"),
                    "match_analysis_integrated": scan_stats.get("match_analysis_integrated", False),
                    "scan_read_match_elapsed_seconds": scan_stats.get("scan_read_match_elapsed_seconds", 0.0),
                    "scan_and_read_elapsed_seconds": scan_stats.get("scan_and_read_elapsed_seconds", 0.0),
                    "scan_and_read_includes_match_analysis": scan_stats.get(
                        "scan_and_read_includes_match_analysis", False
                    ),
                    "match_analysis_elapsed_seconds": scan_stats.get("match_analysis_elapsed_seconds", 0.0),
                    "match_analysis_worker_elapsed_seconds_total": scan_stats.get(
                        "match_analysis_worker_elapsed_seconds_total", 0.0
                    ),
                    "match_analysis_separate_pass_eliminated": scan_stats.get(
                        "match_analysis_separate_pass_eliminated", False
                    ),
                    "total_search_elapsed_seconds": scan_stats.get("total_search_elapsed_seconds", 0.0),
                },
                "counters": counters,
                "scan_stats": scan_stats,
                "error_details": [dict(detail) for detail in summary.error_details],
                "results": [result.to_dict() for result in summary.results],
                "table_rows": [result.to_table_row() for result in summary.results],
            },
            "ecosystem_contract": {
                "sharedcode_used": [
                    "CliCore",
                    "ToolRuntimeCore",
                    "LoggingCore",
                    "PlatformCore",
                    "JsonContractCore",
                    "DateTimeCore",
                    "FileScanCore",
                    "ConfigCore",
                ],
                "smartfilter_keeps": [
                    "categorías inteligentes",
                    "filtros de descarte",
                    "lectores de archivos",
                    "coincidencias por nombre/contenido",
                    "acciones y experiencia de resultados",
                ],
            },
        },
        diagnostics=all_diagnostics,
        errors=all_errors,
    )


def write_search_results_contract(
    *,
    summary: SearchSummary,
    runtime: ToolRuntimeContext,
    cli_options: Mapping[str, Any],
    output_path: str | Path,
    logger: SharedLogger | None = None,
) -> Path:
    contract = build_search_results_contract(
        summary=summary,
        runtime=runtime,
        cli_options=cli_options,
        json_output_path=output_path,
        logger=logger,
    )
    return write_json_file(contract, output_path)
