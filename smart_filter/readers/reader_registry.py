from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from smart_filter.readers.base import ReaderFunction, ReaderResult, build_reader_result
from smart_filter.readers.csv_reader import read_csv_text
from smart_filter.readers.docx_reader import read_docx_text
from smart_filter.readers.pdf_reader import read_pdf_text
from smart_filter.readers.text_reader import read_text_by_extension
from smart_filter.readers.xlsx_reader import read_xlsx_text


@dataclass(frozen=True)
class ReaderCapability:
    extension: str
    reader_name: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "extension": self.extension,
            "reader_name": self.reader_name,
            "description": self.description,
        }


_READER_FUNCTIONS: dict[str, tuple[str, ReaderFunction, str]] = {
    ".xlsx": ("xlsx_reader", read_xlsx_text, "Extrae valores de celdas con openpyxl en modo read_only/data_only."),
    ".pdf": ("pdf_reader", read_pdf_text, "Extrae texto de páginas PDF con pypdf cuando el documento lo permite."),
    ".docx": ("docx_reader", read_docx_text, "Extrae párrafos, tablas, encabezados y pies con python-docx."),
    ".csv": ("csv_reader", read_csv_text, "Detecta delimitador común y concatena valores visibles del CSV."),
    ".txt": ("text_reader", read_text_by_extension, "Lee texto plano con fallback de codificación."),
    ".log": ("text_reader", read_text_by_extension, "Lee logs como texto plano con fallback de codificación."),
    ".md": ("text_reader", read_text_by_extension, "Lee Markdown como texto plano."),
    ".json": ("json_reader", read_text_by_extension, "Aplana claves y valores JSON para búsqueda textual."),
    ".xml": ("xml_reader", read_text_by_extension, "Aplana tags, atributos y texto XML para búsqueda textual."),
    ".html": ("html_reader", read_text_by_extension, "Extrae texto visible HTML ignorando script/style/noscript."),
    ".htm": ("html_reader", read_text_by_extension, "Extrae texto visible HTML ignorando script/style/noscript."),
}


def normalize_extension(extension: str | None) -> str:
    text = str(extension or "").strip().lower()
    if text and not text.startswith("."):
        text = f".{text}"
    return text


def can_read_extension(extension: str | None) -> bool:
    return normalize_extension(extension) in _READER_FUNCTIONS


def get_reader_capabilities() -> list[dict[str, str]]:
    return [
        ReaderCapability(extension=extension, reader_name=reader_name, description=description).to_dict()
        for extension, (reader_name, _reader, description) in sorted(_READER_FUNCTIONS.items())
    ]


def read_file_content(path: str | Path, *, max_size_bytes: int | None = None) -> ReaderResult:
    item = Path(path)
    extension = normalize_extension(item.suffix)
    reader_info = _READER_FUNCTIONS.get(extension)

    if reader_info is None:
        return build_reader_result(
            item,
            reader_name="unsupported_reader",
            status="unsupported_extension",
            error=f"No hay reader registrado para {extension or 'archivo sin extensión'}.",
        )

    reader_name, reader_function, _description = reader_info

    try:
        size_bytes = item.stat().st_size
    except OSError as exc:
        return build_reader_result(item, reader_name=reader_name, status="stat_error", error=str(exc))

    if max_size_bytes is not None and size_bytes > max_size_bytes:
        return build_reader_result(
            item,
            reader_name=reader_name,
            status="skipped_by_size",
            error=f"Archivo omitido por tamaño ({size_bytes} bytes > {max_size_bytes} bytes).",
            skipped_by_size=True,
        )

    try:
        text = reader_function(item)
    except Exception as exc:  # pragma: no cover - defensive by design for GUI stability.
        return build_reader_result(item, reader_name=reader_name, status="reader_error", error=str(exc))

    return build_reader_result(item, reader_name=reader_name, text=text, status="ok")
