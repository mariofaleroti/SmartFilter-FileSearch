from __future__ import annotations

SAVED_DISCARD_PREFIX = "Texto guardado: "


def extract_saved_discard_term(value: object) -> str:
    text = str(value or "").strip()
    if text.startswith(SAVED_DISCARD_PREFIX):
        return text[len(SAVED_DISCARD_PREFIX):].strip()
    return ""
