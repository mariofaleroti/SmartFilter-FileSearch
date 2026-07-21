from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_REQUIRED_CONTRACT_KEYS = (
    "meta",
    "summary",
    "report_brief",
    "data",
    "diagnostics",
    "errors",
)


def load_factory_contract_data(
    path: str | Path,
    *,
    expected_config_type: str,
    fallback_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Load immutable factory data without ever modifying the template.

    Release validation guarantees that the JSON templates exist and are valid.
    The compiled fallback keeps source/dev executions usable if a template was
    accidentally removed before the next build.
    """

    factory_path = Path(path)
    try:
        document = json.loads(factory_path.read_text(encoding="utf-8-sig"))
        if not isinstance(document, Mapping):
            raise ValueError("El contrato de fábrica no es un objeto JSON.")
        missing = [key for key in _REQUIRED_CONTRACT_KEYS if key not in document]
        if missing:
            raise ValueError(f"Faltan claves del contrato de fábrica: {missing}")

        meta = document.get("meta")
        data = document.get("data")
        if not isinstance(meta, Mapping) or not isinstance(data, Mapping):
            raise ValueError("Las secciones meta y data del contrato de fábrica son inválidas.")
        if str(meta.get("file_type") or "") != "config":
            raise ValueError("El contrato de fábrica no es de tipo config.")
        if str(meta.get("config_type") or "") != expected_config_type:
            raise ValueError("El config_type del contrato de fábrica no coincide.")
        return deepcopy(dict(data))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return deepcopy(dict(fallback_data))
