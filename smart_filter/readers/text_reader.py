from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from smart_filter.readers.base import collapse_spaces, safe_text

TEXT_ENCODINGS_TO_TRY = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

HTML_EXTENSIONS = {".html", ".htm"}
JSON_EXTENSIONS = {".json"}
XML_EXTENSIONS = {".xml"}


class VisibleTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._hidden_depth > 0:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._hidden_depth > 0:
            return
        clean_data = safe_text(data)
        if clean_data:
            self.parts.append(clean_data)

    def get_text(self) -> str:
        return "\n".join(self.parts)


def read_text_with_fallback(file_path: str | Path) -> str:
    last_error: Exception | None = None
    path = Path(file_path)

    for encoding in TEXT_ENCODINGS_TO_TRY:
        try:
            return path.read_text(encoding=encoding, errors="strict")
        except UnicodeDecodeError as error:
            last_error = error
            continue

    if last_error is not None:
        raise last_error
    return ""


def read_plain_text(file_path: str | Path) -> str:
    return read_text_with_fallback(file_path)


def read_html_text(file_path: str | Path) -> str:
    html = read_text_with_fallback(file_path)
    if not html:
        return ""

    parser = VisibleTextHTMLParser()
    parser.feed(html)
    visible_text = parser.get_text()
    if visible_text:
        return visible_text

    return collapse_spaces(re.sub(r"<[^>]+>", " ", html))


def _flatten_json_values(value: Any, output: list[str], *, label: str = "") -> None:
    if isinstance(value, dict):
        if label:
            output.append(f"{label}:")
        for key, item in value.items():
            clean_key = str(key or "").strip()
            _flatten_json_values(item, output, label=clean_key)
    elif isinstance(value, list):
        if label:
            output.append(f"{label}:")
        for item in value:
            _flatten_json_values(item, output, label=label)
    elif value is not None:
        clean_value = str(value).strip()
        if not clean_value:
            return
        output.append(f"{label}: {clean_value}" if label else clean_value)


def read_json_text(file_path: str | Path) -> str:
    raw_text = read_text_with_fallback(file_path)
    if not raw_text:
        return ""

    try:
        payload = json.loads(raw_text)
    except Exception:
        return raw_text

    parts: list[str] = []
    _flatten_json_values(payload, parts)
    return "\n".join(parts) if parts else raw_text


def _xml_element_lines(element: ET.Element, output: list[str]) -> None:
    tag = str(element.tag or "").strip()
    direct_text = str(element.text or "").strip()
    attributes = " ".join(
        f"{key}={value}" for key, value in element.attrib.items() if str(key).strip()
    ).strip()

    if direct_text or attributes:
        value = " ".join(part for part in (attributes, direct_text) if part)
        output.append(f"{tag}: {value}" if tag else value)
    elif tag:
        output.append(f"{tag}:")

    for child in list(element):
        _xml_element_lines(child, output)


def read_xml_text(file_path: str | Path) -> str:
    raw_text = read_text_with_fallback(file_path)
    if not raw_text:
        return ""

    try:
        root = ET.fromstring(raw_text)
    except Exception:
        return raw_text

    parts: list[str] = []
    _xml_element_lines(root, parts)
    return "\n".join(parts) if parts else raw_text


def read_text_by_extension(file_path: str | Path) -> str:
    extension = Path(file_path).suffix.lower()
    if extension in HTML_EXTENSIONS:
        return read_html_text(file_path)
    if extension in JSON_EXTENSIONS:
        return read_json_text(file_path)
    if extension in XML_EXTENSIONS:
        return read_xml_text(file_path)
    return read_plain_text(file_path)
