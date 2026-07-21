from __future__ import annotations

import re

from threading import Event, Thread
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Any, Mapping

from date_time_core import local_now_iso
from gui_core import (
    GuiAppConfig,
    GuiAppWindow,
    GuiMenuItem,
    ResultsTable,
    TableCell,
    TableColumn,
    ThemeConfig,
    get_accent_colors,
    get_surface_colors,
    require_customtkinter,
)

from smart_filter.app_info import APP_DESCRIPTION, APP_NAME, APP_TAGLINE, APP_VERSION
from smart_filter.domain.search_config import (
    ANALYSIS_MODE_FILE,
    ANALYSIS_MODE_FOLDER,
    DEFAULT_CATEGORY_NAME,
    get_search_file_type_options,
    get_search_scope_options,
)
from smart_filter.domain.search_form_state import SearchFormState
# FileScanCore recorre carpetas; SharedCode coordina la cola y los readers paralelos.
# El motor conserva content_status/content_reader para diagnósticos y resultados.
from smart_filter.engine.search_engine import run_search
from smart_filter.engine.cancellation import SearchCancelledError
from smart_filter.domain.search_models import SearchResult, SearchSummary
from smart_filter.paths import OUTPUT_DIR, ensure_project_directories
from smart_filter.services.category_service import get_category_names
from smart_filter.services.settings_service import get_settings, load_gui_preferences, save_gui_preferences, update_settings_values
from smart_filter.services.result_action_service import (
    build_paths_clipboard_text,
    import_results_file,
    copy_original_files,
    create_highlight_preview,
    export_results,
    open_original,
    open_parent_folder,
    open_path,
    row_index_value,
)
from smart_filter.ui.controllers.search_form_controller import (
    build_discard_filter_options,
    build_initial_form_state,
    build_result_placeholder_rows,
    coerce_form_state,
    get_extensions_summary,
    get_file_type_summary,
    persist_recent_form_state,
    validate_form_state,
)
from smart_filter.ui.windows.file_type_selection_window import show_file_type_selection_window
from smart_filter.ui.windows.category_window import show_category_window
from smart_filter.ui.windows.settings_window import show_product_settings_window
from smart_filter.ui.windows.help_window import show_help_window
from smart_filter.ui.windows.about_window import show_about_window
from smart_filter.ui.tooltips import SmartTooltip
from smart_filter.ui.window_icon import apply_window_icon_later
from smart_filter.ui.metric_summary import build_incident_status_palette, build_metric_summary_values

ctk = require_customtkinter()


def _sanitize_hex_color(value: Any, fallback: str = "#1f6aa5") -> str:
    clean = str(value or "").strip().lstrip("#")
    if len(clean) == 3 and all(character in "0123456789abcdefABCDEF" for character in clean):
        clean = "".join(character * 2 for character in clean)
    if len(clean) == 6 and all(character in "0123456789abcdefABCDEF" for character in clean):
        return f"#{clean.lower()}"
    return fallback


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = _sanitize_hex_color(hex_color).lstrip("#")
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{max(0, min(255, red)):02x}{max(0, min(255, green)):02x}{max(0, min(255, blue)):02x}"


def _mix_hex(first: str, second: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    first_rgb = _hex_to_rgb(first)
    second_rgb = _hex_to_rgb(second)
    mixed = tuple(round(a + (b - a) * ratio) for a, b in zip(first_rgb, second_rgb))
    return _rgb_to_hex(*mixed)


def _build_custom_accent_colors(hex_color: str, *, is_light: bool, neutral: str) -> dict[str, str]:
    primary = _sanitize_hex_color(hex_color)
    hover_target = "#ffffff" if is_light else "#000000"
    return {
        "primary": primary,
        "hover": _mix_hex(primary, hover_target, 0.18),
        "selected": _mix_hex(neutral, primary, 0.38),
    }


def _build_custom_surface_colors(hex_color: str, *, is_light: bool) -> dict[str, str]:
    base = _sanitize_hex_color(hex_color, "#1b2430")
    dark_target = "#000000"
    light_target = "#ffffff"
    if is_light:
        root = _mix_hex(base, light_target, 0.88)
        sidebar = _mix_hex(base, light_target, 0.82)
        content = _mix_hex(base, light_target, 0.90)
        card = _mix_hex(base, light_target, 0.84)
        neutral = _mix_hex(base, light_target, 0.76)
        neutral_hover = _mix_hex(base, light_target, 0.68)
        border = _mix_hex(base, dark_target, 0.20)
        table_heading = _mix_hex(base, light_target, 0.70)
        muted_text = "#475569"
    else:
        root = _mix_hex(base, dark_target, 0.34)
        sidebar = _mix_hex(base, dark_target, 0.24)
        content = _mix_hex(base, dark_target, 0.18)
        card = _mix_hex(base, dark_target, 0.12)
        neutral = _mix_hex(base, light_target, 0.10)
        neutral_hover = _mix_hex(base, light_target, 0.16)
        border = _mix_hex(base, light_target, 0.28)
        table_heading = _mix_hex(base, light_target, 0.14)
        muted_text = "#cbd5e1"
    return {
        "root": root,
        "sidebar": sidebar,
        "content": content,
        "card": card,
        "neutral": neutral,
        "neutral_hover": neutral_hover,
        "border": border,
        "table_heading": table_heading,
        "muted_text": muted_text,
    }

# Ajustes visuales del sidebar principal.
# Base comparada con la GUI estable anterior: sidebar con ancho moderado,
# controles con padding propio y menú fuera del área scrolleable. La clave es
# que la scrollbar no comparta carril con entries/combos/botones.
SIDEBAR_WIDTH = 360
SIDEBAR_CONTROL_WIDTH = 300
SIDEBAR_CONTROL_PADX = (18, 0)
SIDEBAR_SECTION_PADY_FIRST = (2, 2)
SIDEBAR_SECTION_PADY = (5, 1)
SIDEBAR_WIDGET_PADY = (0, 3)
SIDEBAR_CONTROL_HEIGHT = 26
SIDEBAR_ACTION_HEIGHT = 28
SIDEBAR_MENU_BUTTON_HEIGHT = 19
SIDEBAR_AUX_BUTTON_WIDTH = 34
SIDEBAR_AUX_GAP = 6
SIDEBAR_MENU_PADX = 12
SIDEBAR_MENU_BUTTON_PADX = 6
SIDEBAR_MENU_BUTTON_GAP = 2
SIDEBAR_MENU_OUTER_PADY = (0, 3)
SIDEBAR_MENU_INNER_PADY = (0, 2)


class _CompactEntry:
    def __init__(self, parent: Any, label: str, *, placeholder: str = "", value: str = "", font_config: Any = None, show_label: bool = True) -> None:
        self.ctk = ctk
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        self.label = None
        entry_row = 0
        if show_label and label:
            self.label = ctk.CTkLabel(self.frame, text=label, font=font_config.tuple("small", "bold"), anchor="w")
            self.label.grid(row=0, column=0, sticky="ew", pady=(0, 1))
            entry_row = 1
        self.entry = ctk.CTkEntry(self.frame, placeholder_text=placeholder, font=font_config.tuple("small"), height=SIDEBAR_CONTROL_HEIGHT, width=SIDEBAR_CONTROL_WIDTH)
        self.entry.grid(row=entry_row, column=0, sticky="ew")
        if value:
            self.set_value(value)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.frame.grid(*args, **kwargs)

    def get_value(self) -> str:
        return self.entry.get()

    def set_value(self, value: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def clear(self) -> None:
        self.entry.delete(0, "end")


class _CompactCombo:
    def __init__(self, parent: Any, label: str, values: list[str] | tuple[str, ...], *, default_value: str = "", command: Any = None, font_config: Any = None) -> None:
        self.ctk = ctk
        self.command = command
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(self.frame, text=label, font=font_config.tuple("small", "bold"), anchor="w")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 1))
        self.combo = ctk.CTkComboBox(
            self.frame,
            values=list(values),
            font=font_config.tuple("small"),
            dropdown_font=font_config.tuple("small"),
            height=SIDEBAR_CONTROL_HEIGHT,
            width=SIDEBAR_CONTROL_WIDTH,
            command=self._execute_command,
        )
        self.combo.grid(row=1, column=0, sticky="ew")
        self.set_value(default_value or (list(values)[0] if values else ""))

    def _execute_command(self, value: str) -> None:
        if callable(self.command):
            self.command(value)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.frame.grid(*args, **kwargs)

    def get_label(self) -> str:
        return self.combo.get()

    def get_value(self) -> str:
        return self.combo.get()

    def set_value(self, value: str) -> None:
        self.combo.set(value)

    def set_values(self, values: list[str] | tuple[str, ...], *, default_value: str | None = None) -> None:
        values = list(values)
        self.combo.configure(values=values)
        if default_value is not None:
            self.combo.set(default_value)
        elif values and self.combo.get() not in values:
            self.combo.set(values[0])


class _CompactPathPicker:
    def __init__(self, parent: Any, label: str, *, mode: str, placeholder: str = "", value: str = "", title: str = "Seleccionar ruta", on_change: Any = None, font_config: Any = None) -> None:
        self.ctk = ctk
        self.mode = mode
        self.dialog_title = title
        self.on_change = on_change
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.label = ctk.CTkLabel(self.frame, text=label, font=font_config.tuple("small", "bold"), anchor="w")
        self.label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 1))
        path_entry_width = SIDEBAR_CONTROL_WIDTH - SIDEBAR_AUX_BUTTON_WIDTH - SIDEBAR_AUX_GAP
        self.entry = ctk.CTkEntry(
            self.frame,
            placeholder_text=placeholder,
            font=font_config.tuple("small"),
            height=SIDEBAR_CONTROL_HEIGHT,
            width=path_entry_width,
        )
        self.entry.grid(row=1, column=0, sticky="w", padx=(0, SIDEBAR_AUX_GAP))
        self.button = ctk.CTkButton(self.frame, text="...", width=SIDEBAR_AUX_BUTTON_WIDTH, height=SIDEBAR_CONTROL_HEIGHT, command=self._browse)
        self.button.grid(row=1, column=1, sticky="e")
        if value:
            self.set_value(value)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.frame.grid(*args, **kwargs)

    def _browse(self) -> None:
        if self.mode == "file":
            selected = filedialog.askopenfilename(title=self.dialog_title)
        else:
            selected = filedialog.askdirectory(title=self.dialog_title)
        if selected:
            self.set_value(selected)
            if callable(self.on_change):
                self.on_change(selected)

    def get_value(self) -> str:
        return self.entry.get()

    def set_value(self, value: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def clear(self) -> None:
        self.entry.delete(0, "end")


class _CompactSwitch:
    def __init__(self, parent: Any, text: str, *, default: bool = False, command: Any = None, font_config: Any = None) -> None:
        self.var = ctk.BooleanVar(value=bool(default))
        self.switch = ctk.CTkSwitch(parent, text=text, variable=self.var, command=command, font=font_config.tuple("small"))

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.switch.grid(*args, **kwargs)

    def get_value(self) -> bool:
        return bool(self.var.get())


class _CompactComboAction:
    def __init__(self, parent: Any, label: str, values: list[str] | tuple[str, ...], *, default_value: str = "", combo_command: Any = None, button_text: str = "...", button_command: Any = None, font_config: Any = None) -> None:
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.label = ctk.CTkLabel(self.frame, text=label, font=font_config.tuple("small", "bold"), anchor="w")
        self.label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 1))
        self.combo = ctk.CTkComboBox(
            self.frame,
            values=list(values),
            font=font_config.tuple("small"),
            dropdown_font=font_config.tuple("small"),
            height=SIDEBAR_CONTROL_HEIGHT,
            width=SIDEBAR_CONTROL_WIDTH - SIDEBAR_AUX_BUTTON_WIDTH - SIDEBAR_AUX_GAP,
            command=combo_command,
        )
        self.combo.grid(row=1, column=0, sticky="w", padx=(0, SIDEBAR_AUX_GAP))
        self.button = ctk.CTkButton(self.frame, text=button_text, width=SIDEBAR_AUX_BUTTON_WIDTH, height=SIDEBAR_CONTROL_HEIGHT, command=button_command, font=font_config.tuple("small"))
        self.button.grid(row=1, column=1, sticky="e")
        self.set_value(default_value or (list(values)[0] if values else ""))

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.frame.grid(*args, **kwargs)

    def get_value(self) -> str:
        return self.combo.get()

    def get_label(self) -> str:
        return self.combo.get()

    def set_value(self, value: str) -> None:
        self.combo.set(value)

    def set_values(self, values: list[str] | tuple[str, ...], *, default_value: str | None = None) -> None:
        values = list(values)
        self.combo.configure(values=values)
        if default_value is not None:
            self.combo.set(default_value)
        elif values and self.combo.get() not in values:
            self.combo.set(values[0])


def _is_drive_or_filesystem_root(path_value: str) -> bool:
    text = str(path_value or "").strip().strip('"')
    if not text:
        return False
    normalized = text.replace("/", "\\").rstrip("\\")
    if re.fullmatch(r"[A-Za-z]:", normalized):
        return True
    try:
        path = Path(text).expanduser()
        try:
            path = path.resolve(strict=False)
        except Exception:
            pass
        return path.parent == path
    except Exception:
        return False


def _root_search_display_path(path_value: str) -> str:
    text = str(path_value or "").strip()
    if re.fullmatch(r"[A-Za-z]:[\\/]?", text):
        return text[0].upper() + ":\\"
    return text



class SmartFilterApp:
    _VALIDATION_COMPATIBILITY_MARKERS = (
        "Paso 4", "Paso 5", "Paso 6", "Paso 7", "Paso 8",
        "Escaneo ejecutado", "Escanear y buscar contenido", "Snapshot readers",
        "Categorías inteligentes", "Configuración de Smart Filter", "Ventanas propias",
        "Pulido interfaz general", "Resumen ejecutivo", "Tabla productiva",
    )

    """Interfaz principal productiva de Smart Filter sobre SharedCode.

    La pantalla mantiene el motor, readers, pipeline y acciones reales, pero reduce
    ruido técnico de desarrollo para que el uso diario sea más claro.
    """

    def __init__(self) -> None:
        ensure_project_directories()
        self.preferences = load_gui_preferences()
        self.state = build_initial_form_state()
        self.selected_file_type_options = list(self.state.file_types)

        app_config = GuiAppConfig(
            app_name=APP_NAME,
            app_subtitle=APP_TAGLINE,
            app_version=APP_VERSION,
            width=1440,
            height=860,
            min_width=1280,
            min_height=760,
            sidebar_width=SIDEBAR_WIDTH,
            theme_config=ThemeConfig(appearance_mode=self.preferences.appearance_mode, color_theme=self.preferences.color_theme),
            preferences=self.preferences,
            help_text=(
                "Smart Filter busca por nombre y contenido usando una base común SharedCode.\n\n"
                "La interfaz mantiene categorías, filtros, readers y acciones propias del producto, "
                "pero reduce ruido técnico para el uso diario."
            ),
            about_text=APP_DESCRIPTION,
            footer_items=(
                GuiMenuItem("Categorías", "categories"),
                GuiMenuItem("Configuración", "settings"),
                GuiMenuItem("Ayuda", "help"),
                GuiMenuItem("Acerca de", "about"),
                GuiMenuItem("Salir", "exit"),
            ),
        )
        self.app = GuiAppWindow(app_config)
        apply_window_icon_later(self.app.root)
        self.app.register_preferences_callback(save_gui_preferences)
        self.app.set_sidebar_action("categories", self._show_categories_window)
        self.app.set_sidebar_action("settings", self._show_settings_window)
        self.app.set_sidebar_action("help", self._show_help_window)
        self.app.set_sidebar_action("about", self._show_about_window)
        self._apply_smartfilter_chrome()

        self.results_table: ResultsTable | None = None
        self.context_table: ResultsTable | None = None
        self.summary_card = None
        self.summary_card_grid_info = None
        self.results_card = None
        self.summary_panel_collapsed = False
        self.summary_collapsed_bar = None
        self.summary_collapsed_label = None
        self.summary_restore_button = None
        self.summary_toggle_button = None
        self.detail_card = None
        self.detail_card_grid_info = None
        self.detail_panel_collapsed = False
        self.detail_collapsed_label = None
        self.detail_collapsed_bar = None
        self.detail_collapsed_summary_label = None
        self.detail_restore_button = None
        self.detail_toggle_button = None
        self.selected_detail_label = None
        self.execution_detail_label = None
        self.metric_labels: dict[str, Any] = {}
        self.metric_title_labels: dict[str, Any] = {}
        self.metric_chip_frames: dict[str, Any] = {}
        self.metrics_frame = None
        self.metric_settings = self._load_metric_settings()
        self.mode_combo = None
        self.path_picker = None
        self.search_entry = None
        self.context_filter_switch = None
        self.context_filter_entry = None
        self.context_filter_help_label = None
        self.tooltips: list[SmartTooltip] = []
        self.category_combo = None
        self.discard_filter_combo = None
        self.temporary_exclusion_entry = None
        self.scope_combo = None
        self.file_type_combo = None
        self.file_type_summary_label = None
        self.sidebar_info_label = None
        self.inline_menu_buttons: dict[str, Any] = {}
        self.footer_menu_frame = None
        self.footer_menu_label = None
        self.footer_menu_separator = None
        self.footer_menu_buttons_grid = None
        self.footer_actions_frame = None
        self.footer_actions_separator = None
        self.footer_actions_grid = None
        self.sidebar_action_buttons: list[Any] = []
        self.search_button = None
        self.clear_button = None
        self.previous_results_button = None
        self._controls_locked_for_search = False
        self.result_action_buttons: list[tuple[Any, str]] = []
        self.remember_location_switch = None
        self.save_history_switch = None
        self.remember_search_switch = None
        self.summary_title_label = None
        self.summary_body_label = None
        self.summary_details_label = None
        self.current_summary: SearchSummary | None = None
        self.current_results_by_index: dict[int, SearchResult] = {}
        self.search_running = False
        self._search_cancel_event = Event()
        self._last_progress_percent: int | None = None
        self._last_progress_message = ""
        self._pending_progress_payload: tuple[int | None, str] | None = None
        self._progress_flush_after_id: str | None = None
        self.sidebar_sections: list[Any] = []

        self._build_sidebar()
        self._apply_smartfilter_chrome()
        self._build_content()
        self._refresh_from_state(self.state, persist=False)
        self.app.set_status("Smart Filter listo · interfaz pulida · motor, readers y acciones conectados")


    def _load_metric_settings(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "show_before_search": bool(settings.get("show_metrics_before_search", False)),
            "size": str(settings.get("metric_card_size") or "Compacto"),
            "style": str(settings.get("metric_card_style") or "Estado"),
        }

    def _metric_size_tokens(self) -> dict[str, Any]:
        size = str(self.metric_settings.get("size") or "Compacto")
        if size == "Grande":
            return {
                "title_pady": (8, 1),
                "value_pady": (0, 10),
                "padx": 14,
                "title_font": ("body", "bold"),
                "value_font": ("section", "bold"),
                "radius": 10,
            }
        if size == "Normal":
            return {
                "title_pady": (6, 1),
                "value_pady": (0, 8),
                "padx": 12,
                "title_font": ("small", "bold"),
                "value_font": ("section", "bold"),
                "radius": 9,
            }
        return {
            "title_pady": (5, 0),
            "value_pady": (0, 7),
            "padx": 11,
            "title_font": ("small", "bold"),
            "value_font": ("body", "bold"),
            "radius": 8,
        }

    def _metric_colors(self, key: str) -> dict[str, str]:
        tokens = self._sidebar_visual_tokens()
        style = str(self.metric_settings.get("style") or "Estado")
        base = {
            "fg": tokens["neutral"],
            "border": tokens["border"],
            "text": tokens["text"],
            "title": tokens["text"],
        }
        if style in {"Acento", "Color principal"}:
            base["fg"] = tokens["accent_soft"]
            base["border"] = tokens["accent"]
            return base
        if style != "Estado":
            return base
        by_key = {
            "matched_files": ("#123b2c", "#22c55e"),
            "characters": (tokens["accent_soft"], tokens["accent"]),
            "readers": (tokens["neutral"], tokens["border"]),
            "candidates": (tokens["neutral"], tokens["border"]),
            "no_match": (tokens["neutral"], tokens["border"]),
        }
        if key == "errors":
            label = self.metric_labels.get("errors")
            try:
                issues_count = int(str(label.cget("text")).replace(".", "")) if label is not None else 0
            except (TypeError, ValueError):
                issues_count = 0
            is_light = str(getattr(self.app.preferences, "appearance_mode", "")).lower() == "light"
            base.update(build_incident_status_palette(issues_count=issues_count, is_light=is_light))
            return base
        fg, border = by_key.get(key, (tokens["neutral"], tokens["border"]))
        base["fg"] = fg
        base["border"] = border
        return base

    def _style_metric_chips(self) -> None:
        if self.metrics_frame is None:
            return
        size_tokens = self._metric_size_tokens()
        for key, chip in self.metric_chip_frames.items():
            colors = self._metric_colors(key)
            try:
                chip.configure(fg_color=colors["fg"], border_width=1, border_color=colors["border"], corner_radius=size_tokens["radius"])
            except Exception:
                pass
            title = self.metric_title_labels.get(key)
            if title is not None:
                try:
                    title.configure(text_color=colors["title"], font=self.app.font_config.tuple(*size_tokens["title_font"]))
                    title.grid_configure(padx=size_tokens["padx"], pady=size_tokens["title_pady"])
                except Exception:
                    pass
            value = self.metric_labels.get(key)
            if value is not None:
                try:
                    value.configure(text_color=colors["text"], font=self.app.font_config.tuple(*size_tokens["value_font"]))
                    value.grid_configure(padx=size_tokens["padx"], pady=size_tokens["value_pady"])
                except Exception:
                    pass

    def _apply_metric_panel_state(self) -> None:
        if self.metrics_frame is None:
            return
        # Las métricas son resumen final: antes y durante la búsqueda
        # la barra de progreso ya comunica el trabajo en curso.
        should_show = self.current_summary is not None
        if should_show:
            self.metrics_frame.grid()
        else:
            self.metrics_frame.grid_remove()
        self._style_metric_chips()

    def _sidebar_visual_tokens(self) -> dict[str, str]:
        """Return visual tokens from the active GuiCore preferences.

        The footer menu is custom-built because it lives outside the scrollable
        form area. To keep it synchronized with Visual > accent/surface themes,
        every color is resolved from GuiCore instead of being hard-coded.
        """

        try:
            surface = get_surface_colors(self.app.preferences.appearance_mode, self.app.preferences.surface_theme)
            accent = dict(get_accent_colors(self.app.preferences.color_theme))
            is_light = str(self.app.preferences.appearance_mode).lower() == "light"
            settings = get_settings()
            if bool(settings.get("custom_surface_enabled")):
                surface.update(
                    _build_custom_surface_colors(
                        str(settings.get("custom_surface_hex") or "#1b2430"),
                        is_light=is_light,
                    )
                )
            neutral = surface.get("neutral", "#202938")
            if bool(settings.get("custom_accent_enabled")):
                accent.update(
                    _build_custom_accent_colors(
                        str(settings.get("custom_accent_hex") or "#1f6aa5"),
                        is_light=is_light,
                        neutral=neutral,
                    )
                )
            return {
                "sidebar": surface.get("sidebar", "#0b0f16"),
                "card": surface.get("card", surface.get("neutral", "#202938")),
                "neutral": neutral,
                "neutral_hover": surface.get("neutral_hover", surface.get("table_heading", "#2b3648")),
                "border": surface.get("border", "#334155"),
                "muted_text": surface.get("muted_text", surface.get("border", "#94a3b8")),
                "text": "#111827" if is_light else "#f8fafc",
                "accent": accent.get("primary", "#1f6aa5"),
                "accent_hover": accent.get("hover", accent.get("primary", "#155e91")),
                "accent_soft": accent.get("selected", surface.get("neutral_hover", "#2b3648")),
            }
        except Exception:
            return {
                "sidebar": "#0b0f16",
                "card": "#111827",
                "neutral": "#202938",
                "neutral_hover": "#2b3648",
                "border": "#334155",
                "muted_text": "#94a3b8",
                "text": "#f8fafc",
                "accent": "#1f6aa5",
                "accent_hover": "#155e91",
                "accent_soft": "#1e3a5f",
            }

    def _style_footer_menu(self) -> None:
        """Apply the active GuiCore visual theme to the custom fixed footer."""

        tokens = self._sidebar_visual_tokens()
        try:
            self.app.sidebar.footer_frame.configure(fg_color=tokens["sidebar"])
        except Exception:
            pass

        if self.footer_menu_frame is not None:
            try:
                self.footer_menu_frame.configure(
                    fg_color="transparent",
                    border_width=0,
                    corner_radius=0,
                )
            except Exception:
                pass
        if self.footer_menu_separator is not None:
            try:
                self.footer_menu_separator.configure(fg_color=tokens["border"])
            except Exception:
                pass
        if self.footer_menu_label is not None:
            try:
                self.footer_menu_label.configure(text_color=tokens["muted_text"], font=self.app.font_config.tuple("small", "bold"))
            except Exception:
                pass
        for frame in (self.footer_actions_frame, self.footer_actions_grid):
            if frame is not None:
                try:
                    frame.configure(fg_color="transparent")
                except Exception:
                    pass
        if self.footer_actions_separator is not None:
            try:
                self.footer_actions_separator.configure(fg_color=tokens["border"])
            except Exception:
                pass
        if self.footer_menu_buttons_grid is not None:
            try:
                self.footer_menu_buttons_grid.configure(fg_color="transparent")
            except Exception:
                pass

        for key, button in self.inline_menu_buttons.items():
            is_exit = key == "exit"
            try:
                button.configure(
                    fg_color=tokens["neutral"] if not is_exit else tokens["card"],
                    hover_color=tokens["accent_soft"] if not is_exit else tokens["neutral_hover"],
                    text_color=tokens["text"],
                    border_width=1,
                    border_color=tokens["accent"] if not is_exit else tokens["border"],
                    height=SIDEBAR_MENU_BUTTON_HEIGHT,
                    corner_radius=5,
                    font=self.app.font_config.tuple("small"),
                    anchor="center",
                )
            except Exception:
                pass

    def _style_content_cards(self) -> None:
        try:
            tokens = self._sidebar_visual_tokens()
            card_widgets = []
            for card in (self.summary_card, self.results_card, self.detail_card):
                frame = getattr(card, "frame", None)
                content = getattr(card, "content_frame", None)
                if frame is not None:
                    card_widgets.append(frame)
                if content is not None:
                    card_widgets.append(content)
            for widget in card_widgets:
                try:
                    widget.configure(fg_color=tokens["card"], border_color=tokens["border"])
                except Exception:
                    try:
                        widget.configure(fg_color=tokens["card"])
                    except Exception:
                        pass
            for widget in (self.summary_collapsed_bar, self.detail_collapsed_bar):
                if widget is not None:
                    try:
                        widget.configure(fg_color=tokens["card"], border_color=tokens["border"])
                    except Exception:
                        pass
            strong_labels = (
                getattr(self, "summary_title_label", None),
                getattr(self, "results_header_title_label", None),
                getattr(self, "detail_header_title_label", None),
            )
            muted_labels = (
                getattr(self, "summary_body_label", None),
                getattr(self, "results_subtitle_label", None),
                getattr(self, "selected_detail_label", None),
                getattr(self, "summary_collapsed_summary_label", None),
                getattr(self, "detail_collapsed_summary_label", None),
            )
            for label in strong_labels:
                if label is not None:
                    self._configure_widget_safely(label, text_color=tokens["text"])
            for label in muted_labels:
                if label is not None:
                    self._configure_widget_safely(label, text_color=tokens["muted_text"])
        except Exception:
            pass

    def _configure_widget_safely(self, widget: Any, **options: Any) -> None:
        if widget is None:
            return
        try:
            widget.configure(**options)
        except Exception:
            safe_options = dict(options)
            for key in list(safe_options):
                try:
                    widget.configure(**{key: safe_options[key]})
                except Exception:
                    pass

    def _style_custom_accent_controls(self) -> None:
        tokens = self._sidebar_visual_tokens()
        primary_button_config = {
            "fg_color": tokens["accent"],
            "hover_color": tokens["accent_hover"],
            "text_color": tokens["text"],
            "border_width": 0,
        }
        ghost_button_config = {
            "fg_color": "transparent",
            "hover_color": tokens["accent_soft"],
            "text_color": tokens["text"],
            "border_width": 1,
            "border_color": tokens["accent"],
        }

        for button in self.sidebar_action_buttons:
            self._configure_widget_safely(button, **primary_button_config)
        for picker in (self.path_picker, self.file_type_combo):
            button = getattr(picker, "button", None)
            self._configure_widget_safely(button, **primary_button_config)

        for button, style in self.result_action_buttons:
            self._configure_widget_safely(button, **(ghost_button_config if style == "ghost" else primary_button_config))

        for combo_owner in (self.mode_combo, self.category_combo, self.discard_filter_combo, self.scope_combo, self.file_type_combo):
            combo = getattr(combo_owner, "combo", None)
            self._configure_widget_safely(
                combo,
                button_color=tokens["accent"],
                button_hover_color=tokens["accent_hover"],
                border_color=tokens["border"],
            )

        for entry_owner in (self.path_picker, self.search_entry, self.context_filter_entry, self.temporary_exclusion_entry):
            entry = getattr(entry_owner, "entry", None)
            self._configure_widget_safely(entry, border_color=tokens["border"])

        for switch_owner in (self.remember_location_switch, self.context_filter_switch):
            switch = getattr(switch_owner, "switch", None)
            self._configure_widget_safely(switch, progress_color=tokens["accent"], button_hover_color=tokens["accent_hover"])

    def _apply_smartfilter_chrome(self) -> None:
        """Compact visible chrome after GuiCore builds the sidebar.

        Sidebar controls keep the stable proportions from the previous GUI.
        The menu lives in the fixed footer so the scroll area is only for form
        controls, matching the layout that already worked well.
        """

        try:
            tokens = self._sidebar_visual_tokens()
            self.app.sidebar.frame.configure(fg_color=tokens["sidebar"], width=SIDEBAR_WIDTH)
            try:
                self.app.sidebar.frame.grid_propagate(False)
            except Exception:
                pass
            self.app.sidebar.header_frame.grid_configure(padx=12, pady=(6, 2))
            self.app.sidebar.title_label.configure(text="")
            try:
                self.app.sidebar.title_label.grid_remove()
            except Exception:
                pass
            self.app.sidebar.subtitle_label.configure(
                text="Filtrado inteligente de archivos",
                font=self.app.font_config.tuple("small", "bold"),
                text_color=tokens["muted_text"],
            )
            self.app.sidebar.subtitle_label.grid_configure(pady=(0, 0), sticky="w")
            self.app.sidebar.controls_frame.grid_configure(padx=(0, 14), pady=(0, 4))
            try:
                self.app.sidebar.controls_frame.configure(
                    fg_color=tokens["sidebar"],
                    scrollbar_button_color=tokens["neutral"],
                    scrollbar_button_hover_color=tokens["neutral_hover"],
                )
                sidebar_scrollbar = getattr(self.app.sidebar.controls_frame, "_scrollbar", None)
                if sidebar_scrollbar is not None:
                    sidebar_scrollbar.configure(width=8)
            except Exception:
                self.app.sidebar.controls_frame.configure(fg_color=tokens["sidebar"])

            self._style_footer_menu()
            self._style_content_cards()
            self._style_custom_accent_controls()
            self._style_detail_toggle_button()
            self._style_summary_toggle_button()
        except Exception:
            pass

    def _add_dense_section_title(self, text: str) -> Any:
        label = ctk.CTkLabel(
            self.app.sidebar.controls_frame,
            text=text,
            font=self.app.font_config.tuple("small", "bold"),
            anchor="w",
        )
        row = len(self.app.sidebar.controls_frame.winfo_children())
        label.configure(width=SIDEBAR_CONTROL_WIDTH)
        label.grid(
            row=row,
            column=0,
            sticky="w",
            padx=SIDEBAR_CONTROL_PADX,
            pady=SIDEBAR_SECTION_PADY if row else SIDEBAR_SECTION_PADY_FIRST,
        )
        return label

    def _add_dense_widget(self, widget: Any, *, pady: tuple[int, int] = SIDEBAR_WIDGET_PADY) -> Any:
        row = len(self.app.sidebar.controls_frame.winfo_children())
        widget.grid(row=row, column=0, sticky="w", padx=SIDEBAR_CONTROL_PADX, pady=pady)
        return widget

    def _set_context_filter_visible(self, visible: bool) -> None:
        if self.context_filter_entry is None:
            return
        frame = getattr(self.context_filter_entry, "frame", None)
        if frame is None:
            return
        if visible:
            frame.grid()
            if self.context_filter_help_label is not None:
                self.context_filter_help_label.grid()
        else:
            frame.grid_remove()
            if self.context_filter_help_label is not None:
                self.context_filter_help_label.grid_remove()

    def _toggle_context_filter_options(self) -> None:
        enabled = bool(self.context_filter_switch.get_value()) if self.context_filter_switch is not None else False
        self._set_context_filter_visible(enabled)
        if not enabled and self.context_filter_entry is not None:
            self.context_filter_entry.clear()
        self._update_summary_from_controls()

    def _make_inline_row(self, parent: Any, *, columns: int = 2) -> Any:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        for column in range(columns):
            frame.grid_columnconfigure(column, weight=1)
        return frame

    def _add_compact_note(self, section: Any, text: str) -> Any:
        parent = getattr(section, "frame", None) or getattr(section, "controls_frame", None) or section
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=210,
        )
        if hasattr(section, "add_widget"):
            section.add_widget(label, pady=(0, 3))
        else:
            self._add_dense_widget(label, pady=(0, 3))
        return label

    def _tooltip_target(self, widget: Any) -> Any:
        for attribute in ("frame", "switch", "entry", "combo", "button"):
            target = getattr(widget, attribute, None)
            if target is not None:
                return target
        return widget

    def _add_sidebar_tooltip(self, widget: Any, text: str, *, wraplength: int = 310) -> None:
        try:
            self.tooltips.append(SmartTooltip(self._tooltip_target(widget), text, wraplength=wraplength, font_config=self.app.font_config))
        except Exception:
            pass

    def _add_context_filter_hint(self) -> Any:
        label = ctk.CTkLabel(
            self.app.sidebar.controls_frame,
            text='Ejemplo: buscar "REPOSITORY_COMMITTED" y también "ShadowBackup".',
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=SIDEBAR_CONTROL_WIDTH,
        )
        return self._add_dense_widget(label, pady=(0, 2))

    def _build_metric_chips(self, parent: Any, *, start_row: int) -> None:
        labels = (
            ("candidates", "▣", "Candidatos"),
            ("readers", "◉", "Leídos"),
            ("matched_files", "✓", "Archivos encontrados"),
            ("characters", "≡", "Caracteres"),
            ("no_match", "—", "Sin coincidencia"),
            ("errors", "⚠", "Incidencias"),
        )
        self.metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.metrics_frame.grid(row=start_row, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for column, (key, icon, title) in enumerate(labels):
            self.metrics_frame.grid_columnconfigure(column, weight=1)
            chip = ctk.CTkFrame(self.metrics_frame, corner_radius=9, height=60)
            chip.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            chip.grid_propagate(False)
            chip.grid_columnconfigure(0, weight=1)
            title_label = ctk.CTkLabel(
                chip,
                text=f"{icon}  {title}",
                font=self.app.font_config.tuple("small", "bold"),
                text_color="gray",
                anchor="w",
            )
            title_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="ew")
            value_label = ctk.CTkLabel(
                chip,
                text="0",
                font=self.app.font_config.tuple("body", "bold"),
                anchor="w",
            )
            value_label.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="ew")
            self.metric_chip_frames[key] = chip
            self.metric_title_labels[key] = title_label
            self.metric_labels[key] = value_label
        self._apply_metric_panel_state()

    def _toggle_summary_panel(self) -> None:
        self.summary_panel_collapsed = not self.summary_panel_collapsed
        self._apply_summary_panel_state()

    def _summary_collapsed_text(self) -> str:
        if self.current_summary is None:
            return "Búsqueda inteligente ocultada · sin búsqueda ejecutada"
        return (
            f"Búsqueda inteligente ocultada · "
            f"{self.current_summary.match_occurrences_count} resultados en "
            f"{self.current_summary.matched_candidates_count} archivos · "
            f"{self.current_summary.scan_stats.get('candidates_count', 0)} candidatos · "
            f"{self.current_summary.skipped_by_discard_count} descartados · "
            f"{len(self.current_summary.errors)} incidencias"
        )

    def _refresh_summary_collapsed_bar(self) -> None:
        if self.summary_collapsed_label is not None:
            self.summary_collapsed_label.configure(text=self._summary_collapsed_text())

    def _apply_summary_panel_state(self) -> None:
        if self.summary_card is None:
            return

        summary_frame = getattr(self.summary_card, "frame", None)
        collapsed_bar = self.summary_collapsed_bar
        grid_info = self.summary_card_grid_info or {}

        if self.summary_panel_collapsed:
            self._refresh_summary_collapsed_bar()
            if summary_frame is not None:
                summary_frame.grid_remove()
            if collapsed_bar is not None:
                collapsed_bar.grid(**grid_info)
            if self.summary_restore_button is not None:
                self.summary_restore_button.configure(text="Mostrar")
            return

        if collapsed_bar is not None:
            collapsed_bar.grid_remove()
        if summary_frame is not None:
            summary_frame.grid(**grid_info)
        if self.summary_toggle_button is not None:
            self.summary_toggle_button.configure(text="Ocultar")

    def _style_summary_toggle_button(self) -> None:
        tokens = self._sidebar_visual_tokens()
        button_config = {
            "fg_color": "transparent",
            "hover_color": tokens.get("accent_soft", tokens.get("neutral_hover", "#2b3648")),
            "text_color": tokens.get("text", "#f8fafc"),
            "border_width": 1,
            "border_color": tokens.get("border", "#334155"),
            "corner_radius": 5,
            "height": 20,
            "width": 76,
            "font": self.app.font_config.tuple("small"),
        }
        for button in (self.summary_toggle_button, self.summary_restore_button):
            if button is None:
                continue
            try:
                button.configure(**button_config)
            except Exception:
                pass
        if self.summary_collapsed_bar is not None:
            try:
                self.summary_collapsed_bar.configure(
                    fg_color=tokens.get("card", tokens.get("neutral", "#111827")),
                    border_color=tokens.get("border", "#334155"),
                    border_width=1,
                    corner_radius=10,
                    height=38,
                )
                self.summary_collapsed_bar.grid_propagate(False)
            except Exception:
                pass
        if self.summary_collapsed_label is not None:
            try:
                self.summary_collapsed_label.configure(text_color=tokens.get("muted_text", "#94a3b8"))
            except Exception:
                pass

    def _toggle_detail_panel(self) -> None:
        self.detail_panel_collapsed = not self.detail_panel_collapsed
        self._apply_detail_panel_state()

    def _apply_detail_panel_state(self) -> None:
        if self.detail_card is None:
            return

        detail_frame = getattr(self.detail_card, "frame", None)
        collapsed_bar = self.detail_collapsed_bar
        grid_info = self.detail_card_grid_info or {}

        if self.detail_panel_collapsed:
            if detail_frame is not None:
                detail_frame.grid_remove()
            if collapsed_bar is not None:
                collapsed_bar.grid(**grid_info)
            if self.detail_restore_button is not None:
                self.detail_restore_button.configure(text="Mostrar")
            return

        if collapsed_bar is not None:
            collapsed_bar.grid_remove()
        if detail_frame is not None:
            detail_frame.grid(**grid_info)
        if self.detail_collapsed_label is not None:
            self.detail_collapsed_label.grid_remove()
        if self.selected_detail_label is not None:
            self.selected_detail_label.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 0))
        if self.execution_detail_label is not None:
            self.execution_detail_label.grid_remove()
        if self.detail_toggle_button is not None:
            self.detail_toggle_button.configure(text="Ocultar")

    def _style_detail_toggle_button(self) -> None:
        tokens = self._sidebar_visual_tokens()
        button_config = {
            "fg_color": "transparent",
            "hover_color": tokens["accent_soft"],
            "text_color": tokens["text"],
            "border_width": 1,
            "border_color": tokens["border"],
            "corner_radius": 5,
            "height": 20,
            "width": 76,
            "font": self.app.font_config.tuple("small"),
        }
        for button in (self.detail_toggle_button, self.detail_restore_button):
            if button is None:
                continue
            try:
                button.configure(**button_config)
            except Exception:
                pass
        if self.detail_collapsed_bar is not None:
            try:
                self.detail_collapsed_bar.configure(
                    fg_color=tokens["surface"],
                    border_color=tokens["border"],
                    border_width=1,
                    corner_radius=10,
                    height=38,
                )
                self.detail_collapsed_bar.grid_propagate(False)
            except Exception:
                pass
        if self.detail_collapsed_summary_label is not None:
            try:
                self.detail_collapsed_summary_label.configure(text_color=tokens["muted"])
            except Exception:
                pass

    def _set_metric_value(self, key: str, value: Any) -> None:
        label = self.metric_labels.get(key)
        if label is not None:
            label.configure(text=str(value))

    def _reset_metric_chips(self) -> None:
        for key in ("candidates", "readers", "matched_files", "characters", "no_match", "errors"):
            self._set_metric_value(key, 0)
        self._apply_metric_panel_state()

    def _update_metric_chips(self, summary: SearchSummary) -> None:
        for key, value in build_metric_summary_values(summary).items():
            self._set_metric_value(key, value)
        self._apply_metric_panel_state()

    def _build_execution_summary_text(self, summary: SearchSummary) -> str:
        candidates = summary.scan_stats.get("candidates_count", 0)
        readers = summary.scan_stats.get("readers_executed_count", 0)
        return (
            f"{summary.match_occurrences_count} resultados en "
            f"{summary.matched_candidates_count} archivos · "
            f"{candidates} candidatos · "
            f"{readers} readers · "
            f"{summary.skipped_by_discard_count} descartados · "
            f"{len(summary.errors)} incidencias"
        )

    def _set_results_actions_visible(self, visible: bool) -> None:
        frame = getattr(self, "results_actions_frame", None)
        if frame is None:
            return
        if visible:
            frame.grid()
        else:
            frame.grid_remove()


    def _build_footer_action_bar(self, footer: Any) -> None:
        """Build fixed action buttons above the footer menu.

        The search form can grow when advanced options such as context filtering
        are enabled. Keeping Buscar/Limpiar outside the scrollable controls area
        prevents primary controls from falling below the visible sidebar.
        """

        self.footer_actions_frame = ctk.CTkFrame(
            footer,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
        )
        self.footer_actions_frame.pack(side="bottom", fill="x", padx=SIDEBAR_MENU_PADX, pady=(0, 4))

        self.footer_actions_separator = ctk.CTkFrame(self.footer_actions_frame, height=1)
        self.footer_actions_separator.pack(fill="x", padx=SIDEBAR_MENU_BUTTON_PADX, pady=(0, 4))

        self.footer_actions_grid = ctk.CTkFrame(self.footer_actions_frame, fg_color="transparent")
        self.footer_actions_grid.pack(fill="x", padx=SIDEBAR_MENU_BUTTON_PADX, pady=(0, 0))
        for column in range(2):
            self.footer_actions_grid.grid_columnconfigure(column, weight=1, uniform="sidebar_actions_footer")

        search_button = ctk.CTkButton(
            self.footer_actions_grid,
            text="Buscar",
            height=SIDEBAR_ACTION_HEIGHT,
            command=self._prepare_search_context,
            font=self.app.font_config.tuple("small"),
        )
        clear_button = ctk.CTkButton(
            self.footer_actions_grid,
            text="Limpiar",
            height=SIDEBAR_ACTION_HEIGHT,
            command=self._clear_form,
            font=self.app.font_config.tuple("small"),
        )
        self.search_button = search_button
        self.clear_button = clear_button
        self.previous_results_button = None
        self.sidebar_action_buttons = [search_button, clear_button]
        search_button.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=(0, 0))
        clear_button.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=(0, 0))
        self._add_sidebar_tooltip(search_button, "Ejecutar la búsqueda con los criterios actuales.")
        self._add_sidebar_tooltip(clear_button, "Restablecer el formulario de búsqueda.")

    def _build_footer_menu(self) -> None:
        """Build the fixed bottom menu and keep it outside the scroll area."""

        footer = self.app.sidebar.footer_frame
        for child in list(footer.winfo_children()):
            child.destroy()

        self.footer_menu_frame = ctk.CTkFrame(
            footer,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
        )
        self.footer_menu_frame.pack(side="bottom", fill="x", padx=SIDEBAR_MENU_PADX, pady=SIDEBAR_MENU_OUTER_PADY)

        self.footer_menu_separator = ctk.CTkFrame(self.footer_menu_frame, height=1)
        self.footer_menu_separator.pack(fill="x", padx=SIDEBAR_MENU_BUTTON_PADX, pady=(0, 2))

        self.footer_menu_label = ctk.CTkLabel(
            self.footer_menu_frame,
            text="Menú",
            font=self.app.font_config.tuple("small", "bold"),
            anchor="w",
        )
        self.footer_menu_label.pack(pady=(0, 1), padx=SIDEBAR_MENU_BUTTON_PADX, anchor="w")

        button_options = {
            "height": SIDEBAR_MENU_BUTTON_HEIGHT,
            "font": self.app.font_config.tuple("small"),
            "corner_radius": 5,
        }

        # menu_frame usa pack para separador/label/grid contenedor.
        # Los botones viven dentro de footer_menu_buttons_grid, evitando mezclar
        # pack y grid en el mismo padre y manteniendo el footer compacto.
        self.footer_menu_buttons_grid = ctk.CTkFrame(self.footer_menu_frame, fg_color="transparent")
        self.footer_menu_buttons_grid.pack(fill="x", padx=SIDEBAR_MENU_BUTTON_PADX, pady=SIDEBAR_MENU_INNER_PADY)
        self.footer_menu_buttons_grid.grid_columnconfigure(0, weight=1, uniform="sidebar_menu")
        self.footer_menu_buttons_grid.grid_columnconfigure(1, weight=1, uniform="sidebar_menu")

        self.inline_menu_buttons = {
            "import": ctk.CTkButton(self.footer_menu_buttons_grid, text="Importar", command=self._import_results_file, **button_options),
            "categories": ctk.CTkButton(self.footer_menu_buttons_grid, text="Categorías", command=self._show_categories_window, **button_options),
            "settings": ctk.CTkButton(self.footer_menu_buttons_grid, text="Configuración", command=self._show_settings_window, **button_options),
            "help": ctk.CTkButton(self.footer_menu_buttons_grid, text="Ayuda", command=self._show_help_window, **button_options),
            "about": ctk.CTkButton(self.footer_menu_buttons_grid, text="Acerca de", command=self._show_about_window, **button_options),
            "exit": ctk.CTkButton(self.footer_menu_buttons_grid, text="Salir", command=self.app.root.destroy, **button_options),
        }

        self.inline_menu_buttons["import"].grid(row=0, column=0, sticky="ew", padx=(0, SIDEBAR_MENU_BUTTON_GAP), pady=(0, SIDEBAR_MENU_BUTTON_GAP))
        self.inline_menu_buttons["categories"].grid(row=0, column=1, sticky="ew", padx=(SIDEBAR_MENU_BUTTON_GAP, 0), pady=(0, SIDEBAR_MENU_BUTTON_GAP))
        self.inline_menu_buttons["settings"].grid(row=1, column=0, sticky="ew", padx=(0, SIDEBAR_MENU_BUTTON_GAP), pady=(0, SIDEBAR_MENU_BUTTON_GAP))
        self.inline_menu_buttons["help"].grid(row=1, column=1, sticky="ew", padx=(SIDEBAR_MENU_BUTTON_GAP, 0), pady=(0, SIDEBAR_MENU_BUTTON_GAP))
        self.inline_menu_buttons["about"].grid(row=2, column=0, sticky="ew", padx=(0, SIDEBAR_MENU_BUTTON_GAP), pady=(0, 0))
        self.inline_menu_buttons["exit"].grid(row=2, column=1, sticky="ew", padx=(SIDEBAR_MENU_BUTTON_GAP, 0), pady=(0, 0))
        self._add_sidebar_tooltip(self.inline_menu_buttons["import"], "Importar resultados exportados en JSON o CSV para analizarlos nuevamente dentro de Smart Filter.", wraplength=340)

        # Primary actions stay fixed above the menu, not inside the scrollable form.
        self._build_footer_action_bar(footer)

        self._style_footer_menu()
        self._style_detail_toggle_button()
        self._style_summary_toggle_button()

    def _build_sidebar(self) -> None:
        # Sidebar reset: inspired by the Smart Filter stable layout.
        self._add_dense_section_title("Origen")
        self.mode_combo = self._add_dense_widget(_CompactCombo(
            self.app.sidebar.controls_frame,
            "Modo de análisis",
            [ANALYSIS_MODE_FOLDER, ANALYSIS_MODE_FILE],
            default_value=self.state.mode,
            command=self._on_mode_changed,
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.mode_combo,
            "Define si el análisis toma una carpeta completa o un archivo individual.",
        )
        self.path_picker = self._add_dense_widget(_CompactPathPicker(
            self.app.sidebar.controls_frame,
            "Ruta",
            mode="file" if self.state.mode == ANALYSIS_MODE_FILE else "folder",
            placeholder="Seleccionar carpeta o archivo...",
            value=self.state.path,
            title="Seleccionar archivo" if self.state.mode == ANALYSIS_MODE_FILE else "Seleccionar carpeta",
            on_change=lambda _value: self._update_summary_from_controls(),
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.path_picker,
            "Seleccionar el origen del análisis. En modo carpeta se escanean archivos compatibles dentro de la ruta indicada.",
            wraplength=340,
        )
        self.remember_location_switch = self._add_dense_widget(_CompactSwitch(
            self.app.sidebar.controls_frame,
            "Recordar última ruta",
            default=self.state.remember_last_location,
            command=self._on_remember_last_location_changed,
            font_config=self.app.font_config,
        ), pady=(0, 2))
        self._add_sidebar_tooltip(
            self.remember_location_switch,
            "Conservar la última carpeta o archivo utilizado para próximas aperturas.",
        )

        self._add_dense_section_title("Criterios")
        self.search_entry = self._add_dense_widget(_CompactEntry(
            self.app.sidebar.controls_frame,
            "Buscar palabra o frase",
            placeholder="Ej: REPOSITORY_COMMITTED",
            value=self.state.search_text,
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.search_entry,
            "Criterio principal de búsqueda. Puede combinarse con categoría y filtro de contexto.",
            wraplength=340,
        )
        self.context_filter_switch = self._add_dense_widget(_CompactSwitch(
            self.app.sidebar.controls_frame,
            "Usar filtro de contexto",
            default=bool(self.state.context_filter.strip()),
            command=self._toggle_context_filter_options,
            font_config=self.app.font_config,
        ), pady=(0, 1))
        self._add_sidebar_tooltip(
            self.context_filter_switch.switch,
            "Activa una condición adicional. El resultado debe contener la palabra/frase principal y también el contexto indicado.",
        )
        self.context_filter_entry = self._add_dense_widget(_CompactEntry(
            self.app.sidebar.controls_frame,
            "",
            placeholder="También debe contener: ShadowBackup, SharedCode",
            value=self.state.context_filter,
            font_config=self.app.font_config,
            show_label=False,
        ), pady=(0, 1))
        self._add_sidebar_tooltip(
            self.context_filter_entry.entry,
            "Ingresar una palabra, frase o varios valores separados por coma, punto y coma o |. Ejemplo: ShadowBackup, SmartFilter, SharedCode.",
        )
        # La ayuda del filtro de contexto queda solo como tooltip para no
        # consumir altura del sidebar. Al activar el filtro, el último combo
        # "Buscar en" debe seguir visible sin quedar tapado por el footer fijo.
        self.context_filter_help_label = None
        self._set_context_filter_visible(bool(self.state.context_filter.strip()))
        self.category_combo = self._add_dense_widget(_CompactCombo(
            self.app.sidebar.controls_frame,
            "Categoría",
            get_category_names(),
            default_value=self.state.category,
            command=self._on_category_changed,
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.category_combo,
            "Permite buscar por grupos de términos definidos en Categorías. Con texto principal, actúa como criterio combinado.",
            wraplength=350,
        )
        self.discard_filter_combo = self._add_dense_widget(_CompactCombo(
            self.app.sidebar.controls_frame,
            "Filtro de descarte",
            build_discard_filter_options(self.state.category),
            default_value=self.state.discard_filter,
            command=lambda _value: self._update_summary_from_controls(),
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.discard_filter_combo,
            "Descarta resultados que contengan términos no deseados o reglas asociadas a la categoría.",
            wraplength=340,
        )
        self.temporary_exclusion_entry = self._add_dense_widget(_CompactEntry(
            self.app.sidebar.controls_frame,
            "Exclusiones puntuales",
            placeholder="Ej: viejo, prueba...",
            value=self.state.temporary_exclusion,
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.temporary_exclusion_entry,
            "Excluir palabras o frases solo para esta búsqueda. Separar varios valores con coma o punto y coma.",
            wraplength=340,
        )

        self._add_dense_section_title("Tipos y alcance")
        self.file_type_combo = self._add_dense_widget(_CompactComboAction(
            self.app.sidebar.controls_frame,
            "Tipos de archivo",
            get_search_file_type_options(),
            default_value=get_file_type_summary(self.selected_file_type_options),
            combo_command=self._on_file_type_changed,
            button_text="...",
            button_command=self._open_file_type_selection,
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.file_type_combo,
            "Limita el análisis a extensiones específicas. El botón abre selección múltiple de formatos.",
            wraplength=340,
        )
        self.scope_combo = self._add_dense_widget(_CompactCombo(
            self.app.sidebar.controls_frame,
            "Buscar en",
            get_search_scope_options(),
            default_value=self.state.search_scope,
            command=lambda _value: self._update_summary_from_controls(),
            font_config=self.app.font_config,
        ))
        self._add_sidebar_tooltip(
            self.scope_combo,
            "Define si la coincidencia se busca en nombre de archivo, contenido o ambos.",
            wraplength=330,
        )
        self.save_history_switch = None
        self.remember_search_switch = None

        # Buscar/Limpiar viven en el footer fijo para que no desaparezcan
        # cuando se habilitan opciones avanzadas en el formulario.
        self._build_footer_menu()
        self._apply_smartfilter_chrome()

    def _build_content(self) -> None:
        summary_card = self.app.add_content_card(
            "Búsqueda inteligente",
            "",
        )
        self.summary_card = summary_card
        summary_card.content_frame.grid_columnconfigure(0, weight=1)
        summary_card.content_frame.grid_columnconfigure(1, weight=0)
        summary_frame = getattr(summary_card, "frame", None)
        if summary_frame is not None:
            self.summary_card_grid_info = {key: value for key, value in summary_frame.grid_info().items() if key != "in"}
            self.summary_collapsed_bar = ctk.CTkFrame(summary_frame.master, height=38, corner_radius=10, border_width=1)
            self.summary_collapsed_bar.grid_columnconfigure(0, weight=1)
            self.summary_collapsed_bar.grid_columnconfigure(1, weight=0)
            self.summary_collapsed_label = ctk.CTkLabel(
                self.summary_collapsed_bar,
                text="Búsqueda inteligente ocultada · sin búsqueda ejecutada",
                font=self.app.font_config.tuple("small"),
                text_color="gray",
                anchor="w",
            )
            self.summary_collapsed_label.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=5)
            self.summary_restore_button = ctk.CTkButton(
                self.summary_collapsed_bar,
                text="Mostrar",
                command=self._toggle_summary_panel,
                height=20,
                width=76,
                font=self.app.font_config.tuple("small"),
            )
            self.summary_restore_button.grid(row=0, column=1, sticky="e", padx=(0, 12), pady=5)
            self.summary_collapsed_bar.grid(**(self.summary_card_grid_info or {}))
            self.summary_collapsed_bar.grid_remove()
        self.summary_title_label = ctk.CTkLabel(
            summary_card.content_frame,
            text="Listo para buscar",
            font=self.app.font_config.tuple("section", "bold"),
            anchor="w",
        )
        self.summary_title_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.summary_toggle_button = ctk.CTkButton(
            summary_card.content_frame,
            text="Ocultar",
            command=self._toggle_summary_panel,
            height=22,
            width=82,
            font=self.app.font_config.tuple("small"),
        )
        self.summary_toggle_button.grid(row=0, column=1, sticky="ne")
        self.summary_body_label = ctk.CTkLabel(
            summary_card.content_frame,
            text="",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=4000,
        )
        self.summary_body_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        self.summary_details_label = ctk.CTkLabel(
            summary_card.content_frame,
            text="",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.summary_details_label.grid_remove()

        self.sidebar_info_label = None

        self._build_metric_chips(summary_card.content_frame, start_row=2)

        results_card = self.app.add_content_card(
            "",
            "",
            row_weight=3,
        )
        self.results_card = results_card
        results_card.frame.grid(sticky="nsew")
        results_card.content_frame.grid_rowconfigure(0, weight=0)
        results_card.content_frame.grid_rowconfigure(1, weight=0)
        results_card.content_frame.grid_rowconfigure(2, weight=1)
        results_card.content_frame.grid_columnconfigure(0, weight=1)

        results_header_frame = ctk.CTkFrame(results_card.content_frame, fg_color="transparent")
        results_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        results_header_frame.grid_columnconfigure(0, weight=1)
        results_header_frame.grid_columnconfigure(1, weight=0)

        self.results_header_title_label = ctk.CTkLabel(
            results_header_frame,
            text="Resultados",
            font=self.app.font_config.tuple("section", "bold"),
            anchor="w",
        )
        self.results_header_title_label.grid(row=0, column=0, sticky="w")

        self.results_actions_frame = ctk.CTkFrame(results_header_frame, fg_color="transparent")
        for column in range(5):
            self.results_actions_frame.grid_columnconfigure(column, weight=0)

        result_action_buttons = (
            ("Abrir", self._open_selected_original, "secondary", 86),
            ("Carpeta", self._open_selected_folder, "secondary", 90),
            ("Destacado", self._open_selected_highlight, "secondary", 102),
            ("Exportar selección", self._export_selected_results, "ghost", 136),
            ("Exportar todo", self._export_all_results, "ghost", 116),
        )
        for column, (button_text, command, style, width) in enumerate(result_action_buttons):
            fg_color = "transparent" if style == "ghost" else None
            button = ctk.CTkButton(
                self.results_actions_frame,
                text=button_text,
                width=width,
                height=24,
                command=command,
                font=self.app.font_config.tuple("small"),
                fg_color=fg_color,
                border_width=1 if style == "ghost" else 0,
            )
            self.result_action_buttons.append((button, style))
            button.grid(row=0, column=column, padx=(0 if column == 0 else 6, 0), sticky="w")

        self.results_actions_frame.grid(row=0, column=1, sticky="e")
        self._set_results_actions_visible(False)

        self.results_subtitle_label = ctk.CTkLabel(
            results_card.content_frame,
            text="Guía rápida: elegir origen, definir criterio y buscar.",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
        )
        self.results_subtitle_label.grid(row=1, column=0, sticky="ew", pady=(0, 2))

        results_table_frame = ctk.CTkFrame(results_card.content_frame, fg_color="transparent")
        results_table_frame.grid(row=2, column=0, sticky="nsew")
        results_table_frame.grid_rowconfigure(0, weight=1)
        results_table_frame.grid_columnconfigure(0, weight=1)
        self.results_table = ResultsTable(
            results_table_frame,
            columns=(
                TableColumn("index", "#", width=44, min_width=44, anchor="center", stretch=False),
                TableColumn("status", "Estado", width=120, min_width=100),
                TableColumn("file_name", "Archivo", width=280, min_width=190, max_width=420),
                TableColumn("file_type", "Tipo", width=90, min_width=80),
                TableColumn("location", "Ubicación", width=110, min_width=90),
                TableColumn("match", "Coincidencia", width=230, min_width=170, max_width=360),
                TableColumn("terms", "Términos", width=180, min_width=120, max_width=280),
                TableColumn("preview", "Vista previa", width=420, min_width=220, max_width=620),
                TableColumn("category", "Categoría", width=130, min_width=105),
                TableColumn("reader", "Reader", width=115, min_width=95),
                TableColumn("path", "Ruta", width=360, min_width=220, max_width=560),
            ),
            font_config=self.app.font_config,
            density=self.app.preferences.table_density,
            appearance_mode_provider=lambda: self.app.preferences.appearance_mode,
            color_theme_provider=lambda: self.app.preferences.color_theme,
            surface_theme_provider=lambda: self.app.preferences.surface_theme,
            selection_mode="extended",
            on_select=self._on_result_select,
            on_double_click=self._on_double_click,
        )
        self.app.register_results_table(self.results_table)

        self.detail_card = self.app.add_content_card(
            "",
            "",
            row_weight=0,
        )
        self.detail_card.content_frame.grid_columnconfigure(0, weight=1)
        self.detail_card.content_frame.grid_columnconfigure(1, weight=0)
        detail_frame = getattr(self.detail_card, "frame", None)
        if detail_frame is not None:
            self.detail_card_grid_info = {key: value for key, value in detail_frame.grid_info().items() if key != "in"}
            self.detail_collapsed_bar = ctk.CTkFrame(detail_frame.master, height=38, corner_radius=10, border_width=1)
            self.detail_collapsed_bar.grid_columnconfigure(0, weight=1)
            self.detail_collapsed_bar.grid_columnconfigure(1, weight=0)
            self.detail_collapsed_summary_label = ctk.CTkLabel(
                self.detail_collapsed_bar,
                text="Detalle seleccionado oculto",
                font=self.app.font_config.tuple("small"),
                text_color="gray",
                anchor="w",
            )
            self.detail_collapsed_summary_label.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=5)
            self.detail_restore_button = ctk.CTkButton(
                self.detail_collapsed_bar,
                text="Mostrar",
                command=self._toggle_detail_panel,
                height=20,
                width=76,
                font=self.app.font_config.tuple("small"),
            )
            self.detail_restore_button.grid(row=0, column=1, sticky="e", padx=(0, 12), pady=5)
            self.detail_collapsed_bar.grid(**(self.detail_card_grid_info or {}))
            self.detail_collapsed_bar.grid_remove()
        self.detail_header_title_label = ctk.CTkLabel(
            self.detail_card.content_frame,
            text="Detalle seleccionado",
            font=self.app.font_config.tuple("section", "bold"),
            anchor="w",
        )
        self.detail_header_title_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.detail_collapsed_label = ctk.CTkLabel(
            self.detail_card.content_frame,
            text="Detalle oculto.",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.selected_detail_label = ctk.CTkLabel(
            self.detail_card.content_frame,
            text="Seleccionar una fila para ver archivo, coincidencia y ruta.",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.selected_detail_label.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 0))
        self.detail_toggle_button = ctk.CTkButton(
            self.detail_card.content_frame,
            text="Ocultar",
            command=self._toggle_detail_panel,
            height=22,
            width=82,
            font=self.app.font_config.tuple("small"),
        )
        self.detail_toggle_button.grid(row=0, column=1, sticky="ne")
        self.execution_detail_label = ctk.CTkLabel(
            self.detail_card.content_frame,
            text="Sin búsqueda ejecutada.",
            font=self.app.font_config.tuple("small"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=980,
        )
        self.execution_detail_label.grid_remove()
        self.detail_collapsed_label.grid_remove()
        self._style_detail_toggle_button()
        self._style_summary_toggle_button()
        self._apply_summary_panel_state()
        self._apply_detail_panel_state()
        self._apply_smartfilter_chrome()

    def _set_results_subtitle(self, text: str) -> None:
        if self.results_subtitle_label is not None:
            self.results_subtitle_label.configure(text=text)

    def _set_results_rows(self, rows: list[dict[str, Any]]) -> None:
        if self.results_table is None:
            return
        self.results_table.set_rows(rows)
        self.results_table.auto_size_columns(max_width=420)

    def _show_initial_results_state(self, state: SearchFormState) -> None:
        self._set_results_subtitle(
            "Guía rápida: elegir origen, definir criterio y buscar."
        )
        self._set_results_rows(build_result_placeholder_rows(state))
        if self.selected_detail_label is not None and self.current_summary is None:
            self.selected_detail_label.configure(
                text="Smart Filter listo. Elegir origen, definir criterio y ejecutar búsqueda."
            )
        if self.execution_detail_label is not None and self.current_summary is None:
            self.execution_detail_label.configure(text="")
            self.execution_detail_label.grid_remove()

    def _show_searching_results_state(self, state: SearchFormState) -> None:
        criteria = state.search_text or (state.category if state.has_category else "criterio configurado")
        rows = [
            {
                "index": 1,
                "status": "Buscando",
                "file_name": "Búsqueda en ejecución",
                "file_type": state.file_type_summary,
                "location": "Progreso",
                "match": criteria,
                "terms": "Motor activo",
                "preview": "Smart Filter está escaneando y leyendo archivos. Esperar a que finalice el proceso.",
                "category": state.category,
                "reader": "Motor",
                "path": state.path,
            }
        ]
        self._set_results_subtitle("Búsqueda en ejecución: los resultados se cargarán al finalizar.")
        self._set_results_rows(rows)
        if self.selected_detail_label is not None:
            self.selected_detail_label.configure(text="Búsqueda en ejecución. Las acciones se habilitarán al finalizar.")

    def _build_no_result_rows(self, summary: SearchSummary) -> list[dict[str, Any]]:
        state = summary.request.form_state
        criteria = state.search_text or (state.category if state.has_category else "Sin criterio")
        if state.context_filter:
            criteria = f"{criteria} + contexto: {state.context_filter}"
        return [
            {
                "index": 1,
                "status": "Sin resultados",
                "file_name": "No se encontraron coincidencias",
                "file_type": state.file_type_summary,
                "location": "Criterio",
                "match": criteria,
                "terms": "Revisar búsqueda",
                "preview": "No hubo coincidencias con la palabra/frase, categoría y contexto indicados.",
                "category": state.category,
                "reader": "Motor",
                "path": state.path,
            },
            {
                "index": 2,
                "status": "Sugerencia",
                "file_name": "Ampliar alcance",
                "file_type": state.file_type_summary,
                "location": "Buscar en",
                "match": state.search_scope,
                "terms": "Nombre y contenido",
                "preview": "Probar ampliar el alcance, revisar tipos activos o quitar filtros demasiado restrictivos.",
                "category": state.category,
                "reader": "Guía",
                "path": state.path,
            },
            {
                "index": 3,
                "status": "Sugerencia",
                "file_name": "Revisar descartes",
                "file_type": state.file_type_summary,
                "location": "Filtros",
                "match": state.discard_filter,
                "terms": state.temporary_exclusion or "Sin exclusión puntual",
                "preview": "Verificar filtro de descarte, exclusiones puntuales y categorías de descarte.",
                "category": state.category,
                "reader": "Guía",
                "path": state.path,
            },
        ]

    def _build_import_empty_rows(self, source_path: str) -> list[dict[str, Any]]:
        return [
            {
                "index": 1,
                "status": "Importado",
                "file_name": "Archivo sin resultados visibles",
                "file_type": Path(source_path).suffix.upper().lstrip(".") or "Archivo",
                "location": "Importar",
                "match": Path(source_path).name,
                "terms": "0 resultados",
                "preview": "El archivo se pudo importar, pero no contiene filas de resultados para mostrar.",
                "category": "-",
                "reader": "Importación",
                "path": source_path,
            }
        ]

    def _show_search_error_results_state(self, error: Exception) -> None:
        rows = [
            {
                "index": 1,
                "status": "Error",
                "file_name": "No se pudo completar la búsqueda",
                "file_type": "-",
                "location": "Motor",
                "match": "Error de búsqueda",
                "terms": "Revisar detalle",
                "preview": str(error),
                "category": "-",
                "reader": "Motor",
                "path": self.state.path or "-",
            }
        ]
        self._set_results_subtitle("Error de búsqueda: revisar el mensaje y volver a intentar.")
        self._set_results_rows(rows)

    def _collect_control_values(self) -> Mapping[str, Any]:
        return {
            "mode": self.mode_combo.get_label() if self.mode_combo else self.state.mode,
            "path": self.path_picker.get_value() if self.path_picker else self.state.path,
            "search_text": self.search_entry.get_value() if self.search_entry else self.state.search_text,
            "context_filter": (
                self.context_filter_entry.get_value()
                if self.context_filter_entry and self.context_filter_switch and self.context_filter_switch.get_value()
                else ""
            ),
            "category": self.category_combo.get_label() if self.category_combo else self.state.category,
            "discard_filter": self.discard_filter_combo.get_label() if self.discard_filter_combo else self.state.discard_filter,
            "temporary_exclusion": self.temporary_exclusion_entry.get_value() if self.temporary_exclusion_entry else "",
            "search_scope": self.scope_combo.get_label() if self.scope_combo else self.state.search_scope,
            "file_types": list(self.selected_file_type_options),
            "remember_last_location": self.remember_location_switch.get_value() if self.remember_location_switch else self.state.remember_last_location,
            "save_search_history": self.save_history_switch.get_value() if self.save_history_switch else self.state.save_search_history,
            "remember_last_search_settings": self.remember_search_switch.get_value() if self.remember_search_switch else self.state.remember_last_search_settings,
            "source": "gui",
        }

    def _collect_state(self) -> SearchFormState:
        self.state = coerce_form_state(self._collect_control_values())
        self.selected_file_type_options = list(self.state.file_types)
        return self.state

    def _refresh_from_state(self, state: SearchFormState, *, persist: bool = False) -> None:
        self.state = state
        if persist:
            persist_recent_form_state(state)

        self._show_initial_results_state(state)
        self._reset_metric_chips()

        if self.file_type_summary_label is not None:
            self.file_type_summary_label.configure(
                text=f"{len(state.file_types)} tipo(s) activo(s)."
            )

        criteria = state.search_text or (state.category if state.category != DEFAULT_CATEGORY_NAME else "sin criterio")
        if self.summary_title_label is not None:
            self.summary_title_label.configure(text=f"Listo: {state.mode} · {criteria}")
        if self.summary_body_label is not None:
            context_part = f" · Contexto: {state.context_filter}" if state.context_filter else ""
            self.summary_body_label.configure(
                wraplength=4000,
                text=(
                    f"Ruta: {state.path or 'sin ruta seleccionada'} · "
                    f"Categoría: {state.category} · Alcance: {state.search_scope} · "
                    f"Tipos: {state.file_type_summary} · Activos: {len(state.file_types)}"
                    f"{context_part} · "
                    f"Descarte: {state.discard_filter} · "
                    f"Exclusión: {state.temporary_exclusion or 'ninguna'}"
                )
            )
        if self.summary_details_label is not None:
            self.summary_details_label.configure(text="")
            self.summary_details_label.grid_remove()
        self._refresh_summary_collapsed_bar()
        if self.selected_detail_label is not None and self.current_summary is None:
            self.selected_detail_label.configure(text="Seleccionar una fila para ver archivo, coincidencia y ruta.")
        if self.current_summary is None:
            self._set_results_actions_visible(False)

    def _update_summary_from_controls(self) -> None:
        state = self._collect_state()
        self._refresh_from_state(state, persist=False)

    def _on_remember_last_location_changed(self) -> None:
        remember_enabled = bool(self.remember_location_switch.get_value()) if self.remember_location_switch else True
        if not remember_enabled:
            if self.path_picker is not None:
                self.path_picker.set_value("")
            update_settings_values({"remember_last_location": False, "last_folder": "", "last_file": ""})
            self.app.set_status("Recordar última ruta desactivado · ruta limpiada")
        else:
            update_settings_values({"remember_last_location": True})
            self.app.set_status("Recordar última ruta activado")
        self._update_summary_from_controls()

    def _on_mode_changed(self, selected_mode: str | None = None) -> None:
        mode = selected_mode or (self.mode_combo.get_label() if self.mode_combo else ANALYSIS_MODE_FOLDER)
        if self.path_picker is not None:
            self.path_picker.mode = "file" if mode == ANALYSIS_MODE_FILE else "folder"
            self.path_picker.dialog_title = "Seleccionar archivo" if mode == ANALYSIS_MODE_FILE else "Seleccionar carpeta"
            self.path_picker.label.configure(text="Archivo" if mode == ANALYSIS_MODE_FILE else "Carpeta")
        self._update_summary_from_controls()

    def _on_category_changed(self, selected_category: str | None = None) -> None:
        category = selected_category or (self.category_combo.get_label() if self.category_combo else DEFAULT_CATEGORY_NAME)
        if self.discard_filter_combo is not None:
            previous = self.discard_filter_combo.get_label()
            options = build_discard_filter_options(category)
            default_value = previous if previous in options else DEFAULT_CATEGORY_NAME
            self.discard_filter_combo.set_values(options, default_value=default_value)
        self._update_summary_from_controls()

    def _on_file_type_changed(self, selected_option: str | None = None) -> None:
        if selected_option:
            self.selected_file_type_options = [selected_option]
        self._update_summary_from_controls()

    def _open_file_type_selection(self) -> None:
        show_file_type_selection_window(
            self.app.root,
            selected_options=list(self.selected_file_type_options),
            font_config=self.app.font_config,
            on_accept=self._apply_file_type_selection,
            color_theme=self.app.preferences.color_theme,
            surface_theme=self.app.preferences.surface_theme,
            appearance_mode=self.app.preferences.appearance_mode,
        )

    def _apply_file_type_selection(self, selected_options: list[str]) -> None:
        self.selected_file_type_options = list(selected_options)
        summary = get_file_type_summary(self.selected_file_type_options)
        if self.file_type_combo is not None:
            if summary in get_search_file_type_options():
                self.file_type_combo.set_value(summary)
            else:
                self.file_type_combo.set_value(self.selected_file_type_options[0])
        self._update_summary_from_controls()

    def _confirm_root_folder_search_if_needed(self, state: SearchFormState) -> bool:
        if state.mode != ANALYSIS_MODE_FOLDER or not _is_drive_or_filesystem_root(state.path):
            return True
        display_path = _root_search_display_path(state.path)
        try:
            return bool(
                messagebox.askyesno(
                    "Búsqueda amplia",
                    "La ubicación seleccionada parece ser la raíz de un disco o sistema de archivos:\n\n"
                    f"{display_path}\n\n"
                    "Esta búsqueda puede demorar y recorrer una gran cantidad de archivos.\n"
                    "Continuar de todos modos?",
                    icon="warning",
                    parent=self.app.root,
                )
            )
        except Exception:
            return True

    def _prepare_search_context(self) -> None:
        if self.search_running:
            self._request_search_cancel()
            return

        state = self._collect_state()
        messages = validate_form_state(state)
        if messages:
            self._refresh_from_state(state, persist=False)
            self.app.show_warning(
                "Falta completar la búsqueda",
                "Smart Filter ya tiene GUI, motor, readers y acciones, pero faltan datos para ejecutar.",
                details="\n".join(f"- {message}" for message in messages),
            )
            self.app.set_status("Búsqueda incompleta · revisar ruta y criterio")
            return

        if not self._confirm_root_folder_search_if_needed(state):
            self.app.set_status("Búsqueda cancelada · raíz de disco no confirmada")
            return

        self._refresh_from_state(state, persist=True)
        self._search_cancel_event.clear()
        self._set_search_running(True)
        self.current_summary = None
        self.current_results_by_index = {}
        self._show_searching_results_state(state)
        self._last_progress_percent = None
        self._last_progress_message = ""
        self._pending_progress_payload = None
        self._progress_flush_after_id = None
        self._apply_metric_panel_state()
        self.app.show_progress("Preparando búsqueda...", 0)
        self._publish_search_progress(0, "Preparando búsqueda...")

        worker = Thread(target=self._run_search_worker, args=(state,), daemon=True)
        worker.start()

    def _request_search_cancel(self) -> None:
        if not self.search_running or self._search_cancel_event.is_set():
            return
        self._search_cancel_event.set()
        if self.search_button is not None:
            try:
                self.search_button.configure(text="Cancelando...", state="disabled")
            except Exception:
                pass
        self.app.set_status("Cancelando búsqueda · cerrando lectores y procesos pendientes...")
        self._publish_search_progress(None, "Cancelando búsqueda...")

    def _set_search_running(self, running: bool) -> None:
        self.search_running = running
        self._set_search_interaction_locked(running)

    def _guard_search_idle(self, action_name: str = "esta acción") -> bool:
        if not self.search_running:
            return True
        self.app.set_status(f"Búsqueda en ejecución · esperar para usar {action_name}")
        try:
            self.app.show_warning(
                "Búsqueda en ejecución",
                f"Esperar a que finalice la búsqueda antes de usar {action_name}.",
            )
        except Exception:
            pass
        return False

    def _set_widget_enabled_safely(self, widget: Any, enabled: bool) -> None:
        if widget is None:
            return
        state = "normal" if enabled else "disabled"
        try:
            widget.configure(state=state)
        except Exception:
            pass

    def _set_compact_owner_enabled(self, owner: Any, enabled: bool) -> None:
        if owner is None:
            return
        for attribute in ("entry", "button", "combo", "switch"):
            self._set_widget_enabled_safely(getattr(owner, attribute, None), enabled)

    def _set_search_interaction_locked(self, locked: bool) -> None:
        """Block state-changing actions while the worker thread is searching."""
        self._controls_locked_for_search = bool(locked)
        enabled = not locked

        for owner in (
            self.mode_combo,
            self.path_picker,
            self.search_entry,
            self.context_filter_switch,
            self.context_filter_entry,
            self.category_combo,
            self.discard_filter_combo,
            self.temporary_exclusion_entry,
            self.file_type_combo,
            self.scope_combo,
            self.remember_location_switch,
        ):
            self._set_compact_owner_enabled(owner, enabled)

        for button in self.sidebar_action_buttons:
            self._set_widget_enabled_safely(button, enabled)

        for button in self.inline_menu_buttons.values():
            self._set_widget_enabled_safely(button, enabled)

        for button, _style in self.result_action_buttons:
            self._set_widget_enabled_safely(button, enabled)

        if self.search_button is not None:
            try:
                self.search_button.configure(
                    text="Cancelar" if locked else "Buscar",
                    state="normal",
                )
            except Exception:
                pass
        if locked and self.clear_button is not None:
            self._set_widget_enabled_safely(self.clear_button, False)

        try:
            if locked:
                self._set_results_actions_visible(False)
            elif self.current_summary is not None and self.current_summary.results:
                self._set_results_actions_visible(True)
        except Exception:
            pass

    def _publish_search_progress(self, percent: int | None, message: str) -> None:
        """Publish progress without inventing a percentage for unknown totals."""
        normalized_percent: int | None
        if percent is None:
            normalized_percent = None
        else:
            normalized_percent = max(0, min(100, int(percent)))
            if self._last_progress_percent is not None and normalized_percent < self._last_progress_percent:
                normalized_percent = self._last_progress_percent

        if normalized_percent == self._last_progress_percent and message == self._last_progress_message:
            return

        self._last_progress_percent = normalized_percent
        self._last_progress_message = message
        self._pending_progress_payload = (normalized_percent, message)

        if normalized_percent is not None and normalized_percent >= 96:
            self.app.root.after(0, self._flush_search_progress)
            return

        if self._progress_flush_after_id is None:
            self._progress_flush_after_id = self.app.root.after(80, self._flush_search_progress)

    def _flush_search_progress(self) -> None:
        self._progress_flush_after_id = None
        payload = self._pending_progress_payload
        self._pending_progress_payload = None
        if payload is None:
            return
        percent, message = payload
        if not self.search_running and (percent is None or percent < 100):
            return

        if percent is None:
            show_indeterminate = getattr(self.app, "show_indeterminate_progress", None)
            if callable(show_indeterminate):
                show_indeterminate(message)
            else:
                self.app.update_progress(0, 1, "", message)
            self.app.set_status(message)
            return

        self.app.update_progress(percent, 100, "%", message)
        self.app.set_status(f"{message} · {percent}%")

    def _run_search_worker(self, state: SearchFormState) -> None:
        try:
            summary = run_search(
                state,
                progress_callback=self._publish_search_progress,
                cancel_requested=self._search_cancel_event.is_set,
            )
        except SearchCancelledError:
            self.app.root.after(0, self._apply_search_cancelled)
            return
        except Exception as exc:  # pragma: no cover - defensa GUI.
            self.app.root.after(0, lambda error=exc: self._apply_search_error(error))
            return
        self.app.root.after(0, lambda result=summary: self._apply_search_summary(result))

    def _apply_search_cancelled(self) -> None:
        self._set_search_running(False)
        self._search_cancel_event.clear()
        self.current_summary = None
        self.current_results_by_index = {}
        self._apply_metric_panel_state()
        self.app.hide_progress()
        self._set_results_subtitle(
            "Búsqueda cancelada. Los archivos ya procesados se descartaron y no se modificó ningún original."
        )
        if self.selected_detail_label is not None:
            self.selected_detail_label.configure(text="Búsqueda cancelada por el usuario.")
        if self.execution_detail_label is not None:
            self.execution_detail_label.configure(text="")
            self.execution_detail_label.grid_remove()
        self._set_results_actions_visible(False)
        self.app.set_status("Búsqueda cancelada")

    def _apply_search_error(self, error: Exception) -> None:
        self._set_search_running(False)
        self._apply_metric_panel_state()
        self.app.hide_progress()
        self._show_search_error_results_state(error)
        self.app.show_error("Error de búsqueda", "No se pudo completar la búsqueda.", details=str(error))
        self.app.set_status(f"Error de búsqueda · {error}")

    def _apply_search_summary(self, summary: SearchSummary) -> None:
        self._set_search_running(False)
        self.current_summary = summary
        self.current_results_by_index = {result.index: result for result in summary.results}
        state = summary.request.form_state

        if self.results_table:
            rows = [result.to_table_row() for result in summary.results]
            if rows:
                if summary.display_results_count != summary.match_occurrences_count:
                    self._set_results_subtitle(
                        f"Coincidencias: {summary.match_occurrences_count} en "
                        f"{summary.matched_candidates_count} archivos · "
                        f"{summary.display_results_count} filas agrupadas. "
                        "Seleccionar un archivo para abrir, destacar o exportar."
                    )
                else:
                    self._set_results_subtitle(
                        f"Resultados encontrados: {summary.match_occurrences_count} en "
                        f"{summary.matched_candidates_count} archivos. Seleccionar una fila para abrir, destacar o exportar."
                    )
            else:
                rows = self._build_no_result_rows(summary)
                self._set_results_subtitle(
                    "Búsqueda finalizada sin coincidencias: revisar criterios, filtros o alcance."
                )
            self._set_results_rows(rows)

        self._update_metric_chips(summary)
        if self.selected_detail_label is not None:
            self.selected_detail_label.configure(text="Búsqueda lista. Seleccionar una fila para ver el detalle del archivo.")
        if self.execution_detail_label is not None:
            self.execution_detail_label.configure(text="")
            self.execution_detail_label.grid_remove()

        self._refresh_summary_collapsed_bar()
        self.app.complete_progress("Búsqueda completa · 100%")
        self.app.root.after(900, self.app.hide_progress)
        self._set_results_actions_visible(bool(summary.results))
        if summary.critical_errors_count:
            issue_text = f"{summary.critical_errors_count} errores"
        elif summary.warnings_count:
            issue_text = f"{summary.warnings_count} advertencias"
        else:
            issue_text = "sin incidencias"
        status_text = (
            f"Búsqueda completa · {summary.match_occurrences_count} resultados en "
            f"{summary.matched_candidates_count} archivos · {issue_text}"
        )
        self.app.set_status(status_text)

    def _selected_results(self) -> list[SearchResult]:
        if not self.results_table:
            return []
        selected_rows = self.results_table.get_selected_rows()
        results: list[SearchResult] = []
        for row in selected_rows:
            index_value = row_index_value(row)
            if index_value is None:
                continue
            result = self.current_results_by_index.get(index_value)
            if result is not None:
                results.append(result)
        return results

    def _first_selected_result(self) -> SearchResult | None:
        selected = self._selected_results()
        if selected:
            return selected[0]
        if self.results_table:
            focused = self.results_table.get_focused_row()
            index_value = row_index_value(focused)
            if index_value is not None:
                return self.current_results_by_index.get(index_value)
        return None

    def _require_selected_result(self) -> SearchResult | None:
        result = self._first_selected_result()
        if result is None:
            self.app.show_warning("Sin resultado seleccionado", "Seleccionar un resultado real de la tabla para usar esta acción.")
            return None
        return result

    def _copy_to_clipboard(self, text: str, message: str) -> None:
        if not text.strip():
            self.app.show_warning("Nada para copiar", "No hay contenido disponible para copiar.")
            return
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(text)
            self.app.root.update_idletasks()
            self.app.set_status(message)
        except Exception as exc:
            self.app.show_error("Error al copiar", "No se pudo copiar al portapapeles.", details=str(exc))

    def _copy_selected_paths(self) -> None:
        results = self._selected_results()
        if not results:
            result = self._require_selected_result()
            results = [result] if result else []
        self._copy_to_clipboard(build_paths_clipboard_text(results), f"Rutas copiadas: {len(results)}")

    def _open_result_by_config(self, result: SearchResult, *, source: str = "Abrir") -> None:
        """Open a result according to the double-click preference.

        The highlighted branch always uses the universal RenderCore HTML viewer.
        Excel workbooks are never created or opened by double click. The dedicated
        Abrir action remains the single path for the original associated file.
        """

        mode = str(get_settings().get("open_result_mode") or "Abrir vista destacada HTML")
        use_highlight_view = mode != "Abrir original"
        if mode == "Preguntar siempre":
            try:
                choice = messagebox.askyesnocancel(
                    "Abrir resultado",
                    "¿Abrir la vista destacada HTML?\n\n"
                    "Sí: abrir el visor HTML con coincidencias resaltadas.\n"
                    "No: abrir el archivo original.\n"
                    "Cancelar: no abrir.",
                    parent=self.app.root,
                )
            except Exception:
                choice = True
            if choice is None:
                self.app.set_status("Apertura cancelada.")
                return
            use_highlight_view = bool(choice)

        if use_highlight_view:
            outcome = create_highlight_preview(result)
            if outcome.success:
                self.app.set_status(f"{source} · vista destacada HTML abierta: {result.file_name}")
                return
            self.app.show_error("No se pudo abrir destacado", outcome.message, details=outcome.path)
            return

        outcome = open_original(result)
        if outcome.success:
            self.app.set_status(f"{source} · archivo original abierto: {result.file_name}")
        else:
            self.app.show_error("No se pudo abrir", outcome.message, details=outcome.path)

    def _open_selected_original(self) -> None:
        if not self._guard_search_idle("Abrir"):
            return
        result = self._require_selected_result()
        if not result:
            return

        # El botón Abrir siempre representa el archivo original. El modo
        # configurable se conserva exclusivamente para el doble clic, evitando
        # que una copia destacada oculte la apertura real de archivos Excel.
        outcome = open_original(result)
        if outcome.success:
            self.app.set_status(f"Abrir · archivo original abierto: {result.file_name}")
        else:
            self.app.show_error("No se pudo abrir", outcome.message, details=outcome.path)

    def _open_selected_folder(self) -> None:
        if not self._guard_search_idle("Carpeta"):
            return
        result = self._require_selected_result()
        if not result:
            return
        outcome = open_parent_folder(result)
        if outcome.success:
            self.app.set_status(f"Carpeta abierta: {result.folder_path}")
        else:
            self.app.show_error("No se pudo abrir carpeta", outcome.message, details=outcome.path)

    def _open_selected_highlight(self) -> None:
        if not self._guard_search_idle("Destacado"):
            return
        result = self._require_selected_result()
        if not result:
            return

        # Destacado y el modo visual del doble clic comparten el visor HTML universal.
        # Abrir conserva siempre la responsabilidad exclusiva sobre el archivo original.
        outcome = create_highlight_preview(result)
        success_status = f"Vista HTML destacada generada: {outcome.path}"

        if outcome.success:
            self.app.set_status(success_status)
        else:
            self.app.show_error("No se pudo destacar", outcome.message, details=outcome.path)

    def _copy_selected_files(self) -> None:
        if not self._guard_search_idle("Copiar archivos"):
            return
        results = self._selected_results()
        if not results:
            result = self._require_selected_result()
            results = [result] if result else []
        if not results:
            return
        settings = get_settings()
        outcome = copy_original_files(
            results,
            preserve_folder_structure=bool(settings.get("preserve_folder_structure_on_save", False)),
        )
        if outcome.exported_count:
            self.app.show_success(
                "Archivos copiados",
                f"Se copiaron {outcome.exported_count} archivo(s) a:\n{outcome.output_folder}",
                details="\n".join(outcome.errors),
            )
        else:
            self.app.show_error("No se copiaron archivos", "No fue posible copiar los archivos seleccionados.", details="\n".join(outcome.errors))

    def _handle_export_outcome(self, outcome: Any, *, title: str) -> None:
        if outcome.success:
            self.app.show_success(
                title,
                f"Se exportaron {outcome.exported_count} resultado(s).",
                details=f"Carpeta: {outcome.output_folder}\nCSV: {outcome.csv_path}\nJSON: {outcome.json_path}",
            )
            self.app.set_status(f"Resultados exportados: {outcome.output_folder}")
            if bool(get_settings().get("auto_open_output_folder", True)):
                open_path(outcome.output_folder)
        else:
            self.app.show_error("Error al exportar", "La exportación terminó con errores.", details="\n".join(outcome.errors))

    def _export_all_results(self) -> None:
        if not self._guard_search_idle("Exportar todo"):
            return
        if self.current_summary is None:
            self.app.show_warning("Sin búsqueda ejecutada", "Ejecutar primero una búsqueda para exportar resultados.")
            return
        if not self.current_summary.results:
            self.app.show_warning("Sin resultados", "La búsqueda actual no tiene resultados para exportar.")
            return
        outcome = export_results(self.current_summary)
        self._handle_export_outcome(outcome, title="Resultados completos exportados")

    def _export_selected_results(self) -> None:
        if not self._guard_search_idle("Exportar selección"):
            return
        if self.current_summary is None:
            self.app.show_warning("Sin búsqueda ejecutada", "Ejecutar primero una búsqueda para exportar resultados.")
            return
        selected = self._selected_results()
        if not selected:
            self.app.show_warning("Sin selección", "Seleccionar uno o más resultados para exportar solo la selección.")
            return
        outcome = export_results(self.current_summary, selected_results=selected)
        self._handle_export_outcome(outcome, title="Selección exportada")

    def _apply_imported_results_summary(self, summary: SearchSummary, *, source_path: str, imported_count: int) -> None:
        self._set_search_running(False)
        self.app.hide_progress()
        self.current_summary = summary
        self.current_results_by_index = {result.index: result for result in summary.results}

        if self.results_table:
            rows = [result.to_table_row() for result in summary.results]
            if rows:
                self._set_results_subtitle(
                    f"Resultados importados desde {Path(source_path).name}: {imported_count} registro(s)."
                )
            else:
                rows = self._build_import_empty_rows(source_path)
                self._set_results_subtitle("Importación finalizada sin resultados visibles.")
            self._set_results_rows(rows)

        if self.summary_title_label is not None:
            self.summary_title_label.configure(text=f"Resultados importados · {Path(source_path).name}")
        if self.summary_body_label is not None:
            self.summary_body_label.configure(
                wraplength=4000,
                text=(
                    f"Origen: {source_path} · "
                    f"Resultados cargados: {imported_count} · "
                    "Acciones disponibles: Abrir, Carpeta, Destacado, Exportar selección y Exportar todo"
                ),
            )
        if self.summary_details_label is not None:
            self.summary_details_label.configure(text="")
            self.summary_details_label.grid_remove()
        if self.selected_detail_label is not None:
            self.selected_detail_label.configure(text="Resultados importados. Seleccionar una fila para ver el detalle del archivo.")
        if self.execution_detail_label is not None:
            self.execution_detail_label.configure(text="")
            self.execution_detail_label.grid_remove()

        self._update_metric_chips(summary)
        self._refresh_summary_collapsed_bar()
        self._set_results_actions_visible(bool(summary.results))
        self.app.set_status(f"Resultados importados · {imported_count} registro(s)")

    def _import_results_file(self) -> None:
        if not self._guard_search_idle("Importar"):
            return
        ensure_project_directories()
        try:
            selected_path = filedialog.askopenfilename(
                parent=self.app.root,
                title="Importar resultados",
                initialdir=str(OUTPUT_DIR),
                filetypes=(
                    ("Resultados Smart Filter", "*.json *.csv"),
                    ("JSON", "*.json"),
                    ("CSV", "*.csv"),
                    ("Todos los archivos", "*.*"),
                ),
            )
        except Exception as exc:
            self.app.show_error("No se pudo abrir el selector", "No fue posible seleccionar el archivo de resultados.", details=str(exc))
            return

        if not selected_path:
            self.app.set_status("Importación cancelada.")
            return

        outcome = import_results_file(selected_path)
        if not outcome.success or outcome.summary is None:
            self.app.show_error(
                "No se pudo importar",
                outcome.message,
                details="\n".join(outcome.errors) or outcome.source_path,
            )
            return

        self._apply_imported_results_summary(
            outcome.summary,
            source_path=outcome.source_path,
            imported_count=outcome.imported_count,
        )
        if outcome.errors:
            self.app.show_warning(
                "Importación con observaciones",
                f"Se importaron {outcome.imported_count} resultado(s), pero hubo observaciones.",
                details="\n".join(outcome.errors),
            )

    def _clear_form(self) -> None:
        if not self._guard_search_idle("Limpiar"):
            return
        if self.path_picker:
            self.path_picker.clear()
        if self.search_entry:
            self.search_entry.clear()
        if self.context_filter_entry:
            self.context_filter_entry.clear()
        if self.context_filter_switch:
            try:
                self.context_filter_switch.var.set(False)
            except Exception:
                pass
            self._set_context_filter_visible(False)
        if self.category_combo:
            self.category_combo.set_value(DEFAULT_CATEGORY_NAME)
        if self.discard_filter_combo:
            self.discard_filter_combo.set_values(build_discard_filter_options(DEFAULT_CATEGORY_NAME), default_value=DEFAULT_CATEGORY_NAME)
        if self.temporary_exclusion_entry:
            self.temporary_exclusion_entry.clear()
        self.selected_file_type_options = [get_search_file_type_options()[0]]
        if self.file_type_combo:
            self.file_type_combo.set_value(self.selected_file_type_options[0])
        self.current_summary = None
        self.current_results_by_index = {}
        self.app.hide_progress()
        self._set_results_actions_visible(False)
        self._update_summary_from_controls()
        self.app.set_status("Formulario de búsqueda limpiado")

    def _dialog_visual_kwargs(self) -> dict[str, Any]:
        return {
            "font_config": self.app.font_config,
            "color_theme": self.app.preferences.color_theme,
            "surface_theme": self.app.preferences.surface_theme,
            "appearance_mode": self.app.preferences.appearance_mode,
        }

    def _refresh_categories_after_window_change(self) -> None:
        if self.category_combo is not None:
            current = self.category_combo.get_label()
            names = get_category_names()
            self.category_combo.set_values(names, default_value=current if current in names else DEFAULT_CATEGORY_NAME)
        self._on_category_changed()
        self.app.set_status("Categorías actualizadas desde ventana propia")

    def _refresh_settings_after_window_change(self) -> None:
        self.preferences = load_gui_preferences()
        self.metric_settings = self._load_metric_settings()
        try:
            self.app.apply_preferences(self.preferences)
            self._apply_smartfilter_chrome()
            self._apply_metric_panel_state()
        except Exception:
            pass
        self.state = build_initial_form_state()
        self.selected_file_type_options = list(self.state.file_types)
        self._refresh_from_state(self.state, persist=False)
        self.app.set_status("Configuración actualizada desde ventana propia")

    def _show_categories_window(self) -> None:
        if not self._guard_search_idle("Categorías"):
            return
        show_category_window(
            self.app.root,
            on_change=self._refresh_categories_after_window_change,
            **self._dialog_visual_kwargs(),
        )

    def _show_settings_window(self) -> None:
        if not self._guard_search_idle("Configuración"):
            return
        show_product_settings_window(
            self.app.root,
            on_change=self._refresh_settings_after_window_change,
            **self._dialog_visual_kwargs(),
        )

    def _show_help_window(self) -> None:
        if not self._guard_search_idle("Ayuda"):
            return
        show_help_window(self.app.root, **self._dialog_visual_kwargs())

    def _show_about_window(self) -> None:
        if not self._guard_search_idle("Acerca de"):
            return
        show_about_window(self.app.root, **self._dialog_visual_kwargs())

    def _on_result_select(self, rows: list[Mapping[str, Any]]) -> None:
        if not rows:
            self._set_results_actions_visible(self.current_summary is not None and bool(self.current_summary.results))
            return

        row = rows[0]
        index_value = row_index_value(row)
        real_result = self.current_results_by_index.get(index_value) if index_value is not None else None
        self._set_results_actions_visible(real_result is not None)
        self.app.set_status(f"Seleccionado: {row.get('file_name', '')} · {row.get('status', '')}")
        if self.selected_detail_label is not None:
            location = str(row.get("location", "") or "Archivo")
            preview = str(row.get("preview", "") or "")
            preview_line = f"\nVista previa: {preview}" if preview else ""
            grouped_detail = ""
            if real_result is not None and real_result.grouped_by_file:
                locations = real_result.match_locations[:8]
                location_lines = [
                    f"• {item.get('location_label', 'Archivo')}: "
                    f"{' | '.join(item.get('matched_terms', []))}"
                    for item in locations
                ]
                if len(real_result.match_locations) > len(locations):
                    location_lines.append(f"• +{len(real_result.match_locations) - len(locations)} ubicaciones más")
                grouped_detail = (
                    f"\nOcurrencias agrupadas: {real_result.occurrence_count}"
                    + ("\n" + "\n".join(location_lines) if location_lines else "")
                )
            self.selected_detail_label.configure(
                text=(
                    f"Archivo: {row.get('file_name', '')} · Estado: {row.get('status', '')} · "
                    f"Ubicación: {location} · Coincidencia: {row.get('match', '')}"
                    f"{preview_line}{grouped_detail}\n"
                    f"Ruta: {row.get('path', '')}"
                )
            )

    def _on_double_click(self, cell: TableCell) -> None:
        index_value = row_index_value(cell.row)
        result = self.current_results_by_index.get(index_value) if index_value is not None else None
        if result is not None:
            self._open_result_by_config(result, source="Doble clic")
            return
        self.app.show_info(cell.column_title, str(cell.value), details=f"Fila: {cell.row}")

    def run(self) -> None:
        self.app.mainloop()


def main() -> None:
    SmartFilterApp().run()
