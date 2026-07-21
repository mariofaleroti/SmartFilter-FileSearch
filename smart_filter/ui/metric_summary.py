from __future__ import annotations

from typing import Any


def build_metric_summary_values(summary: Any) -> dict[str, int]:
    """Return the six executive metrics shown after a search.

    ``Caracteres`` communicates the actual text volume processed and is easier
    to interpret than the internal match-location counter. Successful reader
    executions are preferred over attempted executions so ``Leídos`` remains
    semantically correct.
    """

    scan_stats = dict(getattr(summary, "scan_stats", {}) or {})
    analyzed_count = int(getattr(summary, "analyzed_candidates_count", 0) or 0)

    candidates_count = scan_stats.get("candidates_count")
    if candidates_count is None:
        candidates_count = analyzed_count

    readers_succeeded = scan_stats.get("reader_succeeded_count")
    if readers_succeeded is None:
        readers_succeeded = scan_stats.get("readers_executed_count")
    if readers_succeeded is None:
        readers_succeeded = analyzed_count

    issues_count = scan_stats.get("issues_count")
    if issues_count is None:
        issues_count = len(getattr(summary, "errors", []) or [])

    return {
        "candidates": int(candidates_count or 0),
        "readers": int(readers_succeeded or 0),
        "matched_files": int(getattr(summary, "matched_candidates_count", 0) or 0),
        "characters": int(scan_stats.get("content_text_chars_count") or 0),
        "no_match": int(getattr(summary, "no_match_count", 0) or 0),
        "errors": int(issues_count or 0),
    }

def build_incident_status_palette(*, issues_count: int, is_light: bool) -> dict[str, str]:
    """Return persistent red status colors for the Incidencias card.

    Zero issues keeps a subdued red identity, while one or more issues uses a
    stronger alert treatment. Separate palettes preserve contrast in light and
    dark appearance modes.
    """

    has_issues = int(issues_count or 0) > 0
    if is_light:
        if has_issues:
            return {
                "fg": "#fee2e2",
                "border": "#dc2626",
                "text": "#7f1d1d",
                "title": "#991b1b",
            }
        return {
            "fg": "#fff7f7",
            "border": "#fca5a5",
            "text": "#7f1d1d",
            "title": "#991b1b",
        }

    if has_issues:
        return {
            "fg": "#3b1818",
            "border": "#ef4444",
            "text": "#ffffff",
            "title": "#fecaca",
        }
    return {
        "fg": "#26181b",
        "border": "#7f1d1d",
        "text": "#f8fafc",
        "title": "#fca5a5",
    }
