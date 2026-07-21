from __future__ import annotations

import argparse
import json
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.bootstrap import ensure_sharedcode_on_path
from smart_filter.app_info import APP_VERSION

ensure_sharedcode_on_path()

from config_core import write_json_file
from release_core import clean_release_dir, copy_release_files
from smart_filter.output.release_report import write_release_report
from smart_filter.output.tool_manifest import (
    CLI_EXECUTABLE_NAME,
    GUI_EXECUTABLE_NAME,
    MANIFEST_NAME,
    RELEASE_FOLDER_NAME,
    write_tool_manifest,
)
from smart_filter.paths import ASSETS_DIR, OUTPUT_DIR
from smart_filter.services.category_service import build_category_contract, build_default_category_data
from smart_filter.services.settings_service import build_settings_contract, get_default_settings_data

RELEASE_ROOT = PROJECT_ROOT / "release"
RELEASE_DIR = RELEASE_ROOT / RELEASE_FOLDER_NAME
BUILD_REPORT_PATH = OUTPUT_DIR / "smartfilter_release_build_report.json"


def _pyinstaller_available() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def _run_pyinstaller(spec_name: str) -> None:
    command = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_name]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _copy_executable(source_name: str, target_name: str, errors: list[dict]) -> None:
    candidates = [
        PROJECT_ROOT / "dist" / source_name,
        PROJECT_ROOT / "dist" / f"{source_name}.exe",
        PROJECT_ROOT / "dist" / source_name / f"{source_name}.exe",
        PROJECT_ROOT / "dist" / source_name / source_name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            target = RELEASE_DIR / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)
            return
    errors.append(
        {
            "code": "SMARTFILTER_EXECUTABLE_NOT_FOUND",
            "message": f"No se encontró el ejecutable generado para {source_name}.",
            "context": {"searched_paths": [str(path) for path in candidates]},
        }
    )


def _write_factory_release_data() -> int:
    """Create a clean user data directory from immutable factory templates."""

    data_dir = RELEASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json_file(
        build_settings_contract(get_default_settings_data()),
        data_dir / "settings.json",
    )
    write_json_file(
        build_category_contract(build_default_category_data()),
        data_dir / "categories.json",
    )
    return 2


def _validate_factory_release_data(errors: list[dict]) -> None:
    settings_path = RELEASE_DIR / "data" / "settings.json"
    categories_path = RELEASE_DIR / "data" / "categories.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if str(settings.get("meta", {}).get("tool_version") or "") != APP_VERSION:
            raise ValueError("La versión de settings.json no coincide con APP_VERSION.")
        data = settings.get("data", {})
        state = data.get("state", {})
        history = data.get("history", {})
        filters = data.get("filters", {})
        experience = data.get("experience", {})
        expected_empty = {
            "last_folder": "",
            "last_file": "",
            "last_search_text": "",
            "last_context_filter": "",
            "last_category": "Ninguna",
            "last_discard_filter": "Ninguna",
        }
        invalid_state = {key: state.get(key) for key, value in expected_empty.items() if state.get(key) != value}
        if invalid_state or history.get("search_history") or filters.get("saved_discard_terms"):
            raise ValueError(f"Estado de usuario presente: {invalid_state}")
        if filters.get("ignored_folder_paths") or filters.get("ignored_file_paths"):
            raise ValueError("El release contiene rutas de exclusión personales.")
        if experience.get("save_search_history") or experience.get("remember_last_location") or experience.get("remember_last_search_settings"):
            raise ValueError("Las preferencias de fábrica permiten persistir datos de búsqueda sensibles.")

        categories = json.loads(categories_path.read_text(encoding="utf-8"))
        if str(categories.get("meta", {}).get("tool_version") or "") != APP_VERSION:
            raise ValueError("La versión de categories.json no coincide con APP_VERSION.")
        category_map = categories.get("data", {}).get("categories", {})
        forbidden_categories = {"prueba", "ventas_prueba_real"} & set(category_map)
        forbidden_terms = {
            str(term).strip().casefold()
            for record in category_map.values()
            if isinstance(record, dict)
            for term in record.get("exclude_terms", [])
        }
        if forbidden_categories or "pepe" in forbidden_terms:
            raise ValueError(
                f"Categorías o términos de prueba presentes: {sorted(forbidden_categories)}"
            )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        errors.append(
            {
                "code": "SMARTFILTER_RELEASE_FACTORY_DATA_INVALID",
                "message": "El release no contiene un estado de fábrica limpio.",
                "context": {"error": str(error)},
            }
        )


def _validate_built_cli_executable(errors: list[dict]) -> None:
    executable = RELEASE_DIR / CLI_EXECUTABLE_NAME
    if not executable.is_file():
        errors.append(
            {
                "code": "SMARTFILTER_PORTABLE_SELF_CHECK_EXECUTABLE_MISSING",
                "message": "No se encontró SmartFilterCLI para validar el portable.",
                "context": {"path": str(executable)},
            }
        )
        return

    completed = subprocess.run(
        [str(executable), "--portable-self-check"],
        cwd=RELEASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined_output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
    )
    expected_markers = (
        f"SMARTFILTER_PORTABLE_SELF_CHECK_OK version={APP_VERSION}",
        "grouped_occurrences=2",
        "highlight_xlsx=ok",
        "highlight_html=ok",
        "section_scope=ok",
        "factory_defaults=ok",
    )
    missing_markers = [marker for marker in expected_markers if marker not in combined_output]
    if completed.returncode != 0 or missing_markers:
        errors.append(
            {
                "code": "SMARTFILTER_PORTABLE_SELF_CHECK_FAILED",
                "message": "El ejecutable portable no superó la autoprueba del motor.",
                "context": {
                    "returncode": completed.returncode,
                    "expected_markers": list(expected_markers),
                    "missing_markers": missing_markers,
                    "output": combined_output[-4000:],
                },
            }
        )



def _validate_release_payload(errors: list[dict], *, require_executables: bool) -> None:
    required = [
        RELEASE_DIR / MANIFEST_NAME,
        RELEASE_DIR / "data" / "settings.json",
        RELEASE_DIR / "data" / "categories.json",
        RELEASE_DIR / "assets",
    ]
    if require_executables:
        required.extend(
            [
                RELEASE_DIR / GUI_EXECUTABLE_NAME,
                RELEASE_DIR / CLI_EXECUTABLE_NAME,
            ]
        )

    missing = [str(path.relative_to(RELEASE_DIR)) for path in required if not path.exists()]
    if missing:
        errors.append(
            {
                "code": "SMARTFILTER_RELEASE_REQUIRED_ITEM_MISSING",
                "message": "El release no contiene todos los elementos obligatorios.",
                "context": {"missing_items": missing},
            }
        )
    else:
        _validate_factory_release_data(errors)

    forbidden_names = {"README_RELEASE.md", "README.txt", "README.md"}
    forbidden_found = [
        str(path.relative_to(RELEASE_DIR)).replace("\\", "/")
        for path in RELEASE_DIR.rglob("*")
        if path.is_file() and path.name in forbidden_names
    ]
    if forbidden_found:
        errors.append(
            {
                "code": "SMARTFILTER_RELEASE_USER_DOCUMENTATION_UNEXPECTED",
                "message": "El portable no debe duplicar documentación; la información de uso vive en Ayuda y Acerca de.",
                "context": {"files": forbidden_found},
            }
        )

    manifest_path = RELEASE_DIR / MANIFEST_NAME
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_version = str(manifest.get("summary", {}).get("version") or "").strip()
            if manifest_version != APP_VERSION:
                errors.append(
                    {
                        "code": "SMARTFILTER_RELEASE_VERSION_MISMATCH",
                        "message": "La versión del manifest no coincide con APP_VERSION.",
                        "context": {"app_version": APP_VERSION, "manifest_version": manifest_version},
                    }
                )
        except (OSError, ValueError, TypeError) as error:
            errors.append(
                {
                    "code": "SMARTFILTER_RELEASE_MANIFEST_READ_FAILED",
                    "message": "No se pudo comprobar el manifest del release.",
                    "context": {"error": str(error)},
                }
            )


def prepare_release(*, build_executables: bool = False) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_release_dir(RELEASE_DIR)

    copied_files_count = 0
    errors: list[dict] = []

    copied_files_count += _write_factory_release_data()
    if ASSETS_DIR.exists():
        result = copy_release_files(ASSETS_DIR, RELEASE_DIR / "assets", clean=False)
        copied_files_count += result.files_count
        errors.extend(result.errors)
    else:
        errors.append(
            {
                "code": "SMARTFILTER_SOURCE_ASSETS_MISSING",
                "message": "No se encontró la carpeta assets del proyecto fuente.",
                "context": {"path": str(ASSETS_DIR)},
            }
        )

    write_tool_manifest(RELEASE_DIR / MANIFEST_NAME)

    pyinstaller_available = _pyinstaller_available()
    if build_executables:
        if not pyinstaller_available:
            errors.append(
                {
                    "code": "SMARTFILTER_PYINSTALLER_MISSING",
                    "message": "PyInstaller no está instalado; no se pueden generar ejecutables.",
                    "context": {"install_command": "python -m pip install pyinstaller"},
                }
            )
        else:
            try:
                _run_pyinstaller("SmartFilter.spec")
                _run_pyinstaller("SmartFilterCLI.spec")
                _copy_executable("SmartFilter", GUI_EXECUTABLE_NAME, errors)
                _copy_executable("SmartFilterCLI", CLI_EXECUTABLE_NAME, errors)
                if not errors:
                    _validate_built_cli_executable(errors)
            except subprocess.CalledProcessError as error:
                errors.append(
                    {
                        "code": "SMARTFILTER_PYINSTALLER_FAILED",
                        "message": "Falló PyInstaller al generar ejecutables.",
                        "context": {"returncode": error.returncode, "command": error.cmd},
                    }
                )

    _validate_release_payload(errors, require_executables=build_executables)

    write_release_report(
        release_dir=RELEASE_DIR,
        output_path=BUILD_REPORT_PATH,
        build_executables_requested=build_executables,
        pyinstaller_available=pyinstaller_available,
        copied_files_count=copied_files_count,
        errors=errors,
    )
    if errors:
        codes = ", ".join(str(item.get("code") or "UNKNOWN") for item in errors)
        raise RuntimeError(f"El release no superó la validación portable: {codes}")
    return RELEASE_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Arma release limpio de Smart Filter.")
    parser.add_argument(
        "--build-exe",
        action="store_true",
        help="Generar SmartFilter.exe y SmartFilterCLI.exe con PyInstaller antes de preparar el release.",
    )
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Imprimir solamente la ruta del release generado.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    release_dir = prepare_release(build_executables=args.build_exe)
    if args.print_path:
        print(release_dir)
    else:
        print(f"Release preparado: {release_dir}")
        print(f"Informe de construcción: {BUILD_REPORT_PATH}")
        if not args.build_exe:
            print("Nota: ejecutables no generados. Usar --build-exe en Windows con PyInstaller instalado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
