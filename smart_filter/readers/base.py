from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ReaderResult:
    """Result returned by a Smart Filter reader.

    The scanner and matcher should not know about each file format. They receive
    a normalized content payload plus diagnostic fields useful for GUI/CLI.
    """

    path: str
    extension: str
    reader_name: str
    text: str = ""
    status: str = "ok"
    error: str = ""
    size_bytes: int | None = None
    char_count: int = 0
    skipped_by_size: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "extension": self.extension,
            "reader_name": self.reader_name,
            "status": self.status,
            "error": self.error,
            "size_bytes": self.size_bytes,
            "char_count": self.char_count,
            "skipped_by_size": self.skipped_by_size,
            "text_preview": self.text[:240],
        }


ReaderFunction = Callable[[Path], str]


def collapse_spaces(text: Any) -> str:
    return " ".join(str(text or "").split())


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def build_reader_result(
    path: str | Path,
    *,
    reader_name: str,
    text: str = "",
    status: str = "ok",
    error: str = "",
    skipped_by_size: bool = False,
) -> ReaderResult:
    item = Path(path)
    size_bytes: int | None = None
    try:
        if item.exists() and item.is_file():
            size_bytes = item.stat().st_size
    except OSError:
        size_bytes = None

    # Preserve line breaks so the GUI can report exact line/row occurrences.
    # Matching still normalizes whitespace later, so this does not weaken search semantics.
    preserved_text = str(text or "").strip()
    return ReaderResult(
        path=str(item),
        extension=item.suffix.lower(),
        reader_name=reader_name,
        text=preserved_text,
        status=status,
        error=error,
        size_bytes=size_bytes,
        char_count=len(preserved_text),
        skipped_by_size=skipped_by_size,
    )
