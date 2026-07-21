from __future__ import annotations

from multiprocessing import freeze_support

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()


if __name__ == "__main__":
    freeze_support()
    from smart_filter.ui.main_app import main

    main()
