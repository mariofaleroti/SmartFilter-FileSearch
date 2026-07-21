from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.app_info import APP_VERSION
from smart_filter.services import result_action_service


def main() -> None:
    source = (ROOT / "smart_filter" / "services" / "result_action_service.py").read_text(encoding="utf-8")
    assert "from platform_core import open_path as platform_open_path" in source
    assert "OFFICE_ORIGINAL_EXTENSIONS" in source

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / "prueba.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        with patch.object(result_action_service, "platform_open_path") as native_open:
            outcome = result_action_service.open_original(type("Result", (), {"full_path": str(pdf_path)})())

        assert outcome.success is True
        native_open.assert_called_once_with(pdf_path)

    app_info = (ROOT / "smart_filter" / "app_info.py").read_text(encoding="utf-8")
    assert f'APP_VERSION = "{APP_VERSION}"' in app_info
    print("OK non-Office original open remains delegated to PlatformCore")


if __name__ == "__main__":
    main()
