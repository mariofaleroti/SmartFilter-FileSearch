from __future__ import annotations

from pathlib import Path

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.output.actions_snapshot import write_step7_actions_snapshot
from smart_filter.output.architecture_contract import write_architecture_contract
from smart_filter.output.cli_snapshot import write_step9_cli_snapshot
from smart_filter.output.config_snapshot import write_config_snapshot
from smart_filter.output.content_snapshot import write_step6_content_snapshot
from smart_filter.output.gui_snapshot import write_gui_snapshot
from smart_filter.output.scan_snapshot import write_step5_scan_snapshot
from smart_filter.output.search_snapshot import write_step4_search_snapshot
from smart_filter.output.windows_snapshot import write_step8_windows_snapshot
from smart_filter.paths import OUTPUT_DIR, ensure_project_directories


def write_development_snapshots(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Generate historical engineering fixtures outside the product CLI flow."""

    ensure_project_directories()
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        write_architecture_contract(output_dir / "smartfilter_sharedcode_mockup.json"),
        write_config_snapshot(output_dir / "smartfilter_step2_config_snapshot.json"),
        write_gui_snapshot(output_dir / "smartfilter_step3_gui_snapshot.json"),
        write_step4_search_snapshot(output_dir / "smartfilter_step4_search_engine_snapshot.json"),
        write_step5_scan_snapshot(output_dir / "smartfilter_step5_scan_pipeline_snapshot.json"),
        write_step6_content_snapshot(output_dir / "smartfilter_step6_reader_pipeline_snapshot.json"),
        write_step7_actions_snapshot(output_dir / "smartfilter_step7_results_actions_snapshot.json"),
        write_step8_windows_snapshot(output_dir / "smartfilter_step8_product_windows_snapshot.json"),
        write_step9_cli_snapshot(output_dir / "smartfilter_step9_cli_results_snapshot.json"),
    ]


def main() -> int:
    for path in write_development_snapshots():
        print(f"Snapshot de desarrollo generado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
