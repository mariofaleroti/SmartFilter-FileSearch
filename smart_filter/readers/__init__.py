"""Smart Filter file readers.

Estos readers son lógica propia del producto: SharedCode camina archivos, Smart
Filter decide cómo extraer texto útil para buscar por contenido.
"""

from smart_filter.readers.reader_registry import (
    ReaderResult,
    can_read_extension,
    get_reader_capabilities,
    read_file_content,
)

__all__ = [
    "ReaderResult",
    "can_read_extension",
    "get_reader_capabilities",
    "read_file_content",
]
