from __future__ import annotations

from typing import Iterable

DEFAULT_CATEGORY_NAME = "Ninguna"

ANALYSIS_MODE_FOLDER = "Carpeta"
ANALYSIS_MODE_FILE = "Archivo individual"
ANALYSIS_MODE_OPTIONS = [ANALYSIS_MODE_FOLDER, ANALYSIS_MODE_FILE]

ALL_FILE_TYPE_OPTION = "Todos los archivos"
DEFAULT_FILE_TYPE_OPTION = ALL_FILE_TYPE_OPTION

SEARCH_FILE_TYPE_OPTIONS: dict[str, list[str]] = {
    "Excel (.xlsx)": [".xlsx"],
    "PDF (.pdf)": [".pdf"],
    "Word (.docx)": [".docx"],
    "CSV (.csv)": [".csv"],
    "Texto (.txt/.log/.md)": [".txt", ".log", ".md"],
    "Datos (.json/.xml)": [".json", ".xml"],
    "HTML (.html/.htm)": [".html", ".htm"],
    ALL_FILE_TYPE_OPTION: [
        ".xlsx", ".pdf", ".docx", ".csv",
        ".txt", ".log", ".md", ".json", ".xml", ".html", ".htm",
    ],
}

SUPPORTED_EXTENSION_LABELS: dict[str, str] = {
    ".xlsx": "Excel",
    ".pdf": "PDF",
    ".docx": "Word",
    ".csv": "CSV",
    ".txt": "TXT",
    ".log": "LOG",
    ".md": "Markdown",
    ".json": "JSON",
    ".xml": "XML",
    ".html": "HTML",
    ".htm": "HTML",
}

DEFAULT_SEARCH_SCOPE_OPTION = "Nombre y contenido"
SEARCH_SCOPE_OPTIONS = ["Nombre y contenido", "Solo nombre", "Solo contenido"]

CATEGORY_SEARCH_MODE_ALL_CONTENT = "Todo el contenido"
CATEGORY_SEARCH_MODE_TARGET_FIELDS = "Solo campos o secciones indicadas"
CATEGORY_SEARCH_MODE_OPTIONS = [
    CATEGORY_SEARCH_MODE_ALL_CONTENT,
    CATEGORY_SEARCH_MODE_TARGET_FIELDS,
]

DEFAULT_TARGET_FIELDS = [
    "categoria",
    "categorias",
    "category",
    "categories",
    "area",
    "areas",
    "rubro",
    "sector",
    "perfil",
    "perfil laboral",
    "puesto",
    "cargo",
    "formacion",
    "educacion",
    "experiencia",
    "conocimientos",
    "habilidades",
]

MAX_CONTENT_FILE_SIZE_OPTIONS = ["Sin límite", "10 MB", "25 MB", "50 MB", "100 MB"]
MAX_CONTENT_FILE_SIZE_BYTES = {
    "Sin límite": None,
    "10 MB": 10 * 1024 * 1024,
    "25 MB": 25 * 1024 * 1024,
    "50 MB": 50 * 1024 * 1024,
    "100 MB": 100 * 1024 * 1024,
}

HIGHLIGHT_CELL_COLOR_OPTIONS = ["Ninguno", "Amarillo", "Naranja", "Verde", "Azul", "Violeta", "Gris"]
HIGHLIGHT_TEXT_COLOR_OPTIONS = ["Ninguno", "Rojo", "Azul", "Verde", "Naranja", "Violeta", "Negro"]
OPEN_RESULT_MODE_OPTIONS = ["Abrir vista destacada HTML", "Abrir original", "Preguntar siempre"]
RESULTS_DENSITY_OPTIONS = ["Compacta", "Normal", "Cómoda"]
APP_FONT_FAMILY_OPTIONS = ["Segoe UI", "Arial", "Calibri", "Verdana", "Tahoma", "Consolas"]
APP_FONT_SIZE_OPTIONS = ["Pequeña", "Normal", "Grande", "Muy grande"]

HIGHLIGHT_CELL_COLOR_PALETTES = {
    "Ninguno": {"row_fill": None, "cell_fill": None},
    "Amarillo": {"row_fill": "FFF2CC", "cell_fill": "FFD966"},
    "Naranja": {"row_fill": "FCE4D6", "cell_fill": "F4B183"},
    "Verde": {"row_fill": "E2F0D9", "cell_fill": "A9D18E"},
    "Azul": {"row_fill": "DDEBF7", "cell_fill": "9DC3E6"},
    "Violeta": {"row_fill": "EADCF8", "cell_fill": "C9A0DC"},
    "Gris": {"row_fill": "E7E6E6", "cell_fill": "BFBFBF"},
}

HIGHLIGHT_TEXT_COLOR_HEX = {
    "Ninguno": None,
    "Rojo": "D90000",
    "Azul": "0057B8",
    "Verde": "008000",
    "Naranja": "C55A11",
    "Violeta": "7030A0",
    "Negro": "000000",
}


def get_search_file_type_options() -> list[str]:
    return list(SEARCH_FILE_TYPE_OPTIONS.keys())


def get_individual_search_file_type_options() -> list[str]:
    return [option for option in SEARCH_FILE_TYPE_OPTIONS if option != ALL_FILE_TYPE_OPTION]


def get_extensions_for_file_type(file_type: str) -> list[str]:
    return list(SEARCH_FILE_TYPE_OPTIONS.get(file_type, SEARCH_FILE_TYPE_OPTIONS[DEFAULT_FILE_TYPE_OPTION]))


def get_all_supported_extensions() -> list[str]:
    return list(SEARCH_FILE_TYPE_OPTIONS[ALL_FILE_TYPE_OPTION])


def get_search_scope_options() -> list[str]:
    return list(SEARCH_SCOPE_OPTIONS)


def get_category_search_mode_options() -> list[str]:
    return list(CATEGORY_SEARCH_MODE_OPTIONS)


def get_default_target_fields() -> list[str]:
    return list(DEFAULT_TARGET_FIELDS)


def normalize_search_mode(search_mode: str | None) -> str:
    return search_mode if search_mode in CATEGORY_SEARCH_MODE_OPTIONS else CATEGORY_SEARCH_MODE_ALL_CONTENT


def normalize_file_extensions(extensions: Iterable[str]) -> list[str]:
    clean_items: list[str] = []
    seen_items: set[str] = set()
    for item in extensions:
        extension = str(item or "").strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = f".{extension}"
        if extension in seen_items:
            continue
        seen_items.add(extension)
        clean_items.append(extension)
    return clean_items
