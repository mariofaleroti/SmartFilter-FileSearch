from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path, PurePosixPath

from smart_filter.app_info import APP_VERSION


REQUIRED_ENTRIES = {
    "SmartFilter/SmartFilter.exe",
    "SmartFilter/SmartFilterCLI.exe",
    "SmartFilter/tool_manifest.json",
    "SmartFilter/data/settings.json",
    "SmartFilter/data/categories.json",
}
FORBIDDEN_NAMES = {"README_RELEASE.md", "README.txt", "README.md"}
FORBIDDEN_PARTS = {"build", "dist", "__pycache__", ".git", ".venv", "runtime", "output"}


def validate_archive(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"No existe el ZIP portable: {path}")

    expected_name = f"SmartFilter_Portable_v{APP_VERSION}.zip"
    if path.name != expected_name:
        raise AssertionError(f"Nombre de ZIP inesperado: {path.name}; esperado: {expected_name}")

    with zipfile.ZipFile(path, "r") as archive:
        names = {name.replace("\\", "/") for name in archive.namelist() if not name.endswith("/")}
        missing = sorted(REQUIRED_ENTRIES - names)
        if missing:
            raise AssertionError(f"Faltan elementos en el ZIP: {missing}")

        unexpected_docs = sorted(name for name in names if PurePosixPath(name).name in FORBIDDEN_NAMES)
        if unexpected_docs:
            raise AssertionError(f"El portable no debe incluir README duplicado: {unexpected_docs}")

        dirty = sorted(
            name
            for name in names
            if any(part in FORBIDDEN_PARTS for part in PurePosixPath(name).parts)
        )
        if dirty:
            raise AssertionError(f"El ZIP contiene elementos de desarrollo: {dirty[:20]}")

        manifest = json.loads(archive.read("SmartFilter/tool_manifest.json").decode("utf-8"))
        manifest_version = str(manifest.get("summary", {}).get("version") or "").strip()
        if manifest_version != APP_VERSION:
            raise AssertionError(
                f"Versión del manifest inconsistente: {manifest_version}; esperado: {APP_VERSION}"
            )

        settings = json.loads(archive.read("SmartFilter/data/settings.json").decode("utf-8"))
        settings_data = settings.get("data", {})
        state = settings_data.get("state", {})
        expected_state = {
            "last_folder": "",
            "last_file": "",
            "last_search_text": "",
            "last_context_filter": "",
            "last_category": "Ninguna",
            "last_discard_filter": "Ninguna",
        }
        dirty_state = {key: state.get(key) for key, value in expected_state.items() if state.get(key) != value}
        if dirty_state:
            raise AssertionError(f"El ZIP contiene estado de usuario: {dirty_state}")
        if settings_data.get("history", {}).get("search_history"):
            raise AssertionError("El ZIP contiene historial de búsquedas.")
        if settings_data.get("filters", {}).get("saved_discard_terms"):
            raise AssertionError("El ZIP contiene términos de descarte personales.")

        categories = json.loads(archive.read("SmartFilter/data/categories.json").decode("utf-8"))
        category_map = categories.get("data", {}).get("categories", {})
        if {"prueba", "ventas_prueba_real"} & set(category_map):
            raise AssertionError("El ZIP contiene categorías de prueba.")
        for record in category_map.values():
            if "pepe" in {str(item).casefold() for item in record.get("exclude_terms", [])}:
                raise AssertionError("El ZIP contiene términos de prueba.")

    print("PORTABLE_ARCHIVE_OK")
    print(f"VERSION_OK {APP_VERSION}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida el ZIP portable final de Smart Filter.")
    parser.add_argument("archive", type=Path, help="Ruta al ZIP SmartFilter_Portable_v<versión>.zip")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    validate_archive(args.archive.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
