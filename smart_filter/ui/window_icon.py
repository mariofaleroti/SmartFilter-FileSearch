from __future__ import annotations

from pathlib import Path
from typing import Any

from smart_filter.bootstrap import project_root


def resolve_app_icon_path() -> Path | None:
    candidates = [
        project_root() / "assets" / "app_icon.ico",
        project_root() / "release" / "SmartFilter" / "assets" / "app_icon.ico",
        Path(__file__).resolve().parents[2] / "assets" / "app_icon.ico",
    ]
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except Exception:
            continue
    return None


def _append_target(targets: list[Any], seen: set[int], value: Any) -> None:
    if value is None:
        return
    marker = id(value)
    if marker not in seen:
        seen.add(marker)
        targets.append(value)


def _candidate_targets(window_like: Any) -> list[Any]:
    queue = [window_like]
    seen: set[int] = set()
    targets: list[Any] = []

    while queue:
        current = queue.pop(0)
        if current is None:
            continue
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        targets.append(current)

        # En GuiCore varias ventanas secundarias son wrappers. El icono real se
        # aplica sobre el Toplevel interno; normalmente se obtiene desde los
        # frames reales con winfo_toplevel().
        try:
            if hasattr(current, "winfo_toplevel"):
                _append_target(targets, seen, current.winfo_toplevel())
        except Exception:
            pass

        for attr in (
            "root",
            "window",
            "toplevel",
            "top_level",
            "_window",
            "_toplevel",
            "_top_level",
            "master",
            "content_frame",
            "footer_frame",
            "header_frame",
            "body_frame",
        ):
            try:
                value = getattr(current, attr, None)
            except Exception:
                value = None
            if value is not None:
                queue.append(value)

        try:
            if hasattr(current, "winfo_children"):
                queue.extend(list(current.winfo_children()))
        except Exception:
            pass

    return targets


def _apply_icon_to_target(target: Any, icon_path: Path) -> bool:
    applied = False
    # En Windows, iconbitmap(path) suele ser lo más confiable para Toplevel.
    for call in (
        lambda: target.iconbitmap(str(icon_path)),
        lambda: target.iconbitmap(default=str(icon_path)),
        lambda: target.wm_iconbitmap(str(icon_path)),
        lambda: target.wm_iconbitmap(default=str(icon_path)),
    ):
        try:
            call()
            applied = True
        except Exception:
            pass
    return applied


def apply_window_icon(window_like: Any) -> bool:
    icon_path = resolve_app_icon_path()
    if icon_path is None:
        return False
    applied = False
    for target in _candidate_targets(window_like):
        if _apply_icon_to_target(target, icon_path):
            applied = True
    return applied


def apply_window_icon_later(window_like: Any) -> None:
    apply_window_icon(window_like)
    for target in _candidate_targets(window_like):
        if hasattr(target, "after"):
            try:
                target.after(0, lambda win=window_like: apply_window_icon(win))
                target.after(150, lambda win=window_like: apply_window_icon(win))
                target.after(450, lambda win=window_like: apply_window_icon(win))
                break
            except Exception:
                continue
