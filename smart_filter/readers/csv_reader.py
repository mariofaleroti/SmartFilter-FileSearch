from __future__ import annotations

import csv
from pathlib import Path

CSV_ENCODINGS_TO_TRY = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

CSV_DELIMITERS_TO_TRY = (
    ",",
    ";",
    "\t",
    "|",
)


def read_text_with_fallback(file_path: str | Path) -> str:
    last_error: Exception | None = None
    path = Path(file_path)

    for encoding in CSV_ENCODINGS_TO_TRY:
        try:
            return path.read_text(encoding=encoding, errors="strict")
        except UnicodeDecodeError as error:
            last_error = error
            continue

    if last_error is not None:
        raise last_error
    return ""


def detect_csv_dialect(text: str) -> csv.Dialect:
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=CSV_DELIMITERS_TO_TRY)
    except csv.Error:
        class DefaultDialect(csv.excel):
            delimiter = ";"
        return DefaultDialect


def _clean_row(row: list[object]) -> list[str]:
    return [str(value or "").strip() for value in row]


def _looks_like_header(text: str, rows: list[list[str]]) -> bool:
    if len(rows) < 2:
        return False
    first = [value for value in rows[0] if value]
    if len(first) < 2 or len(set(value.casefold() for value in first)) != len(first):
        return False
    try:
        if csv.Sniffer().has_header(text[:8192]):
            return True
    except csv.Error:
        pass
    return all(len(value) <= 60 and any(character.isalpha() for character in value) for value in first)


def _rows_to_structured_text(rows: list[list[str]], *, has_header: bool) -> str:
    if not rows:
        return ""

    output: list[str] = []
    if has_header:
        headers = rows[0]
        for row in rows[1:]:
            emitted = False
            for index, value in enumerate(row):
                if not value:
                    continue
                header = headers[index].strip() if index < len(headers) else ""
                if header:
                    output.append(f"{header}: {value}")
                else:
                    output.append(value)
                emitted = True
            if emitted:
                output.append("")
    else:
        for row in rows:
            values = [value for value in row if value]
            if values:
                output.append(" | ".join(values))

    return "\n".join(output).strip()


def read_csv_text(file_path: str | Path) -> str:
    text = read_text_with_fallback(file_path)
    if not text:
        return ""

    dialect = detect_csv_dialect(text)
    try:
        rows = [_clean_row(row) for row in csv.reader(text.splitlines(), dialect=dialect)]
    except Exception:
        return text

    return _rows_to_structured_text(rows, has_header=_looks_like_header(text, rows)) or text
