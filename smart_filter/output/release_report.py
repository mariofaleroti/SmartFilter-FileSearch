from __future__ import annotations

from pathlib import Path
from typing import Any

from json_contract_core import create_result_contract, validate_contract, write_json_file

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.output.tool_manifest import CLI_EXECUTABLE_NAME, GUI_EXECUTABLE_NAME


def _relative_files(release_dir: Path) -> list[str]:
    if not release_dir.exists():
        return []
    return sorted(str(path.relative_to(release_dir)).replace("\\", "/") for path in release_dir.rglob("*") if path.is_file())


def _release_checks(release_dir: Path) -> dict[str, Any]:
    files = set(_relative_files(release_dir))
    return {
        "release_dir_exists": release_dir.is_dir(),
        "manifest_exists": "tool_manifest.json" in files,
        "settings_exists": "data/settings.json" in files,
        "categories_exists": "data/categories.json" in files,
        "assets_dir_exists": (release_dir / "assets").is_dir(),
        "gui_executable_exists": (release_dir / GUI_EXECUTABLE_NAME).is_file(),
        "cli_executable_exists": (release_dir / CLI_EXECUTABLE_NAME).is_file(),
        "development_garbage_absent": not any(
            part in {"build", "dist", "__pycache__", ".git", ".venv", "runtime", "output"}
            for path in files
            for part in Path(path).parts
        ),
    }


def build_release_report(
    *,
    release_dir: str | Path,
    build_executables_requested: bool = False,
    pyinstaller_available: bool = False,
    copied_files_count: int = 0,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    release = Path(release_dir).expanduser().resolve()
    checks = _release_checks(release)
    files = _relative_files(release)
    errors = list(errors or [])

    final_exe_ready = checks["gui_executable_exists"] and checks["cli_executable_exists"]
    status = "ready" if final_exe_ready and not errors else "prepared_without_executables"
    if errors:
        status = "completed_with_errors"

    contract = create_result_contract(
        result_type="smartfilter_release_build_report",
        tool_name=APP_NAME,
        module_name="ReleaseBuilder",
        extra_meta={"tool_version": APP_VERSION},
        summary={
            "status": status,
            "release_dir": str(release),
            "files_count": len(files),
            "copied_files_count": copied_files_count,
            "gui_executable_exists": checks["gui_executable_exists"],
            "cli_executable_exists": checks["cli_executable_exists"],
            "diagnostics_count": 1 if not final_exe_ready else 0,
            "errors_count": len(errors),
        },
        report_brief={
            "title": "Smart Filter - Informe de construcción",
            "description": "Validación del paquete limpio release/SmartFilter y estado de ejecutables.",
            "recommendations": [
                "Generar ejecutables en Windows con tools/build_release.py --build-exe.",
                "Mantener data/settings.json y data/categories.json como archivos externos portables.",
                "No copiar build, dist, __pycache__, .git, output ni runtime al release final.",
            ],
        },
        data={
            "release": {
                "directory": str(release),
                "folder_convention": "release/SmartFilter/",
                "build_executables_requested": build_executables_requested,
                "pyinstaller_available": pyinstaller_available,
                "final_executable_release_ready": final_exe_ready,
            },
            "checks": checks,
            "files": files,
            "expected_final_items": [
                GUI_EXECUTABLE_NAME,
                CLI_EXECUTABLE_NAME,
                "tool_manifest.json",
                "data/settings.json",
                "data/categories.json",
                "assets/",
            ],
            "sharedcode_usage": {
                "release_core": "clean release directory / copy payload",
                "json_contract_core": "manifest and release snapshot contracts",
                "date_time_core": "timestamps inherited through contracts/services",
            },
        },
        diagnostics=[] if final_exe_ready else [
            {
                "level": "warning",
                "code": "SMARTFILTER_RELEASE_EXE_PENDING",
                "message": "La estructura de release está preparada, pero faltan SmartFilter.exe y/o SmartFilterCLI.exe.",
                "context": {
                    "reason": "Este paquete fuente no genera ejecutables Linux; compilar en Windows con PyInstaller.",
                    "command": "python tools/build_release.py --build-exe",
                },
            }
        ],
        errors=errors,
    )
    validation = validate_contract(contract, source=str(release), strict_schema_version=True)
    if not validation.is_valid:
        contract["errors"].extend(
            {
                "code": "SMARTFILTER_RELEASE_REPORT_INVALID",
                "message": issue.message,
                "context": {"path": issue.path, "code": issue.code},
            }
            for issue in validation.issues
        )
        contract["summary"]["errors_count"] = len(contract["errors"])
    return contract


def write_release_report(
    *,
    release_dir: str | Path,
    output_path: str | Path,
    build_executables_requested: bool = False,
    pyinstaller_available: bool = False,
    copied_files_count: int = 0,
    errors: list[dict[str, Any]] | None = None,
) -> Path:
    contract = build_release_report(
        release_dir=release_dir,
        build_executables_requested=build_executables_requested,
        pyinstaller_available=pyinstaller_available,
        copied_files_count=copied_files_count,
        errors=errors,
    )
    return write_json_file(contract, output_path)
