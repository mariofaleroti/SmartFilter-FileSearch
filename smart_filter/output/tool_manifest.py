from __future__ import annotations

from pathlib import Path
from typing import Any

from json_contract_core import create_contract, validate_contract, write_json_file

from smart_filter.bootstrap import (
    REQUIRED_SHAREDCODE_VERSION,
    SHAREDCODE_DISTRIBUTION,
    SHAREDCODE_REPOSITORY_URL,
)
from smart_filter.app_info import (
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_ID,
    APP_NAME,
    APP_RELEASE_CHANNEL,
    APP_RELEASE_STATUS,
    APP_VERSION,
)


RELEASE_FOLDER_NAME = "SmartFilter"
GUI_EXECUTABLE_NAME = "SmartFilter.exe"
CLI_EXECUTABLE_NAME = "SmartFilterCLI.exe"
MANIFEST_NAME = "tool_manifest.json"


def build_tool_manifest(*, include_build_status: bool = True) -> dict[str, Any]:
    """Build Smart Filter tool manifest for Toolkit/external integration."""
    data: dict[str, Any] = {
        "entrypoints": {
            "gui": {
                "enabled": True,
                "executable": GUI_EXECUTABLE_NAME,
                "description": "Interfaz visual para búsqueda manual de archivos.",
            },
            "cli": {
                "enabled": True,
                "executable": CLI_EXECUTABLE_NAME,
                "description": "Interfaz de consola para automatización e integración con Toolkit.",
                "default_args": [
                    "--folder", "{input_dir}",
                    "--query", "{query}",
                    "--json-output", "output/smartfilter_results.json",
                ],
            },
        },
        "paths": {
            "release_dir": RELEASE_FOLDER_NAME,
            "data_dir": "data",
            "assets_dir": "assets",
            "output_dir": "output",
            "runtime_dir": "runtime",
            "logs_dir": "runtime/logs",
            "categories_file": "data/categories.json",
            "settings_file": "data/settings.json",
            "default_json_output": "output/smartfilter_results.json",
        },
        "required_items": [
            {
                "id": "gui_executable",
                "kind": "file",
                "path": GUI_EXECUTABLE_NAME,
                "required": True,
                "description": "Ejecutable principal de la interfaz visual.",
            },
            {
                "id": "cli_executable",
                "kind": "file",
                "path": CLI_EXECUTABLE_NAME,
                "required": True,
                "description": "Ejecutable CLI para automatización.",
            },
            {
                "id": "data_dir",
                "kind": "directory",
                "path": "data",
                "required": True,
                "description": "Carpeta de configuración y categorías.",
            },
            {
                "id": "settings_file",
                "kind": "file",
                "path": "data/settings.json",
                "required": True,
                "description": "Configuración portable de Smart Filter.",
            },
            {
                "id": "categories_file",
                "kind": "file",
                "path": "data/categories.json",
                "required": True,
                "description": "Base de categorías inteligentes.",
            },
            {
                "id": "assets_dir",
                "kind": "directory",
                "path": "assets",
                "required": False,
                "description": "Recursos visuales de la aplicación.",
            },
        ],
        "capabilities": {
            "supports_gui": True,
            "supports_cli": True,
            "supports_automation": True,
            "supports_json_output": True,
            "supports_csv_export": True,
            "supports_categories": True,
            "supports_discard_filters": True,
            "supports_file_content_search": True,
            "supports_highlight_view": True,
            "supports_portable_mode": True,
            "uses_sharedcode": True,
        },
        "sharedcode": {
            "distribution": SHAREDCODE_DISTRIBUTION,
            "version": REQUIRED_SHAREDCODE_VERSION,
            "repository": SHAREDCODE_REPOSITORY_URL,
            "required_at_build_time": True,
            "required_at_runtime": False,
            "runtime_model": "SharedCode packages are bundled into the PyInstaller executables; data remains external.",
            "cores_used": [
                "GuiCore",
                "ConfigCore",
                "JsonContractCore",
                "DateTimeCore",
                "FileScanCore",
                "CliCore",
                "ToolRuntimeCore",
                "LoggingCore",
                "PlatformCore",
                "ReleaseCore",
                "RenderCore",
            ],
        },
        "toolkit_menu": {
            "enabled": True,
            "parent_menu_id": "tools",
            "menu_group": "Herramientas externas",
            "menu_label": APP_DISPLAY_NAME,
            "description": "Busca archivos por nombre, contenido y categorías inteligentes.",
            "default_action": "open_gui",
        },
        "actions": [
            {
                "id": "open_gui",
                "label": "Abrir Smart Filter",
                "description": "Abre la interfaz visual de Smart Filter Archivos.",
                "mode": "gui",
                "action_type": "launch_entrypoint",
                "entrypoint": "gui",
                "requires_parameters": False,
            },
            {
                "id": "run_cli_search",
                "label": "Ejecutar búsqueda CLI",
                "description": "Ejecuta una búsqueda automatizada y genera JSON estándar.",
                "mode": "cli",
                "action_type": "launch_entrypoint",
                "entrypoint": "cli",
                "requires_parameters": True,
            },
            {
                "id": "open_data_folder",
                "label": "Abrir carpeta de configuración",
                "description": "Abre la carpeta data de Smart Filter.",
                "mode": "toolkit",
                "action_type": "open_declared_path",
                "target": "paths.data_dir",
                "requires_parameters": False,
            },
        ],
        "health_check": {
            "enabled": True,
            "checks": [
                "manifest_valid",
                "required_items_exist",
                "enabled_entrypoints_exist",
                "settings_contract_valid",
                "categories_contract_valid",
                "menu_actions_valid",
            ],
        },
        "release": {
            "portable": True,
            "channel": APP_RELEASE_CHANNEL,
            "status": APP_RELEASE_STATUS,
            "requires_python_installed": False,
            "requires_sharedcode_folder_at_runtime": False,
            "execution_model": "portable_pyinstaller_onefile",
            "folder_convention": "release/SmartFilter/",
            "exported_items": [
                GUI_EXECUTABLE_NAME,
                CLI_EXECUTABLE_NAME,
                "tool_manifest.json",
                "data/",
                "assets/",
            ],
            "build_script": "tools/build_release.py",
            "gui_spec": "SmartFilter.spec",
            "cli_spec": "SmartFilterCLI.spec",
        },
    }

    if include_build_status:
        data["release"]["build_status"] = {
            "source_package_prepared": True,
            "executables_required_for_final_release": True,
            "note": "Los .exe se generan en Windows con PyInstaller mediante tools/build_release.py --build-exe.",
        }

    return create_contract(
        file_type="manifest",
        subtype_key="manifest_type",
        subtype_value="tool_manifest",
        tool_name=APP_NAME,
        module_name="ToolManifest",
        extra_meta={
            "tool_id": APP_ID,
            "tool_type": "external_tool",
            "tool_version": APP_VERSION,
        },
        summary={
            "name": APP_NAME,
            "display_name": APP_DISPLAY_NAME,
            "version": APP_VERSION,
            "status": APP_RELEASE_STATUS,
            "category": "files",
            "description": APP_DESCRIPTION,
            "entrypoints_count": 2,
            "actions_count": 3,
            "required_items_count": 6,
            "diagnostics_count": 0,
            "errors_count": 0,
        },
        report_brief={
            "title": APP_DISPLAY_NAME,
            "description": "Búsqueda inteligente de archivos con GUI, CLI, categorías, readers y contrato JSON estándar.",
            "menu_label": APP_DISPLAY_NAME,
        },
        data=data,
        diagnostics=[],
        errors=[],
    )


def write_tool_manifest(output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    contract = build_tool_manifest()
    validation = validate_contract(contract, source=str(path), strict_schema_version=True)
    if not validation.is_valid:
        messages = "; ".join(issue.message for issue in validation.issues)
        raise ValueError(f"Tool manifest inválido: {messages}")
    return write_json_file(contract, path)
