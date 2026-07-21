from __future__ import annotations

import json
import tempfile
from pathlib import Path

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.services import category_service as category_service


def main() -> None:
    original_path = category_service.CATEGORIES_PATH
    with tempfile.TemporaryDirectory(prefix="smartfilter_categories_") as temp_dir:
        root = Path(temp_dir)
        category_service.CATEGORIES_PATH = root / "data" / "categories.json"
        try:
            category_service.write_category_data(category_service.build_default_category_data())
            original_admin = category_service.get_category_rule("administracion")
            assert original_admin["terms"]

            category_service.delete_category("administracion")
            assert category_service.get_category("administracion") is None
            assert category_service.list_category_backups(), "Delete must create an automatic backup"

            restored = category_service.restore_missing_default_categories()
            assert restored["restored_count"] == 1
            assert restored["restored_names"] == ["administracion"]
            assert category_service.get_category_rule("administracion")["terms"] == original_admin["terms"]

            selected_export = root / "administracion.json"
            selected_result = category_service.export_categories_to_file(selected_export, ["administracion"])
            assert selected_result["categories_count"] == 1
            exported_document = json.loads(selected_export.read_text(encoding="utf-8"))
            assert tuple(exported_document) == ("meta", "summary", "report_brief", "data", "diagnostics", "errors")
            assert exported_document["meta"]["config_type"] == "category_export"
            assert set(exported_document["data"]["categories"]) == {"administracion"}

            category_service.save_category(
                original_category_name="",
                title="categoria_personal",
                description="Prueba",
                terms=["personalizado"],
                discard_categories=["administracion", "categoria_personal", "inexistente"],
            )
            personal = category_service.get_category_rule("categoria_personal")
            assert personal["discard_categories"] == ["administracion"]
            assert "categoria_personal" not in category_service.get_discard_category_options("categoria_personal")

            category_service.delete_category("administracion")
            add_result = category_service.import_categories_from_file(
                selected_export,
                category_service.CATEGORY_IMPORT_ADD_NEW,
            )
            assert add_result["added_count"] == 1
            assert category_service.get_category("administracion") is not None
            assert category_service.get_category("categoria_personal") is not None

            category_service.save_category(
                original_category_name="administracion",
                title="administracion",
                description="Alterada",
                terms=["solo_un_termino"],
            )
            merge_result = category_service.import_categories_from_file(
                selected_export,
                category_service.CATEGORY_IMPORT_MERGE,
            )
            assert merge_result["updated_count"] == 1
            assert category_service.get_category_rule("administracion")["terms"] == original_admin["terms"]

            replace_preview = category_service.preview_category_import(
                selected_export,
                category_service.CATEGORY_IMPORT_REPLACE,
            )
            assert replace_preview["replace_removed_count"] >= 1
            replace_result = category_service.import_categories_from_file(
                selected_export,
                category_service.CATEGORY_IMPORT_REPLACE,
            )
            assert replace_result["removed_count"] >= 1
            assert set(category_service.get_categories()) == {"administracion"}

            invalid_export = root / "legacy.json"
            invalid_export.write_text(json.dumps({"categories": {}}), encoding="utf-8")
            try:
                category_service.preview_category_import(invalid_export)
            except ValueError as exc:
                assert "contrato" in str(exc).casefold() or "clave" in str(exc).casefold()
            else:
                raise AssertionError("Legacy category JSON must be rejected")

            assert len(category_service.list_category_backups()) <= category_service.MAX_CATEGORY_BACKUPS
            print("CATEGORY_PORTABILITY_SAFETY_OK")
        finally:
            category_service.CATEGORIES_PATH = original_path


if __name__ == "__main__":
    main()
