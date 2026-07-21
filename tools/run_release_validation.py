from __future__ import annotations

import subprocess
import sys

VALIDATORS = (
    "tools.validate_public_repository",
    "tools.validate_cli_product_behavior",
    "tools.validate_factory_defaults",
    "tools.validate_about_release_information",
    "tools.validate_documentation_release_prep",
    "tools.validate_integrated_help_center",
    "tools.validate_category_portability_safety",
    "tools.validate_category_target_fields_scope",
    "tools.validate_category_section_detection",
    "tools.validate_broad_scan_safe",
    "tools.validate_integrated_match_pipeline",
    "tools.validate_reader_metrics",
    "tools.validate_scan_issue_rollup",
    "tools.validate_metric_summary_semantics",
    "tools.validate_metric_cards_readability",
    "tools.validate_cpu_parallel_analysis",
    "tools.validate_performance_monitor_child_cpu",
    "tools.validate_resource_policy_performance",
    "tools.validate_excel_original_open",
    "tools.validate_pdf_original_open",
    "tools.validate_highlight_excel_control_characters",
    "tools.validate_html_highlight_portable_flow",
    "tools.validate_icon_all_windows",
    "tools.validate_icon_secondary_windows_fix",
    "tools.validate_pyinstaller_customtkinter_fix",
    "tools.validate_portable_self_check",
    "tools.validate_portable_build_integrity",
)


def main() -> int:
    for module_name in VALIDATORS:
        print(f"== {module_name} ==", flush=True)
        completed = subprocess.run([sys.executable, "-m", module_name], check=False)
        if completed.returncode != 0:
            print(f"RELEASE_VALIDATION_FAILED module={module_name} returncode={completed.returncode}")
            return completed.returncode
    print(f"RELEASE_VALIDATION_OK validators={len(VALIDATORS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
