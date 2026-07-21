from __future__ import annotations

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.cli.runner import run_cli


def main() -> int:
    result = run_cli(["--portable-self-check"])
    assert result == 0, result
    print("PORTABLE_SELF_CHECK_COMMAND_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
