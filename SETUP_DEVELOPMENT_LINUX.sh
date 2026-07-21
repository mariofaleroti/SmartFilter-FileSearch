#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -c "from smart_filter.bootstrap import ensure_sharedcode_on_path, get_installed_sharedcode_version; ensure_sharedcode_on_path(); print('SharedCode Cores', get_installed_sharedcode_version())"
.venv/bin/python -m tools.run_release_validation
printf '
OK: use .venv/bin/python app.py
'
