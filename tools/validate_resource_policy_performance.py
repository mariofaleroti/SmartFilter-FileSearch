from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine import scan_pipeline
from smart_filter.engine.resource_policy import (
    CpuTopology,
    PROCESSING_MODE_AUTOMATIC,
    PROCESSING_MODE_MANUAL,
    RESOURCE_PROFILE_BALANCED,
    RESOURCE_PROFILE_HIGH,
    RESOURCE_PROFILE_LOW,
    resolve_resource_policy,
)
from smart_filter.engine.search_engine import run_search
from smart_filter.output.result_contract import build_search_results_contract
from tool_runtime_core import create_runtime_context


def _policy(settings: dict[str, object], physical: int, logical: int):
    return resolve_resource_policy(
        settings,
        topology=CpuTopology(physical, logical, "validator"),
    )


def _validate_policy_matrix() -> None:
    expected = [
        (2, 4, 1, 2),
        (4, 8, 1, 4),
        (6, 12, 2, 4),
        (8, 16, 3, 4),
        (12, 24, 4, 4),
    ]
    for physical, logical, processes, readers in expected:
        policy = _policy(
            {
                "processing_mode": PROCESSING_MODE_AUTOMATIC,
                "resource_profile": RESOURCE_PROFILE_BALANCED,
            },
            physical,
            logical,
        )
        assert policy.analysis_processes == processes, (physical, policy)
        assert policy.reader_workers == readers, (physical, policy)
        assert policy.reserved_system_cores >= 1
        assert policy.analysis_processes <= policy.available_physical_cores
        assert policy.max_pending_batches == policy.analysis_processes * 2

    low = _policy(
        {"processing_mode": PROCESSING_MODE_AUTOMATIC, "resource_profile": RESOURCE_PROFILE_LOW},
        8,
        16,
    )
    high = _policy(
        {"processing_mode": PROCESSING_MODE_AUTOMATIC, "resource_profile": RESOURCE_PROFILE_HIGH},
        8,
        16,
    )
    assert low.analysis_processes == 1
    assert low.reader_workers == 2
    assert high.analysis_processes > low.analysis_processes

    manual = _policy(
        {
            "processing_mode": PROCESSING_MODE_MANUAL,
            "resource_profile": RESOURCE_PROFILE_BALANCED,
            "manual_analysis_processes": 99,
            "manual_reader_workers": 99,
            "manual_reserved_cores": 2,
            "manual_max_pending_batches": 99,
        },
        6,
        12,
    )
    assert manual.manual_override
    assert manual.analysis_processes == 4
    assert manual.reader_workers == 8
    assert manual.max_pending_batches == 16


def _build_state(root: Path) -> SearchFormState:
    return SearchFormState(
        mode="Carpeta",
        path=str(root),
        search_text="administracion",
        category="Ninguna",
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        source="resource_policy_validator",
    )


def _validate_pipeline_and_contract() -> dict[str, object]:
    original_get_settings = scan_pipeline.get_settings
    original_batch_items = scan_pipeline.PROCESS_BATCH_MAX_ITEMS
    original_batch_chars = scan_pipeline.PROCESS_BATCH_MAX_CONTENT_CHARS
    previous_mode = os.environ.get("SMARTFILTER_CPU_ANALYSIS")
    settings = {
        "processing_mode": PROCESSING_MODE_MANUAL,
        "resource_profile": RESOURCE_PROFILE_BALANCED,
        "manual_analysis_processes": 2,
        "manual_reader_workers": 4,
        "manual_reserved_cores": 2,
        "manual_max_pending_batches": 4,
        "performance_monitor_enabled": True,
        "performance_timeline_enabled": True,
        "performance_sample_interval_seconds": 0.5,
        "performance_timeline_interval_seconds": 5.0,
        "ignored_folder_keywords": "",
        "ignored_file_keywords": "",
        "ignored_folder_paths": [],
        "ignored_file_paths": [],
        "broad_scan_safe_enabled": True,
    }
    # Manual values are upper bounds. On small VMs the production policy must
    # reduce them to the detected CPU topology instead of oversubscribing it.
    expected_policy = resolve_resource_policy(settings)
    try:
        scan_pipeline.get_settings = lambda: dict(settings)
        # Generate many small batches so the producer must obey backpressure.
        scan_pipeline.PROCESS_BATCH_MAX_ITEMS = 2
        scan_pipeline.PROCESS_BATCH_MAX_CONTENT_CHARS = 128 * 1024
        os.environ["SMARTFILTER_CPU_ANALYSIS"] = "always"

        with tempfile.TemporaryDirectory(prefix="smartfilter_resource_policy_") as temp:
            root = Path(temp)
            paragraph = ("administracion y documentacion operativa " * 4000).strip()
            for index in range(96):
                (root / f"documento_{index:03d}.txt").write_text(
                    f"{paragraph}\nlinea final {index}",
                    encoding="utf-8",
                )

            summary = run_search(_build_state(root))
            stats = summary.scan_stats
            performance = dict(stats.get("performance") or {})
            policy = dict(performance.get("resource_policy") or {})
            pipeline = dict(performance.get("pipeline") or {})
            runtime = dict(performance.get("runtime") or {})

            assert stats["analysis_backend"] == "spawn_process_pool"
            assert stats["analysis_processes_count"] == expected_policy.analysis_processes
            assert stats["reader_workers_count"] == expected_policy.reader_workers
            assert pipeline["max_pending_batches"] == expected_policy.max_pending_batches
            assert pipeline["peak_pending_batches"] <= expected_policy.max_pending_batches
            assert pipeline["pending_limit_respected"] is True
            assert stats["analysis_batches_submitted_count"] > 4
            assert stats["analysis_batches_completed_count"] == stats["analysis_batches_submitted_count"]
            assert stats["analysis_batches_failed_count"] == 0
            assert policy["manual_override"] is True
            assert policy["active_analysis_processes"] == expected_policy.analysis_processes
            assert policy["active_reader_workers"] == expected_policy.reader_workers
            assert policy["physical_cores"] == expected_policy.physical_cores
            assert policy["logical_cores"] == expected_policy.logical_cores
            assert runtime["backend"] == "psutil_process_tree"
            assert runtime["samples_count"] >= 1
            assert "cpu" in runtime and "memory" in runtime and "phases" in runtime
            assert runtime["memory"]["total_peak_mb"] > 0
            assert runtime["cpu"]["children_average_cores"] > 0.05, runtime["cpu"]
            assert runtime["cpu"]["children_peak_cores"] > 0.10, runtime["cpu"]
            assert not any(
                detail.get("code") == "cpu_parallel_low_utilization"
                for detail in summary.error_details
            ), summary.error_details

            runtime_context = create_runtime_context(
                tool_name="Smart Filter",
                tool_version="1.0.24-dev",
                base_dir=root,
            )
            contract = build_search_results_contract(
                summary=summary,
                runtime=runtime_context,
                cli_options={"validator": True},
            )
            assert (
                contract["data"]["performance"]["pipeline"]["max_pending_batches"]
                == expected_policy.max_pending_batches
            )
            assert contract["summary"]["resource_profile"] == RESOURCE_PROFILE_BALANCED
            json.dumps(contract, ensure_ascii=False)

            return {
                "processes": stats["analysis_processes_count"],
                "readers": stats["reader_workers_count"],
                "peak_pending": pipeline["peak_pending_batches"],
                "pending_limit": pipeline["max_pending_batches"],
                "physical_cores": expected_policy.physical_cores,
                "logical_cores": expected_policy.logical_cores,
                "samples": runtime["samples_count"],
                "cpu_peak_cores": runtime["cpu"]["smartfilter_peak_cores"],
                "children_average_cores": runtime["cpu"]["children_average_cores"],
                "children_peak_cores": runtime["cpu"]["children_peak_cores"],
                "memory_peak_mb": runtime["memory"]["total_peak_mb"],
            }
    finally:
        scan_pipeline.get_settings = original_get_settings
        scan_pipeline.PROCESS_BATCH_MAX_ITEMS = original_batch_items
        scan_pipeline.PROCESS_BATCH_MAX_CONTENT_CHARS = original_batch_chars
        if previous_mode is None:
            os.environ.pop("SMARTFILTER_CPU_ANALYSIS", None)
        else:
            os.environ["SMARTFILTER_CPU_ANALYSIS"] = previous_mode


def main() -> int:
    _validate_policy_matrix()
    metrics = _validate_pipeline_and_contract()
    print("RESOURCE_POLICY_PERFORMANCE_OK")
    print(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
