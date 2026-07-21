from __future__ import annotations

from pathlib import Path

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.app_info import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    powershell = (ROOT / "BUILD_PORTABLE_WINDOWS.ps1").read_text(encoding="utf-8")
    cmd = (ROOT / "BUILD_WINDOWS_RELEASE.cmd").read_text(encoding="utf-8")
    builder = (ROOT / "tools" / "build_release.py").read_text(encoding="utf-8")
    archive_validator = (ROOT / "tools" / "validate_portable_archive.py").read_text(encoding="utf-8")
    cli_runner = (ROOT / "smart_filter" / "cli" / "runner.py").read_text(encoding="utf-8")
    manifest_source = (ROOT / "smart_filter" / "output" / "tool_manifest.py").read_text(encoding="utf-8")
    spec = (ROOT / "SmartFilter.spec").read_text(encoding="utf-8")
    cli_spec = (ROOT / "SmartFilterCLI.spec").read_text(encoding="utf-8")
    paths_source = (ROOT / "smart_filter" / "paths.py").read_text(encoding="utf-8")
    factory_loader = (ROOT / "smart_filter" / "factory_defaults.py").read_text(encoding="utf-8")

    for token in (
        "Set-Location $PSScriptRoot",
        "$LASTEXITCODE",
        "Invoke-PythonChecked",
        "Remove-Item \".\\release\"",
        "--portable-self-check",
        "tools.validate_portable_archive",
        "SmartFilter_Portable_v$($appVersion).zip",
        "tools.validate_factory_defaults",
        r"resources\defaults\settings.json",
        r"resources\defaults\categories.json",
    ):
        assert token in powershell, token

    assert "pip install --upgrade pip" not in powershell
    assert "requirements-dev.txt" in powershell
    assert "SharedCode Cores: $sharedCodeVersion (paquete instalado)" in powershell
    assert "SMARTFILTER_SHAREDCODE_DIR" not in powershell
    assert "BUILD_PORTABLE_WINDOWS.ps1" in cmd
    assert "python -m pip install" not in cmd

    assert "_write_release_readme" not in builder
    assert "_write_factory_release_data" in builder
    assert "DATA_DIR" not in builder
    assert "SMARTFILTER_RELEASE_FACTORY_DATA_INVALID" in builder
    assert "README_RELEASE =" not in builder
    assert 'forbidden_names = {"README_RELEASE.md", "README.txt", "README.md"}' in builder
    assert "_validate_release_payload" in builder
    assert "--portable-self-check" in builder
    assert "SMARTFILTER_PORTABLE_SELF_CHECK_OK" in builder
    assert "--portable-self-check" in cli_runner
    assert "README_RELEASE.md" not in manifest_source

    for marker in (
        "REQUIRED_ENTRIES",
        "FORBIDDEN_NAMES",
        "APP_VERSION",
        "PORTABLE_ARCHIVE_OK",
    ):
        assert marker in archive_validator, marker

    assert "smart_filter.engine.candidate_analysis" in spec
    assert "smart_filter.services.result_action_service" in spec
    for spec_source in (spec, cli_spec):
        assert 'render_spec = find_spec("render_core")' in spec_source
        assert 'render_template_root = render_package_root / "templates"' in spec_source
        assert '(str(render_template_root), "render_core/templates")' in spec_source
        assert "SHAREDCODE_ROOT" not in spec_source
        assert "FileNotFoundError" in spec_source
        assert 'factory_defaults_root = PROJECT_ROOT / "resources" / "defaults"' in spec_source
        assert '(str(factory_defaults_root), "resources/defaults")' in spec_source

    assert "FACTORY_SETTINGS_PATH" in paths_source
    assert "FACTORY_CATEGORIES_PATH" in paths_source
    assert "_MEIPASS" in paths_source
    assert "load_factory_contract_data" in factory_loader
    assert (ROOT / "resources" / "defaults" / "settings.json").is_file()
    assert (ROOT / "resources" / "defaults" / "categories.json").is_file()
    assert (ROOT / "assets" / "app_icon.ico").is_file()

    assert "highlight_html=ok" in cli_runner
    assert "section_scope=ok" in cli_runner
    assert "factory_defaults=ok" in cli_runner
    assert APP_VERSION

    print("PORTABLE_BUILD_INTEGRITY_OK")
    print(f"VERSION_OK {APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
