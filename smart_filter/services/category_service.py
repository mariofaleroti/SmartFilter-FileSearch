from __future__ import annotations

import json
import re
import shutil
import unicodedata
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from config_core import load_config, write_json_file
from date_time_core import create_timestamp_pair, utc_now_iso
from json_contract_core import create_contract

from smart_filter.app_info import APP_NAME, APP_VERSION
from smart_filter.factory_defaults import load_factory_contract_data
from smart_filter.domain.default_categories import DEFAULT_CATEGORIES
from smart_filter.domain.search_config import (
    CATEGORY_SEARCH_MODE_ALL_CONTENT,
    CATEGORY_SEARCH_MODE_OPTIONS,
    DEFAULT_CATEGORY_NAME,
    get_category_search_mode_options,
    get_default_target_fields,
    normalize_search_mode,
)
from smart_filter.paths import CATEGORIES_PATH, FACTORY_CATEGORIES_PATH, ensure_project_directories


CATEGORY_IMPORT_ADD_NEW = "add_new"
CATEGORY_IMPORT_MERGE = "merge"
CATEGORY_IMPORT_REPLACE = "replace"
CATEGORY_IMPORT_MODES = (
    CATEGORY_IMPORT_ADD_NEW,
    CATEGORY_IMPORT_MERGE,
    CATEGORY_IMPORT_REPLACE,
)
MAX_CATEGORY_BACKUPS = 30


def _category_backup_dir() -> Path:
    return CATEGORIES_PATH.parent / "backups" / "categories"


def _safe_reason(value: Any) -> str:
    reason = build_category_key(value or "change")
    return reason[:48] or "change"


def _prune_category_backups(limit: int = MAX_CATEGORY_BACKUPS) -> None:
    backup_dir = _category_backup_dir()
    if not backup_dir.exists():
        return
    backups = sorted(backup_dir.glob("categories_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for stale in backups[max(1, int(limit)) :]:
        try:
            stale.unlink()
        except OSError:
            pass


def create_categories_backup(reason: Any = "change") -> Path | None:
    """Preserve the exact current category file before a destructive operation."""
    if not CATEGORIES_PATH.exists():
        return None
    backup_dir = _category_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"categories_{stamp}_{_safe_reason(reason)}.json"
    shutil.copy2(CATEGORIES_PATH, backup_path)
    _prune_category_backups()
    return backup_path


def list_category_backups() -> list[Path]:
    backup_dir = _category_backup_dir()
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("categories_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
    return re.sub(r"\s+", " ", without_accents).strip()


def build_category_key(title: Any) -> str:
    normalized_title = normalize_text(title)
    normalized_title = re.sub(r"[^a-z0-9]+", "_", normalized_title)
    normalized_title = normalized_title.strip("_")

    if not normalized_title:
        raise ValueError("El título de la categoría no puede estar vacío.")

    return normalized_title


def clean_text_items(items: Any) -> list[str]:
    if isinstance(items, str):
        raw_items = [items]
    elif isinstance(items, list):
        raw_items = items
    else:
        raw_items = []

    cleaned_items: list[str] = []
    seen_items: set[str] = set()

    for item in raw_items:
        clean_item = str(item or "").strip()
        normalized_item = normalize_text(clean_item)

        if not clean_item or not normalized_item:
            continue

        if normalized_item in seen_items:
            continue

        seen_items.add(normalized_item)
        cleaned_items.append(clean_item)

    return cleaned_items


def clean_terms(terms: Any) -> list[str]:
    return clean_text_items(terms)


def clean_target_fields(target_fields: Any) -> list[str]:
    cleaned = clean_text_items(target_fields)
    return cleaned or get_default_target_fields()


def _clean_description(value: Any) -> str:
    return str(value or "").strip()


def _new_runtime(source: str = "Smart Filter factory categories") -> dict[str, Any]:
    updated_at_utc, updated_at_local = create_timestamp_pair()
    return {
        "created_at_utc": updated_at_utc,
        "updated_at_utc": updated_at_utc,
        "updated_at_local": updated_at_local,
        "source": source,
    }


def _clone_compiled_default_categories() -> dict[str, dict[str, Any]]:
    return deepcopy(DEFAULT_CATEGORIES)


def _clone_default_categories() -> dict[str, dict[str, Any]]:
    factory_data = load_factory_contract_data(
        FACTORY_CATEGORIES_PATH,
        expected_config_type="category_database",
        fallback_data={"categories": _clone_compiled_default_categories()},
    )
    categories = factory_data.get("categories")
    if not isinstance(categories, (Mapping, list)):
        return _clone_compiled_default_categories()
    return deepcopy(categories)


def clean_category_record(category_key: str, category_data: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(category_data or {})
    key = build_category_key(category_key or data.get("title") or data.get("name") or "categoria")
    title = str(data.get("title") or key).strip() or key
    terms = clean_terms(data.get("terms", []))

    return {
        "title": build_category_key(title),
        "description": _clean_description(data.get("description")),
        "enabled": bool(data.get("enabled", True)),
        "terms": terms,
        "exclude_terms": clean_terms(data.get("exclude_terms", [])),
        "discard_categories": [],  # Se normaliza después de conocer todas las categorías válidas.
        "search_mode": normalize_search_mode(data.get("search_mode")),
        "target_fields": clean_target_fields(data.get("target_fields", [])),
    }


def sanitize_categories(categories: Any) -> dict[str, dict[str, Any]]:
    if isinstance(categories, Mapping):
        raw_categories = dict(categories)
    elif isinstance(categories, list):
        raw_categories = {
            build_category_key(item.get("name") or item.get("title")): item
            for item in categories
            if isinstance(item, Mapping) and (item.get("name") or item.get("title"))
        }
    else:
        raw_categories = _clone_default_categories()

    cleaned_categories: dict[str, dict[str, Any]] = {}

    for raw_key, raw_data in raw_categories.items():
        if str(raw_key or "").strip() == DEFAULT_CATEGORY_NAME:
            continue
        if not isinstance(raw_data, Mapping):
            continue

        category_key = build_category_key(raw_key or raw_data.get("title"))
        record = clean_category_record(category_key, raw_data)
        if not record["terms"]:
            continue
        cleaned_categories[category_key] = record

    valid_names = set(cleaned_categories)
    for category_key, record in cleaned_categories.items():
        cleaned_discard_categories: list[str] = []
        seen_items: set[str] = set()
        original_record = raw_categories.get(category_key) or raw_categories.get(record.get("title")) or {}
        raw_discard = original_record.get("discard_categories", []) if isinstance(original_record, Mapping) else []

        for item in raw_discard or []:
            candidate = build_category_key(item)
            if candidate == category_key or candidate not in valid_names or candidate in seen_items:
                continue
            cleaned_discard_categories.append(candidate)
            seen_items.add(candidate)

        record["discard_categories"] = cleaned_discard_categories

    return cleaned_categories


def build_default_category_data() -> dict[str, Any]:
    return {
        "categories": sanitize_categories(_clone_default_categories()),
        "runtime": _new_runtime(),
    }


def recalculate_summary_data(categories: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    total_categories = len(categories)
    enabled_categories = 0
    disabled_categories = 0
    total_terms = 0
    total_exclude_terms = 0
    total_discard_categories = 0

    for category in categories.values():
        if category.get("enabled", True):
            enabled_categories += 1
        else:
            disabled_categories += 1
        total_terms += len(category.get("terms", []))
        total_exclude_terms += len(category.get("exclude_terms", []))
        total_discard_categories += len(category.get("discard_categories", []))

    return {
        "status": "active",
        "total_categories": total_categories,
        "total_terms": total_terms,
        "total_exclude_terms": total_exclude_terms,
        "total_discard_categories": total_discard_categories,
        "enabled_categories": enabled_categories,
        "disabled_categories": disabled_categories,
        "diagnostics_count": 0,
        "errors_count": 0,
    }


def sanitize_category_data(category_data: Mapping[str, Any] | None) -> dict[str, Any]:
    base = build_default_category_data()
    source = dict(category_data or {})

    if isinstance(source.get("categories"), (Mapping, list)):
        base["categories"] = sanitize_categories(source.get("categories"))

    runtime = dict(source.get("runtime") or base.get("runtime") or {})
    if not str(runtime.get("created_at_utc") or "").strip():
        runtime["created_at_utc"] = utc_now_iso()
    runtime["updated_at_utc"] = utc_now_iso()
    runtime.setdefault("source", "Smart Filter categories")
    base["runtime"] = runtime
    return base


def build_category_contract(category_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = sanitize_category_data(category_data or build_default_category_data())
    data["runtime"]["updated_at_utc"] = utc_now_iso()
    return create_contract(
        file_type="config",
        subtype_key="config_type",
        subtype_value="category_database",
        tool_name=APP_NAME,
        module_name="CategoryService",
        extra_meta={
            "tool_version": APP_VERSION,
            "updated_at_utc": data["runtime"]["updated_at_utc"],
        },
        summary=recalculate_summary_data(data["categories"]),
        report_brief={
            "title": "Base de categorías",
            "description": "Base oficial de categorías inteligentes de Smart Filter.",
            "recommendations": [
                "Las categorías siguen siendo lógica propia de Smart Filter; SharedCode solo gestiona contrato, carga y escritura."
            ],
        },
        data=data,
    )


def build_category_export_contract(
    categories: Mapping[str, Mapping[str, Any]],
    *,
    scope: str,
) -> dict[str, Any]:
    cleaned = sanitize_categories(categories)
    generated_at_utc, generated_at_local = create_timestamp_pair()
    return create_contract(
        file_type="config",
        subtype_key="config_type",
        subtype_value="category_export",
        tool_name=APP_NAME,
        module_name="CategoryService",
        extra_meta={
            "tool_version": APP_VERSION,
            "generated_at_utc": generated_at_utc,
        },
        summary={
            **recalculate_summary_data(cleaned),
            "export_scope": scope,
        },
        report_brief={
            "title": "Exportación de categorías",
            "description": "Paquete portable de categorías inteligentes de Smart Filter.",
            "recommendations": [
                "Importar desde Categorías para agregar, combinar o reemplazar reglas.",
            ],
        },
        data={
            "categories": cleaned,
            "export": {
                "scope": scope,
                "generated_at_utc": generated_at_utc,
                "generated_at_local": generated_at_local,
            },
        },
    )


def export_categories_to_file(
    destination: str | Path,
    category_names: Any = None,
) -> dict[str, Any]:
    categories = get_categories()
    if category_names is None:
        selected = dict(categories)
        scope = "all"
    else:
        requested = clean_text_items(category_names)
        selected = {}
        pending = [build_category_key(item) for item in requested]
        while pending:
            key = pending.pop(0)
            if key in selected or key not in categories:
                continue
            selected[key] = categories[key]
            for dependency in categories[key].get("discard_categories", []):
                dependency_key = build_category_key(dependency)
                if dependency_key not in selected:
                    pending.append(dependency_key)
        scope = "selected_with_dependencies" if len(selected) > len(requested) else "selected"

    if not selected:
        raise ValueError("No hay categorías válidas para exportar.")

    contract = build_category_export_contract(selected, scope=scope)
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(contract, output_path)
    return {
        "path": output_path,
        "scope": scope,
        "categories_count": len(selected),
        "category_names": sorted(selected),
    }


def _load_import_contract(source_path: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    path = Path(source_path)
    if not path.is_file():
        raise ValueError("El archivo de categorías no existe.")
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el JSON de categorías: {exc}") from exc

    if not isinstance(document, Mapping):
        raise ValueError("El archivo no contiene un contrato JSON válido.")
    for required_key in ("meta", "summary", "report_brief", "data", "diagnostics", "errors"):
        if required_key not in document:
            raise ValueError(f"Falta la clave obligatoria del contrato: {required_key}")

    meta = document.get("meta")
    data = document.get("data")
    if not isinstance(meta, Mapping) or not isinstance(data, Mapping):
        raise ValueError("Las secciones meta y data deben ser objetos.")
    if str(meta.get("file_type") or "") != "config":
        raise ValueError("El archivo no es una configuración de Smart Filter.")
    if str(meta.get("config_type") or "") not in {"category_database", "category_export"}:
        raise ValueError("El archivo no es una base ni una exportación de categorías.")
    if not isinstance(data.get("categories"), (Mapping, list)):
        raise ValueError("El archivo no contiene data.categories.")

    categories = sanitize_categories(data.get("categories"))
    if not categories:
        raise ValueError("El archivo no contiene categorías válidas con términos de inclusión.")
    return categories, dict(document)


def preview_category_import(source_path: str | Path, mode: str = CATEGORY_IMPORT_MERGE) -> dict[str, Any]:
    if mode not in CATEGORY_IMPORT_MODES:
        raise ValueError("Modo de importación no válido.")
    imported, _document = _load_import_contract(source_path)
    current = get_categories()
    imported_names = set(imported)
    current_names = set(current)
    return {
        "mode": mode,
        "source_path": Path(source_path),
        "imported_count": len(imported_names),
        "new_count": len(imported_names - current_names),
        "conflict_count": len(imported_names & current_names),
        "replace_removed_count": len(current_names - imported_names) if mode == CATEGORY_IMPORT_REPLACE else 0,
        "category_names": sorted(imported_names),
    }


def import_categories_from_file(source_path: str | Path, mode: str = CATEGORY_IMPORT_MERGE) -> dict[str, Any]:
    if mode not in CATEGORY_IMPORT_MODES:
        raise ValueError("Modo de importación no válido.")

    imported, _document = _load_import_contract(source_path)
    current_document = load_category_document()
    current_data = sanitize_category_data(current_document.get("data", {}))
    current = dict(current_data["categories"])
    before_names = set(current)
    imported_names = set(imported)

    if mode == CATEGORY_IMPORT_ADD_NEW:
        final = dict(current)
        for name, record in imported.items():
            if name not in final:
                final[name] = record
    elif mode == CATEGORY_IMPORT_MERGE:
        final = dict(current)
        final.update(imported)
    else:
        final = dict(imported)

    final = sanitize_categories(final)
    backup_path = create_categories_backup("before_import")
    write_category_data({
        "categories": final,
        "runtime": _new_runtime("Smart Filter category import"),
    })

    after_names = set(final)
    return {
        "mode": mode,
        "source_path": Path(source_path),
        "backup_path": backup_path,
        "imported_count": len(imported_names),
        "added_count": len(after_names - before_names),
        "updated_count": len(imported_names & before_names) if mode == CATEGORY_IMPORT_MERGE else 0,
        "skipped_count": len(imported_names & before_names) if mode == CATEGORY_IMPORT_ADD_NEW else 0,
        "removed_count": len(before_names - after_names),
        "total_categories": len(final),
    }


def restore_missing_default_categories() -> dict[str, Any]:
    document = load_category_document()
    data = sanitize_category_data(document.get("data", {}))
    categories = dict(data["categories"])
    defaults = sanitize_categories(_clone_default_categories())
    missing = sorted(set(defaults) - set(categories))
    if not missing:
        return {
            "restored_count": 0,
            "restored_names": [],
            "backup_path": None,
            "total_categories": len(categories),
        }

    backup_path = create_categories_backup("before_restore_defaults")
    for name in missing:
        categories[name] = deepcopy(defaults[name])
    write_category_data({
        "categories": categories,
        "runtime": _new_runtime("Smart Filter default category restore"),
    })
    return {
        "restored_count": len(missing),
        "restored_names": missing,
        "backup_path": backup_path,
        "total_categories": len(categories),
    }


def get_discard_category_options(current_category_name: Any = None) -> list[str]:
    current_key = build_category_key(current_category_name) if str(current_category_name or "").strip() else ""
    return sorted(name for name in get_categories() if name != current_key)


def write_category_data(category_data: Mapping[str, Any]) -> dict[str, Any]:
    ensure_project_directories()
    data = sanitize_category_data(category_data)
    write_json_file(build_category_contract(data), CATEGORIES_PATH)
    return data


def ensure_categories_file() -> None:
    if CATEGORIES_PATH.exists():
        return
    write_category_data(build_default_category_data())


def load_category_result():
    ensure_categories_file()
    return load_config(
        CATEGORIES_PATH,
        defaults=build_default_category_data(),
        required_paths=("categories", "runtime"),
        type_rules={
            "categories": dict,
            "runtime": dict,
        },
        contract_mode=True,
        validate_standard_contract=True,
        require_contract_validator=True,
    )


def load_category_document() -> dict[str, Any]:
    result = load_category_result()
    if result.raw_content and isinstance(result.raw_content, dict) and result.is_valid:
        document = result.raw_content
        document["data"] = sanitize_category_data(document.get("data", {}))
        document["summary"] = recalculate_summary_data(document["data"]["categories"])
        return document
    return build_category_contract(build_default_category_data())


def save_category_document(document: Mapping[str, Any]) -> dict[str, Any]:
    data = sanitize_category_data(dict(document).get("data", document))
    write_category_data(data)
    return build_category_contract(data)


def recalculate_summary(document: Mapping[str, Any]) -> dict[str, Any]:
    new_document = dict(document)
    data = sanitize_category_data(new_document.get("data", {}))
    new_document["data"] = data
    new_document["summary"] = recalculate_summary_data(data["categories"])
    return new_document


def load_categories() -> dict[str, dict[str, Any]]:
    document = load_category_document()
    return dict(document.get("data", {}).get("categories", {}))


def get_categories() -> dict[str, dict[str, Any]]:
    return load_categories()


def get_category(category_name: Any) -> dict[str, Any] | None:
    category_key = build_category_key(category_name) if str(category_name or "").strip() else ""
    return get_categories().get(category_key)


def get_category_names(include_disabled: bool = False) -> list[str]:
    names: list[str] = []
    for category_name, category_data in get_categories().items():
        if include_disabled or category_data.get("enabled", True):
            if category_name not in names:
                names.append(category_name)
    return [DEFAULT_CATEGORY_NAME] + sorted(names)


def get_enabled_category_names() -> list[str]:
    return get_category_names(include_disabled=False)


def get_category_terms(category_name: Any) -> list[str]:
    return get_category_rule(category_name).get("terms", [])


def get_category_exclude_terms(category_name: Any) -> list[str]:
    return get_category_rule(category_name).get("exclude_terms", [])


def get_category_search_mode(category_name: Any) -> str:
    return get_category_rule(category_name).get("search_mode", CATEGORY_SEARCH_MODE_ALL_CONTENT)


def get_category_target_fields(category_name: Any) -> list[str]:
    return get_category_rule(category_name).get("target_fields", get_default_target_fields())


def clean_discard_categories(discard_categories: Any, current_category_name: Any = None) -> list[str]:
    categories = get_categories()
    current_key = build_category_key(current_category_name) if str(current_category_name or "").strip() else ""
    cleaned_items: list[str] = []
    seen_items: set[str] = set()

    for item in discard_categories or []:
        category_name = str(item or "").strip()
        if not category_name or category_name == DEFAULT_CATEGORY_NAME:
            continue
        category_key = build_category_key(category_name)
        if current_key and category_key == current_key:
            continue
        if category_key not in categories or category_key in seen_items:
            continue
        seen_items.add(category_key)
        cleaned_items.append(category_key)

    return cleaned_items


def get_category_rule(category_name: Any) -> dict[str, Any]:
    if not category_name or str(category_name).strip() == DEFAULT_CATEGORY_NAME:
        return {
            "name": DEFAULT_CATEGORY_NAME,
            "title": DEFAULT_CATEGORY_NAME,
            "description": "",
            "enabled": False,
            "terms": [],
            "exclude_terms": [],
            "discard_categories": [],
            "search_mode": CATEGORY_SEARCH_MODE_ALL_CONTENT,
            "target_fields": get_default_target_fields(),
        }

    category_key = build_category_key(category_name)
    category_data = get_categories().get(category_key)

    if not category_data or not category_data.get("enabled", True):
        return {
            "name": category_key,
            "title": category_key,
            "description": "",
            "enabled": False,
            "terms": [],
            "exclude_terms": [],
            "discard_categories": [],
            "search_mode": CATEGORY_SEARCH_MODE_ALL_CONTENT,
            "target_fields": get_default_target_fields(),
        }

    return {
        "name": category_key,
        "title": category_data.get("title", category_key),
        "description": category_data.get("description", ""),
        "enabled": bool(category_data.get("enabled", True)),
        "terms": clean_terms(category_data.get("terms", [])),
        "exclude_terms": clean_terms(category_data.get("exclude_terms", [])),
        "discard_categories": clean_discard_categories(
            category_data.get("discard_categories", []),
            current_category_name=category_key,
        ),
        "search_mode": normalize_search_mode(category_data.get("search_mode")),
        "target_fields": clean_target_fields(category_data.get("target_fields", [])),
    }


def save_category(
    original_category_name: Any,
    title: Any,
    description: Any,
    terms: Any,
    enabled: bool = True,
    exclude_terms: Any = None,
    discard_categories: Any = None,
    search_mode: str = CATEGORY_SEARCH_MODE_ALL_CONTENT,
    target_fields: Any = None,
) -> str:
    document = load_category_document()
    data = sanitize_category_data(document.get("data", {}))
    categories = data["categories"]

    category_key = build_category_key(title)
    original_key = build_category_key(original_category_name) if str(original_category_name or "").strip() else ""
    cleaned_terms = clean_terms(terms)
    cleaned_exclude_terms = clean_terms(exclude_terms or [])
    cleaned_target_fields = clean_target_fields(target_fields or [])
    clean_search_mode = normalize_search_mode(search_mode)

    if not cleaned_terms:
        raise ValueError("La categoría debe tener al menos un término para incluir.")

    is_renaming = bool(original_key and original_key != category_key)

    if is_renaming and category_key in categories:
        raise ValueError("Ya existe una categoría con ese nombre.")

    if not original_key and category_key in categories:
        raise ValueError("Ya existe una categoría con ese nombre.")

    if original_key and original_key in categories:
        create_categories_backup("before_save")

    if is_renaming:
        for category in categories.values():
            category["discard_categories"] = [
                category_key if item == original_key else item
                for item in category.get("discard_categories", [])
            ]
        categories.pop(original_key, None)

    categories[category_key] = {
        "title": category_key,
        "description": _clean_description(description),
        "enabled": bool(enabled),
        "terms": cleaned_terms,
        "exclude_terms": cleaned_exclude_terms,
        "discard_categories": clean_discard_categories(discard_categories or [], current_category_name=category_key),
        "search_mode": clean_search_mode,
        "target_fields": cleaned_target_fields,
    }

    write_category_data(data)
    return category_key


def delete_category(category_name: Any) -> None:
    if not category_name or str(category_name).strip() == DEFAULT_CATEGORY_NAME:
        raise ValueError("No se puede eliminar esa categoría.")

    category_key = build_category_key(category_name)
    document = load_category_document()
    data = sanitize_category_data(document.get("data", {}))
    categories = data["categories"]

    if category_key not in categories:
        raise ValueError("La categoría no existe.")

    create_categories_backup("before_delete")
    categories.pop(category_key)

    for category in categories.values():
        category["discard_categories"] = [
            item for item in category.get("discard_categories", []) if item != category_key
        ]

    write_category_data(data)


def get_category_search_mode_options() -> list[str]:
    return list(CATEGORY_SEARCH_MODE_OPTIONS)
