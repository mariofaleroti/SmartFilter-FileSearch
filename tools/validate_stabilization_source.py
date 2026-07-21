from __future__ import annotations

import json
from pathlib import Path

from smart_filter.app_info import APP_RELEASE_STATUS, APP_VERSION, get_release_label, get_release_status

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    assert get_release_status("1.0.32-rc1") == "release_candidate"
    assert get_release_status("1.0.32") == "stable"
    assert get_release_label("1.0.32") == "Versión estable"
    assert APP_VERSION == "1.0.32"
    assert APP_RELEASE_STATUS == "stable"

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "Jinja2>=3.1.6" in requirements
    assert "openpyxl>=3.1.5" in requirements
    assert "sharedcode-cores @ https://github.com/mariofaleroti/SharedCode-Cores/releases/download/v1.0.0/" in requirements

    for name in ("settings.json", "categories.json"):
        factory = json.loads((ROOT / "resources" / "defaults" / name).read_text(encoding="utf-8-sig"))
        assert factory.get("data"), f"default vacío: {name}"
        runtime_path = ROOT / "data" / name
        if runtime_path.is_file():
            runtime = json.loads(runtime_path.read_text(encoding="utf-8-sig"))
            assert runtime == factory, f"data/{name} no coincide con el default limpio"

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("build/", "dist/", "release/", "runtime/", "output/", "__pycache__/", "*.pyc"):
        assert entry in gitignore, entry
    assert not (ROOT / "BUILD_PORTABLE_WINDOWS.cmd").exists()
    assert not (ROOT / "tools" / "GitQuickMenu.ps1").exists()
    assert (ROOT / "BUILD_WINDOWS_RELEASE.cmd").is_file()

    manifest_source = (ROOT / "smart_filter" / "output" / "tool_manifest.py").read_text(encoding="utf-8")
    assert '"status": APP_RELEASE_STATUS' in manifest_source
    assert '"channel": APP_RELEASE_CHANNEL' in manifest_source
    assert '"RenderCore"' in manifest_source

    cli_source = (ROOT / "smart_filter" / "cli" / "runner.py").read_text(encoding="utf-8")
    assert "parser.print_help()" in cli_source
    assert "Snapshot Paso 9" not in cli_source
    assert "--write-dev-snapshots" not in cli_source

    metric_source = (ROOT / "smart_filter" / "ui" / "metric_summary.py").read_text(encoding="utf-8")
    assert '"characters": int(scan_stats.get("content_text_chars_count") or 0)' in metric_source
    assert '"occurrences"' not in metric_source

    action_source = (ROOT / "smart_filter" / "services" / "result_action_service.py").read_text(encoding="utf-8")
    assert "_open_original_office_path(target)" in action_source
    assert 'getattr(os, "startfile", None)' in action_source

    print("STABILIZATION_SOURCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
