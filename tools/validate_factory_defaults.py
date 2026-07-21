from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.app_info import APP_VERSION
from smart_filter.domain.search_config import ALL_FILE_TYPE_OPTION, DEFAULT_CATEGORY_NAME
from smart_filter.paths import FACTORY_CATEGORIES_PATH, FACTORY_SETTINGS_PATH
import smart_filter.services.category_service as category_service
import smart_filter.services.settings_service as settings_service
from smart_filter.services.category_service import build_default_category_data
from smart_filter.services.settings_service import get_default_settings_data

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT_KEYS = {"meta", "summary", "report_brief", "data", "diagnostics", "errors"}
OFFICIAL_CATEGORY_NAMES = {
    "administracion",
    "comercial_ventas",
    "soporte_tecnico",
    "sistemas_infraestructura",
    "contabilidad_finanzas",
    "recursos_humanos",
    "compras_proveedores",
    "legal_contratos",
    "logistica_operaciones",
    "urgente_incidencias",
}


def _load(path: Path, config_type: str) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED_ROOT_KEYS <= set(document), path
    assert document["meta"]["file_type"] == "config"
    assert document["meta"]["config_type"] == config_type
    assert document["meta"]["tool_version"] == APP_VERSION
    assert isinstance(document["data"], dict)
    return document


def _validate_settings(document: dict) -> None:
    data = document["data"]
    search = data["search"]
    state = data["state"]
    experience = data["experience"]
    filters = data["filters"]

    assert search["default_analysis_mode"] == "Carpeta"
    assert search["default_category"] == DEFAULT_CATEGORY_NAME
    assert search["default_file_type"] == ALL_FILE_TYPE_OPTION
    assert search["default_file_types"] == [ALL_FILE_TYPE_OPTION]
    assert search["default_search_scope"] == "Nombre y contenido"

    assert state["last_folder"] == ""
    assert state["last_file"] == ""
    assert state["last_search_text"] == ""
    assert state["last_context_filter"] == ""
    assert state["last_category"] == DEFAULT_CATEGORY_NAME
    assert state["last_discard_filter"] == DEFAULT_CATEGORY_NAME
    assert state["last_file_types"] == [ALL_FILE_TYPE_OPTION]

    assert document["data"]["history"]["search_history"] == []
    assert filters["saved_discard_terms"] == []
    assert filters["ignored_folder_paths"] == []
    assert filters["ignored_file_paths"] == []
    assert filters["ignored_folder_keywords"] == ""
    assert filters["ignored_file_keywords"] == ""

    assert experience["save_search_history"] is False
    assert experience["remember_last_analysis_mode"] is True
    assert experience["remember_last_location"] is False
    assert experience["remember_last_search_settings"] is False

    assert data["performance"]["processing_mode"] == "Automático"
    assert data["performance"]["resource_profile"] == "Equilibrado"
    assert data["highlight"]["open_result_mode"] == "Abrir vista destacada HTML"


def _validate_categories(document: dict) -> None:
    categories = document["data"]["categories"]
    assert set(categories) == OFFICIAL_CATEGORY_NAMES
    assert document["summary"]["total_categories"] == len(OFFICIAL_CATEGORY_NAMES)
    assert document["summary"]["total_terms"] == 147
    assert document["summary"]["total_exclude_terms"] == 0
    for name, record in categories.items():
        assert record["enabled"] is True, name
        assert record["terms"], name
        assert "pepe" not in {str(item).casefold() for item in record.get("exclude_terms", [])}
    assert "prueba" not in categories
    assert "ventas_prueba_real" not in categories


def main() -> int:
    assert FACTORY_SETTINGS_PATH == ROOT / "resources" / "defaults" / "settings.json"
    assert FACTORY_CATEGORIES_PATH == ROOT / "resources" / "defaults" / "categories.json"
    settings_document = _load(FACTORY_SETTINGS_PATH, "smartfilter_settings")
    categories_document = _load(FACTORY_CATEGORIES_PATH, "category_database")
    _validate_settings(settings_document)
    _validate_categories(categories_document)

    # Services must consume the same immutable templates used by build/release.
    runtime_settings = get_default_settings_data()
    runtime_categories = build_default_category_data()
    assert runtime_settings["state"]["last_folder"] == ""
    assert runtime_settings["state"]["last_file"] == ""
    assert runtime_settings["state"]["last_search_text"] == ""
    assert runtime_settings["state"]["last_category"] == DEFAULT_CATEGORY_NAME
    assert runtime_settings["history"]["search_history"] == []
    assert set(runtime_categories["categories"]) == OFFICIAL_CATEGORY_NAMES

    # First start and reset must materialize clean user data from the same templates.
    with tempfile.TemporaryDirectory(prefix="smartfilter_factory_") as temp_dir:
        temp_root = Path(temp_dir)
        settings_path = temp_root / "data" / "settings.json"
        categories_path = temp_root / "data" / "categories.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(settings_service, "SETTINGS_PATH", settings_path),
            patch.object(settings_service, "ensure_project_directories", lambda: None),
        ):
            settings_service.ensure_settings_file()
            created = json.loads(settings_path.read_text(encoding="utf-8"))
            _validate_settings(created)
            changed = settings_service.get_settings()
            changed.update({
                "last_folder": "C:/private",
                "last_search_text": "secret",
                "last_category": "administracion",
                "search_history": ["secret"],
            })
            settings_service.write_settings(changed)
            reset = settings_service.reset_settings()
            assert reset["last_folder"] == ""
            assert reset["last_search_text"] == ""
            assert reset["last_category"] == DEFAULT_CATEGORY_NAME
            assert reset["search_history"] == []

        with (
            patch.object(category_service, "CATEGORIES_PATH", categories_path),
            patch.object(category_service, "ensure_project_directories", lambda: None),
        ):
            category_service.ensure_categories_file()
            created = json.loads(categories_path.read_text(encoding="utf-8"))
            _validate_categories(created)
            document = category_service.load_category_document()
            del document["data"]["categories"]["administracion"]
            category_service.save_category_document(document)
            restored = category_service.restore_missing_default_categories()
            assert restored["restored_names"] == ["administracion"]
            assert set(category_service.get_categories()) == OFFICIAL_CATEGORY_NAMES

    print("FACTORY_DEFAULTS_OK")
    print(f"VERSION_OK {APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
