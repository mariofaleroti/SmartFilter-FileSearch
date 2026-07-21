from __future__ import annotations

import re
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Mapping

from gui_core import (
    ActionButton,
    LabeledComboBox,
    LabeledEntry,
    LabeledSwitch,
    SecondaryWindow,
    SecondaryWindowConfig,
    get_accent_colors,
    get_surface_colors,
    require_customtkinter,
)

from smart_filter.domain.search_config import (
    CATEGORY_SEARCH_MODE_ALL_CONTENT,
    CATEGORY_SEARCH_MODE_TARGET_FIELDS,
    DEFAULT_CATEGORY_NAME,
    get_default_target_fields,
)
from smart_filter.services.category_service import (
    CATEGORY_IMPORT_ADD_NEW,
    CATEGORY_IMPORT_MERGE,
    CATEGORY_IMPORT_REPLACE,
    delete_category,
    export_categories_to_file,
    get_categories,
    get_category_rule,
    get_discard_category_options,
    import_categories_from_file,
    preview_category_import,
    restore_missing_default_categories,
    save_category,
)
from smart_filter.services.settings_service import get_settings
from smart_filter.ui.tooltips import SmartTooltip
from smart_filter.ui.window_icon import apply_window_icon_later


DEFAULT_ACCENT_HEX = "#1f6aa5"
DEFAULT_SURFACE_HEX = "#111827"


def _list_to_lines(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "\n".join(str(item).strip() for item in values if str(item).strip())


def _lines_to_list(value: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw_line in str(value or "").replace(";", "\n").splitlines():
        for part in raw_line.split(","):
            clean = part.strip()
            lookup = clean.casefold()
            if not clean or lookup in seen:
                continue
            seen.add(lookup)
            items.append(clean)
    return items


def _sanitize_hex_color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return text.lower()
    return default


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = _sanitize_hex_color(hex_color, DEFAULT_ACCENT_HEX).lstrip("#")
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, rgb[0])),
        max(0, min(255, rgb[1])),
        max(0, min(255, rgb[2])),
    )


def _mix_hex(color: str, target: str, ratio: float) -> str:
    base_rgb = _hex_to_rgb(color)
    target_rgb = _hex_to_rgb(target)
    ratio = max(0.0, min(1.0, ratio))
    mixed = tuple(int(base_rgb[index] + (target_rgb[index] - base_rgb[index]) * ratio) for index in range(3))
    return _rgb_to_hex(mixed)  # type: ignore[arg-type]


def _readable_text_color(hex_color: str) -> str:
    red, green, blue = _hex_to_rgb(hex_color)
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#111827" if luminance > 0.62 else "#ffffff"


def _safe_len(values: Any) -> int:
    return len(values) if isinstance(values, list) else 0


class CategoryWindow:
    """Ventana propia de Smart Filter para administrar categorías inteligentes."""

    def __init__(
        self,
        parent: Any,
        *,
        font_config: Any,
        on_change: Callable[[], None] | None = None,
        color_theme: str | None = None,
        surface_theme: str | None = None,
        appearance_mode: str | None = None,
    ) -> None:
        self.parent = parent
        self.font_config = font_config
        self.on_change = on_change
        self.color_theme = color_theme
        self.surface_theme = surface_theme
        self.appearance_mode = appearance_mode
        self.ctk = require_customtkinter()
        self.current_category: str = ""
        self.category_buttons: dict[str, Any] = {}
        self.editor_stat_labels: dict[str, Any] = {}
        self.list_empty_label: Any | None = None
        self.active_tab: str = "general"
        self.tab_buttons: dict[str, Any] = {}
        self.tab_frames: dict[str, Any] = {}
        self.tooltips: list[SmartTooltip] = []
        self.discard_selected: set[str] = set()
        self.discard_checkboxes: dict[str, Any] = {}
        self.import_mode_labels = {
            "Agregar solo nuevas": CATEGORY_IMPORT_ADD_NEW,
            "Combinar y actualizar": CATEGORY_IMPORT_MERGE,
            "Reemplazar todas": CATEGORY_IMPORT_REPLACE,
        }

        self.window = SecondaryWindow(
            parent,
            SecondaryWindowConfig(
                title="Categorías inteligentes",
                subtitle="Administrar términos, exclusiones y reglas propias de Smart Filter con una vista más clara y compacta.",
                width=1180,
                height=720,
                min_width=1000,
                min_height=620,
                modal=False,
            ),
            font_config=font_config,
        )
        self.window.apply_visual_preferences(font_config, color_theme, surface_theme, appearance_mode)
        apply_window_icon_later(self.window)
        apply_window_icon_later(self.window.content_frame)
        self._build_layout()
        self._reload_category_list()
        self._new_category()

    def _visual_tokens(self) -> dict[str, str]:
        try:
            appearance = self.appearance_mode or "dark"
            surface = get_surface_colors(appearance, self.surface_theme)
            accent = dict(get_accent_colors(self.color_theme))
            is_light = str(appearance).lower() == "light"
            settings = get_settings()

            if bool(settings.get("custom_surface_enabled")):
                base = _sanitize_hex_color(settings.get("custom_surface_hex"), DEFAULT_SURFACE_HEX)
                surface = dict(surface)
                surface["card"] = _mix_hex(base, "#ffffff" if is_light else "#000000", 0.08)
                surface["neutral"] = _mix_hex(base, "#ffffff" if is_light else "#000000", 0.16)
                surface["neutral_hover"] = _mix_hex(base, "#ffffff" if is_light else "#000000", 0.24)
                surface["border"] = _mix_hex(base, "#ffffff" if is_light else "#64748b", 0.35)

            if bool(settings.get("custom_accent_enabled")):
                primary = _sanitize_hex_color(settings.get("custom_accent_hex"), DEFAULT_ACCENT_HEX)
                accent["primary"] = primary
                accent["hover"] = _mix_hex(primary, "#000000", 0.18)
                accent["selected"] = _mix_hex(primary, "#000000" if is_light else "#ffffff", 0.72)

            return {
                "card": surface.get("card", "#111827"),
                "neutral": surface.get("neutral", "#202938"),
                "neutral_hover": surface.get("neutral_hover", "#2b3648"),
                "border": surface.get("border", "#334155"),
                "muted_text": surface.get("muted_text", "#94a3b8"),
                "text": "#111827" if is_light else "#f8fafc",
                "accent": accent.get("primary", DEFAULT_ACCENT_HEX),
                "accent_hover": accent.get("hover", "#155e91"),
                "accent_soft": accent.get("selected", "#1e3a5f"),
            }
        except Exception:
            return {
                "card": "#111827",
                "neutral": "#202938",
                "neutral_hover": "#2b3648",
                "border": "#334155",
                "muted_text": "#94a3b8",
                "text": "#f8fafc",
                "accent": DEFAULT_ACCENT_HEX,
                "accent_hover": "#155e91",
                "accent_soft": "#1e3a5f",
            }

    def _build_layout(self) -> None:
        root = self.window.content_frame
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        tokens = self._visual_tokens()

        self.left_frame = self.ctk.CTkFrame(root, width=292, fg_color=tokens["card"], border_width=1, border_color=tokens["border"])
        self.left_frame.grid(row=0, column=0, sticky="nsw", padx=(12, 8), pady=12)
        self.left_frame.grid_propagate(False)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(3, weight=1)

        self.list_title = self.ctk.CTkLabel(
            self.left_frame,
            text="Categorías",
            font=self.font_config.tuple("section", "bold"),
            anchor="w",
        )
        self.list_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 2))

        self.list_summary_label = self.ctk.CTkLabel(
            self.left_frame,
            text="",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
        )
        self.list_summary_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.filter_entry = self.ctk.CTkEntry(
            self.left_frame,
            placeholder_text="Filtrar categorías...",
            font=self.font_config.tuple("small"),
            height=30,
            fg_color=tokens["neutral"],
            border_color=tokens["border"],
        )
        self.filter_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.filter_entry.bind("<KeyRelease>", lambda _event: self._reload_category_list())

        self.list_frame = self.ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.new_button = ActionButton(
            self.left_frame,
            "Nueva categoría",
            command=self._new_category,
            style="secondary",
            font_config=self.font_config,
            color_theme=self.color_theme,
            surface_theme=self.surface_theme,
            appearance_mode=self.appearance_mode,
        )
        self.new_button.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.form_frame = self.ctk.CTkScrollableFrame(root, fg_color=tokens["card"], border_width=1, border_color=tokens["border"])
        self.form_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
        self.form_frame.grid_columnconfigure(0, weight=1)
        self.form_frame.grid_columnconfigure(1, weight=1)

        self.editor_header_frame = self.ctk.CTkFrame(self.form_frame, fg_color=tokens["neutral"], border_width=1, border_color=tokens["border"])
        self.editor_header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 10))
        self.editor_header_frame.grid_columnconfigure(0, weight=1)
        self.editor_header_frame.grid_columnconfigure(1, weight=0)

        self.editor_title_label = self.ctk.CTkLabel(
            self.editor_header_frame,
            text="Nueva categoría",
            font=self.font_config.tuple("title", "bold"),
            anchor="w",
        )
        self.editor_title_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))

        self.editor_meta_label = self.ctk.CTkLabel(
            self.editor_header_frame,
            text="Agregar nombre, términos y reglas para crear una categoría inteligente.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
        )
        self.editor_meta_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.editor_stats_frame = self.ctk.CTkFrame(self.editor_header_frame, fg_color="transparent")
        self.editor_stats_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=8)
        for index, key in enumerate(("Términos", "Exclusiones", "Descartes", "Campos")):
            label = self.ctk.CTkLabel(
                self.editor_stats_frame,
                text=f"{key}: 0",
                font=self.font_config.tuple("small", "bold"),
                fg_color=tokens["card"],
                text_color=tokens["text"],
                corner_radius=8,
                padx=10,
                pady=3,
            )
            label.grid(row=0, column=index, padx=(0, 6))
            self.editor_stat_labels[key] = label

        self._build_category_tabs(tokens)

        self.status_label = self.ctk.CTkLabel(
            self.form_frame,
            text="",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
        )
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 4))

        self._show_tab("general")

        self.management_frame = self.ctk.CTkFrame(self.window.footer_frame, fg_color="transparent")
        self.management_frame.grid(row=0, column=0, sticky="w")
        self.export_button = ActionButton(self.management_frame, "Exportar", command=self._export_categories, style="secondary", font_config=self.font_config)
        self.export_button.grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.import_button = ActionButton(self.management_frame, "Importar", command=self._import_categories, style="secondary", font_config=self.font_config)
        self.import_button.grid(row=0, column=1, padx=(0, 6), sticky="w")
        self.restore_button = ActionButton(self.management_frame, "Restaurar predeterminadas", command=self._restore_defaults, style="secondary", font_config=self.font_config)
        self.restore_button.grid(row=0, column=2, sticky="w")

        self.save_button = ActionButton(self.window.footer_frame, "Guardar", command=self._save_current, style="primary", font_config=self.font_config)
        self.save_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
        self.delete_button = ActionButton(self.window.footer_frame, "Eliminar", command=self._delete_current, style="danger", font_config=self.font_config)
        self.delete_button.grid(row=0, column=2, padx=(10, 0), sticky="e")
        self.close_button = ActionButton(self.window.footer_frame, "Cerrar", command=self.window.close, style="secondary", font_config=self.font_config)
        self.close_button.grid(row=0, column=3, padx=(10, 0), sticky="e")
        self._add_category_tooltips()

    def _tooltip_target(self, widget: Any) -> Any:
        for attribute in ("frame", "switch", "entry", "combo", "button"):
            target = getattr(widget, attribute, None)
            if target is not None:
                return target
        return widget

    def _add_tooltip(self, widget: Any, text: str, *, wraplength: int = 360) -> None:
        try:
            self.tooltips.append(SmartTooltip(self._tooltip_target(widget), text, wraplength=wraplength, font_config=self.font_config))
        except Exception:
            pass

    def _add_category_tooltips(self) -> None:
        tooltip_pairs = (
            (self.filter_entry, "Filtrar la lista por nombre, descripción o términos de categoría."),
            (self.new_button, "Preparar el editor para crear una categoría nueva."),
            (self.title_entry, "Nombre visible de la categoría. Conviene usar nombres cortos y claros."),
            (self.enabled_switch, "Activar o desactivar la categoría sin borrarla."),
            (self.description_box, "Descripción interna para recordar el objetivo de esta categoría."),
            (self.terms_box, "Términos positivos. Cada línea funciona como palabra o frase de búsqueda."),
            (self.target_fields_switch, "Limitar la categoría a estructuras reconocibles. Una aparición casual de la palabra no abre una sección."),
            (self.target_fields_box, "Nombres de campos, columnas, claves o encabezados. El motor toma su valor asociado o el bloque hasta el siguiente encabezado real."),
            (self.exclude_box, "Términos que descartan resultados dentro de esta categoría."),
            (self.discard_filter_entry, "Filtrar la lista y marcar categorías completas que actúan como descarte cruzado."),
            (self.export_button, "Exportar la categoría seleccionada o toda la base a un JSON portable."),
            (self.import_button, "Importar categorías desde un JSON estándar con modo seguro, combinado o de reemplazo."),
            (self.restore_button, "Restaurar únicamente las categorías predeterminadas que falten, sin tocar las actuales."),
            (self.save_button, "Guardar la categoría actual. Se crea una copia de seguridad antes de modificar una existente."),
            (self.delete_button, "Eliminar la categoría seleccionada después de confirmar su nombre. Se crea una copia de seguridad automática."),
        )
        for widget, text in tooltip_pairs:
            self._add_tooltip(widget, text)

    def _section_label(self, text: str, *, row: int) -> Any:
        tokens = self._visual_tokens()
        label = self.ctk.CTkLabel(
            self.form_frame,
            text=text,
            font=self.font_config.tuple("section", "bold"),
            text_color=tokens["text"],
            anchor="w",
        )
        label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        return label

    def _tab_section_label(self, parent: Any, text: str, *, row: int, columnspan: int = 2) -> Any:
        tokens = self._visual_tokens()
        label = self.ctk.CTkLabel(
            parent,
            text=text,
            font=self.font_config.tuple("section", "bold"),
            text_color=tokens["text"],
            anchor="w",
        )
        label.grid(row=row, column=0, columnspan=columnspan, sticky="ew", pady=(0, 8))
        return label

    def _tab_help_label(self, parent: Any, text: str, *, row: int, columnspan: int = 2) -> Any:
        tokens = self._visual_tokens()
        label = self.ctk.CTkLabel(
            parent,
            text=text,
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
        )
        label.grid(row=row, column=0, columnspan=columnspan, sticky="ew", pady=(0, 8))
        return label

    def _build_category_tabs(self, tokens: Mapping[str, str]) -> None:
        self.tabs_frame = self.ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.tabs_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        for index in range(3):
            self.tabs_frame.grid_columnconfigure(index, weight=0)
        self.tabs_frame.grid_columnconfigure(3, weight=1)

        tab_options = (
            ("general", "General"),
            ("include", "Incluir y alcance"),
            ("discard", "Descartar"),
        )
        for column, (key, label) in enumerate(tab_options):
            button = self.ctk.CTkButton(
                self.tabs_frame,
                text=label,
                command=lambda tab_key=key: self._show_tab(tab_key),
                font=self.font_config.tuple("small", "bold"),
                height=30,
                width=150 if key == "include" else 92,
                border_width=1,
                corner_radius=8,
            )
            button.grid(row=0, column=column, sticky="w", padx=(0, 6))
            self.tab_buttons[key] = button

        self.tab_host_frame = self.ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.tab_host_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.tab_host_frame.grid_columnconfigure(0, weight=1)
        self.tab_host_frame.grid_rowconfigure(0, weight=1)

        self._build_general_tab(tokens)
        self._build_include_tab(tokens)
        self._build_discard_tab(tokens)

    def _register_tab_frame(self, key: str) -> Any:
        frame = self.ctk.CTkFrame(self.tab_host_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        self.tab_frames[key] = frame
        return frame

    def _build_general_tab(self, tokens: Mapping[str, str]) -> None:
        frame = self._register_tab_frame("general")
        self.identity_label = self._tab_section_label(frame, "Identidad de la categoría", row=0)
        self._tab_help_label(
            frame,
            "Definir nombre, descripción y estado. Los términos y el alcance quedan juntos en Incluir y alcance.",
            row=1,
        )

        self.title_entry = LabeledEntry(frame, "Nombre de categoría", placeholder="Ej: soporte_tecnico", font_config=self.font_config)
        self.title_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))

        self.enabled_switch = LabeledSwitch(frame, "Categoría habilitada", default=True, font_config=self.font_config)
        self.enabled_switch.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(24, 10))

        self.description_label = self.ctk.CTkLabel(
            frame,
            text="Descripción",
            font=self.font_config.tuple("small", "bold"),
            anchor="w",
        )
        self.description_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.description_box = self.ctk.CTkTextbox(frame, height=90, font=self.font_config.tuple("body"), wrap="word")
        self.description_box.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.general_hint_label = self.ctk.CTkLabel(
            frame,
            text="Por defecto la categoría busca en todo el contenido. Habilitar el alcance específico solo cuando sea necesario.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
        )
        self.general_hint_label.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def _build_include_tab(self, tokens: Mapping[str, str]) -> None:
        frame = self._register_tab_frame("include")
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self.terms_section_label = self._tab_section_label(frame, "Términos que debe encontrar", row=0, columnspan=1)
        self.target_section_label = self._tab_section_label(frame, "Alcance de búsqueda", row=0, columnspan=1)
        self.target_section_label.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=(0, 8))

        self.terms_help_label = self.ctk.CTkLabel(
            frame,
            text="Una palabra o frase por línea. También es posible pegar valores separados por coma o punto y coma.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.terms_help_label.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        self.target_help_label = self.ctk.CTkLabel(
            frame,
            text="Busca en todo el contenido por defecto. Al limitar, solo acepta etiquetas, columnas, claves o encabezados reconocibles; no una palabra casual dentro de una frase.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
            wraplength=340,
        )
        self.target_help_label.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(0, 8))

        self.terms_box = self.ctk.CTkTextbox(frame, height=300, font=self.font_config.tuple("body"), wrap="word")
        self.terms_box.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 8))

        self.target_panel = self.ctk.CTkFrame(frame, fg_color=tokens["neutral"], border_width=1, border_color=tokens["border"])
        self.target_panel.grid(row=2, column=1, sticky="nsew", padx=(10, 0), pady=(0, 8))
        self.target_panel.grid_columnconfigure(0, weight=1)

        self.target_fields_switch = self.ctk.CTkSwitch(
            self.target_panel,
            text="Limitar dónde buscar",
            command=self._toggle_target_fields_options,
            font=self.font_config.tuple("small", "bold"),
            progress_color=tokens["accent"],
            button_color=tokens["accent"],
            button_hover_color=tokens["accent_hover"],
        )
        self.target_fields_switch.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        self.target_hint_label = self.ctk.CTkLabel(
            self.target_panel,
            text="Desactivado: usa el comportamiento general del motor.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
            wraplength=330,
        )
        self.target_hint_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.target_fields_details_frame = self.ctk.CTkFrame(self.target_panel, fg_color="transparent")
        self.target_fields_details_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.target_fields_details_frame.grid_columnconfigure(0, weight=1)

        self.target_fields_label = self.ctk.CTkLabel(
            self.target_fields_details_frame,
            text="Campos/secciones exactas",
            font=self.font_config.tuple("small", "bold"),
            anchor="w",
        )
        self.target_fields_label.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.target_fields_box = self.ctk.CTkTextbox(
            self.target_fields_details_frame,
            height=170,
            font=self.font_config.tuple("body"),
            wrap="word",
        )
        self.target_fields_box.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        self.target_examples_label = self.ctk.CTkLabel(
            self.target_fields_details_frame,
            text="Ej: puesto, experiencia, incidencias. Se analiza el valor asociado o el bloque hasta el siguiente encabezado real.",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
            wraplength=330,
        )
        self.target_examples_label.grid(row=2, column=0, sticky="ew")
        self._toggle_target_fields_options()

    def _build_discard_tab(self, tokens: Mapping[str, str]) -> None:
        frame = self._register_tab_frame("discard")
        frame.grid_rowconfigure(3, weight=1)
        self.discard_section_label = self._tab_section_label(frame, "Reglas de descarte", row=0)
        self._tab_help_label(
            frame,
            "Separar términos manuales de categorías completas. La lista evita errores de escritura y referencias inválidas.",
            row=1,
        )

        self.exclude_label = self.ctk.CTkLabel(
            frame,
            text="Términos de exclusión",
            font=self.font_config.tuple("small", "bold"),
            anchor="w",
        )
        self.exclude_label.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 4))
        self.exclude_box = self.ctk.CTkTextbox(frame, height=270, font=self.font_config.tuple("body"), wrap="word")
        self.exclude_box.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        self.discard_panel = self.ctk.CTkFrame(frame, fg_color=tokens["neutral"], border_width=1, border_color=tokens["border"])
        self.discard_panel.grid(row=2, column=1, rowspan=2, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.discard_panel.grid_columnconfigure(0, weight=1)
        self.discard_panel.grid_rowconfigure(3, weight=1)

        self.discard_label = self.ctk.CTkLabel(
            self.discard_panel,
            text="Categorías de descarte",
            font=self.font_config.tuple("small", "bold"),
            anchor="w",
        )
        self.discard_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 2))

        self.discard_summary_label = self.ctk.CTkLabel(
            self.discard_panel,
            text="0 seleccionadas",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
        )
        self.discard_summary_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        self.discard_filter_entry = self.ctk.CTkEntry(
            self.discard_panel,
            placeholder_text="Filtrar categorías...",
            font=self.font_config.tuple("small"),
            height=28,
            fg_color=tokens["card"],
            border_color=tokens["border"],
        )
        self.discard_filter_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.discard_filter_entry.bind("<KeyRelease>", lambda _event: self._reload_discard_selector())

        self.discard_list_frame = self.ctk.CTkScrollableFrame(self.discard_panel, fg_color="transparent", height=210)
        self.discard_list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.discard_list_frame.grid_columnconfigure(0, weight=1)
        self._reload_discard_selector()

    def _discard_filter_text(self) -> str:
        try:
            return str(self.discard_filter_entry.get() or "").strip().casefold()
        except Exception:
            return ""

    def _toggle_discard_category(self, category_name: str) -> None:
        checkbox = self.discard_checkboxes.get(category_name)
        try:
            selected = bool(checkbox.get()) if checkbox is not None else category_name not in self.discard_selected
        except Exception:
            selected = category_name not in self.discard_selected
        if selected:
            self.discard_selected.add(category_name)
        else:
            self.discard_selected.discard(category_name)
        self._update_discard_summary()

    def _update_discard_summary(self) -> None:
        count = len(self.discard_selected)
        suffix = "seleccionada" if count == 1 else "seleccionadas"
        if hasattr(self, "discard_summary_label"):
            self.discard_summary_label.configure(text=f"{count} {suffix}")
        stat_label = self.editor_stat_labels.get("Descartes")
        if stat_label is not None:
            stat_label.configure(text=f"Descartes: {count}")

    def _reload_discard_selector(self) -> None:
        if not hasattr(self, "discard_list_frame"):
            return
        for child in list(self.discard_list_frame.winfo_children()):
            child.destroy()
        self.discard_checkboxes.clear()

        tokens = self._visual_tokens()
        query = self._discard_filter_text()
        options = [
            name for name in get_discard_category_options(self.current_category)
            if not query or query in name.casefold()
        ]
        valid_options = set(get_discard_category_options(self.current_category))
        self.discard_selected.intersection_update(valid_options)

        if not options:
            label = self.ctk.CTkLabel(
                self.discard_list_frame,
                text="No hay categorías disponibles.",
                font=self.font_config.tuple("small"),
                text_color=tokens["muted_text"],
                anchor="w",
            )
            label.grid(row=0, column=0, sticky="ew", padx=4, pady=6)
            self._update_discard_summary()
            return

        for row_index, category_name in enumerate(options):
            checkbox = self.ctk.CTkCheckBox(
                self.discard_list_frame,
                text=category_name,
                command=lambda name=category_name: self._toggle_discard_category(name),
                font=self.font_config.tuple("small"),
                fg_color=tokens["accent"],
                hover_color=tokens["accent_hover"],
                border_color=tokens["border"],
            )
            checkbox.grid(row=row_index, column=0, sticky="ew", padx=4, pady=3)
            if category_name in self.discard_selected:
                checkbox.select()
            self.discard_checkboxes[category_name] = checkbox
        self._update_discard_summary()

    def _selected_discard_categories(self) -> list[str]:
        return sorted(self.discard_selected)

    def _target_fields_enabled(self) -> bool:
        try:
            return bool(self.target_fields_switch.get())
        except Exception:
            return False

    def _set_target_fields_enabled(self, enabled: bool) -> None:
        try:
            if enabled:
                self.target_fields_switch.select()
            else:
                self.target_fields_switch.deselect()
        except Exception:
            pass
        self._toggle_target_fields_options()

    def _toggle_target_fields_options(self) -> None:
        enabled = self._target_fields_enabled()
        if not hasattr(self, "target_fields_details_frame"):
            return
        try:
            if enabled:
                self.target_fields_details_frame.grid()
                self.target_hint_label.configure(text="Activado: exige un campo, clave, columna o encabezado real con ese nombre.")
            else:
                self.target_fields_details_frame.grid_remove()
                self.target_hint_label.configure(text="Desactivado: usa el comportamiento general del motor.")
        except Exception:
            pass

    def _show_tab(self, tab_key: str) -> None:
        if tab_key not in self.tab_frames:
            tab_key = "general"
        self.active_tab = tab_key
        tokens = self._visual_tokens()
        selected_text = _readable_text_color(tokens["accent"])
        for key, frame in self.tab_frames.items():
            if key == tab_key:
                frame.grid()
            else:
                frame.grid_remove()
        for key, button in self.tab_buttons.items():
            is_selected = key == tab_key
            try:
                button.configure(
                    fg_color=tokens["accent"] if is_selected else tokens["neutral"],
                    hover_color=tokens["accent_hover"] if is_selected else tokens["neutral_hover"],
                    text_color=selected_text if is_selected else tokens["text"],
                    border_color=tokens["accent"] if is_selected else tokens["border"],
                )
            except Exception:
                pass

    def _category_filter_text(self) -> str:
        try:
            return str(self.filter_entry.get() or "").strip().casefold()
        except Exception:
            return ""

    def _matches_filter(self, category_name: str, rule: Mapping[str, Any], query: str) -> bool:
        if not query:
            return True
        haystack = " ".join(
            [
                category_name,
                str(rule.get("title") or ""),
                str(rule.get("description") or ""),
                " ".join(str(term) for term in rule.get("terms", []) if str(term).strip()),
            ]
        ).casefold()
        return query in haystack

    def _reload_category_list(self) -> None:
        for child in list(self.list_frame.winfo_children()):
            child.destroy()
        self.category_buttons.clear()

        tokens = self._visual_tokens()
        categories = get_categories()
        query = self._category_filter_text()
        visible_categories = [
            (name, rule)
            for name, rule in sorted(categories.items())
            if self._matches_filter(name, rule, query)
        ]

        enabled_count = sum(1 for rule in categories.values() if rule.get("enabled", True))
        total_terms = sum(_safe_len(rule.get("terms", [])) for rule in categories.values())
        self.list_title.configure(text=f"Categorías ({len(visible_categories)}/{len(categories)})" if query else f"Categorías ({len(categories)})")
        self.list_summary_label.configure(text=f"{enabled_count} activas · {total_terms} términos")

        if not visible_categories:
            self.list_empty_label = self.ctk.CTkLabel(
                self.list_frame,
                text="Sin coincidencias",
                font=self.font_config.tuple("small"),
                text_color=tokens["muted_text"],
            )
            self.list_empty_label.grid(row=0, column=0, sticky="ew", pady=(8, 0))
            return

        for row_index, (category_name, rule) in enumerate(visible_categories):
            terms_count = _safe_len(rule.get("terms", []))
            label = f"{category_name} · {terms_count} términos"
            if not rule.get("enabled", True):
                label += " · off"
            button = self.ctk.CTkButton(
                self.list_frame,
                text=label,
                anchor="w",
                command=lambda name=category_name: self._select_category(name),
                font=self.font_config.tuple("body"),
                height=32,
                border_width=1,
            )
            button.grid(row=row_index, column=0, sticky="ew", pady=(0, 6))
            self.category_buttons[category_name] = button
        self._style_category_buttons()

    def _style_category_buttons(self) -> None:
        tokens = self._visual_tokens()
        selected_text = _readable_text_color(tokens["accent"])
        for category_name, button in self.category_buttons.items():
            is_selected = category_name == self.current_category
            try:
                button.configure(
                    fg_color=tokens["accent"] if is_selected else tokens["neutral"],
                    hover_color=tokens["accent_hover"] if is_selected else tokens["neutral_hover"],
                    text_color=selected_text if is_selected else tokens["text"],
                    border_color=tokens["accent"] if is_selected else tokens["border"],
                )
            except Exception:
                pass

    def _update_editor_summary(self, *, title: str, meta: str, terms: int = 0, exclusions: int = 0, discards: int = 0, fields: int = 0) -> None:
        self.editor_title_label.configure(text=title)
        self.editor_meta_label.configure(text=meta)
        values = {
            "Términos": terms,
            "Exclusiones": exclusions,
            "Descartes": discards,
            "Campos": fields,
        }
        for key, value in values.items():
            label = self.editor_stat_labels.get(key)
            if label is not None:
                label.configure(text=f"{key}: {value}")

    def _clear_textbox(self, textbox: Any) -> None:
        textbox.delete("1.0", "end")

    def _set_textbox(self, textbox: Any, value: str) -> None:
        self._clear_textbox(textbox)
        textbox.insert("1.0", value)

    def _get_textbox(self, textbox: Any) -> str:
        return str(textbox.get("1.0", "end")).strip()

    def _dialog_parent(self) -> Any:
        try:
            return self.window.content_frame.winfo_toplevel()
        except Exception:
            return self.parent

    def _export_categories(self) -> None:
        selected_names: list[str] | None = None
        scope_label = "todas las categorías"
        if self.current_category:
            choice = messagebox.askyesnocancel(
                "Exportar categorías",
                f"¿Exportar solo la categoría '{self.current_category}'?\n\n"
                "Sí: categoría seleccionada.\nNo: todas las categorías.\nCancelar: volver.",
                parent=self._dialog_parent(),
            )
            if choice is None:
                return
            if choice:
                selected_names = [self.current_category]
                scope_label = self.current_category

        suggested = (
            f"smartfilter_categoria_{self.current_category}.json"
            if selected_names
            else "smartfilter_categorias.json"
        )
        destination = filedialog.asksaveasfilename(
            parent=self._dialog_parent(),
            title="Exportar categorías",
            defaultextension=".json",
            initialfile=suggested,
            filetypes=(("JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not destination:
            return
        try:
            result = export_categories_to_file(destination, selected_names)
        except Exception as exc:
            self.status_label.configure(text=f"Error al exportar: {exc}")
            messagebox.showerror("Exportar categorías", str(exc), parent=self._dialog_parent())
            return
        self.status_label.configure(
            text=f"Exportadas {result['categories_count']} categorías: {Path(result['path']).name}"
        )
        messagebox.showinfo(
            "Exportación completada",
            f"Se exportó {scope_label} a:\n{result['path']}",
            parent=self._dialog_parent(),
        )

    def _choose_import_mode(self) -> str | None:
        parent = self._dialog_parent()
        dialog = self.ctk.CTkToplevel(parent)
        dialog.title("Modo de importación")
        dialog.geometry("470x270")
        dialog.resizable(False, False)
        try:
            dialog.transient(parent)
            dialog.grab_set()
        except Exception:
            pass
        apply_window_icon_later(dialog)
        tokens = self._visual_tokens()
        dialog.grid_columnconfigure(0, weight=1)

        label = self.ctk.CTkLabel(
            dialog,
            text="Elegir cómo aplicar las categorías importadas",
            font=self.font_config.tuple("section", "bold"),
            anchor="w",
        )
        label.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 6))
        help_label = self.ctk.CTkLabel(
            dialog,
            text=(
                "Agregar solo nuevas conserva todas las existentes.\n"
                "Combinar actualiza las categorías con el mismo nombre.\n"
                "Reemplazar todas elimina las categorías que no estén en el archivo."
            ),
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
            justify="left",
        )
        help_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

        mode_variable = self.ctk.StringVar(value="Agregar solo nuevas")
        option = self.ctk.CTkOptionMenu(
            dialog,
            values=list(self.import_mode_labels),
            variable=mode_variable,
            font=self.font_config.tuple("body"),
            dropdown_font=self.font_config.tuple("body"),
            fg_color=tokens["accent"],
            button_color=tokens["accent_hover"],
            button_hover_color=tokens["accent_hover"],
        )
        option.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))

        result: dict[str, str | None] = {"mode": None}
        actions = self.ctk.CTkFrame(dialog, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="e", padx=18, pady=(0, 16))

        def accept() -> None:
            result["mode"] = self.import_mode_labels.get(mode_variable.get())
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        cancel_button = self.ctk.CTkButton(
            actions,
            text="Cancelar",
            command=cancel,
            width=100,
            fg_color=tokens["neutral"],
            hover_color=tokens["neutral_hover"],
            border_width=1,
            border_color=tokens["border"],
        )
        cancel_button.grid(row=0, column=0, padx=(0, 8))
        accept_button = self.ctk.CTkButton(
            actions,
            text="Continuar",
            command=accept,
            width=110,
            fg_color=tokens["accent"],
            hover_color=tokens["accent_hover"],
        )
        accept_button.grid(row=0, column=1)
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.wait_window()
        return result["mode"]

    def _import_categories(self) -> None:
        source = filedialog.askopenfilename(
            parent=self._dialog_parent(),
            title="Importar categorías",
            filetypes=(("JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not source:
            return
        mode = self._choose_import_mode()
        if not mode:
            return
        try:
            preview = preview_category_import(source, mode)
        except Exception as exc:
            self.status_label.configure(text=f"Error al revisar la importación: {exc}")
            messagebox.showerror("Importar categorías", str(exc), parent=self._dialog_parent())
            return

        mode_text = {
            CATEGORY_IMPORT_ADD_NEW: "Agregar solo nuevas",
            CATEGORY_IMPORT_MERGE: "Combinar y actualizar",
            CATEGORY_IMPORT_REPLACE: "Reemplazar todas",
        }[mode]
        warning = ""
        if mode == CATEGORY_IMPORT_REPLACE:
            warning = (
                f"\n\nATENCIÓN: se quitarán {preview['replace_removed_count']} categorías "
                "que no están en el archivo."
            )
        confirmed = messagebox.askyesno(
            "Confirmar importación",
            (
                f"Modo: {mode_text}\n"
                f"Categorías en el archivo: {preview['imported_count']}\n"
                f"Nuevas: {preview['new_count']}\n"
                f"Coincidencias de nombre: {preview['conflict_count']}"
                f"{warning}\n\nSe creará una copia de seguridad automática antes de aplicar."
            ),
            parent=self._dialog_parent(),
        )
        if not confirmed:
            return
        try:
            result = import_categories_from_file(source, mode)
        except Exception as exc:
            self.status_label.configure(text=f"Error al importar: {exc}")
            messagebox.showerror("Importar categorías", str(exc), parent=self._dialog_parent())
            return

        self._reload_category_list()
        categories = get_categories()
        if self.current_category in categories:
            self._select_category(self.current_category)
        else:
            self._new_category()
        if callable(self.on_change):
            self.on_change()
        backup_text = f" · backup: {Path(result['backup_path']).name}" if result.get("backup_path") else ""
        self.status_label.configure(
            text=(
                f"Importación completada · agregadas={result['added_count']} · "
                f"actualizadas={result['updated_count']} · omitidas={result['skipped_count']}"
                f"{backup_text}"
            )
        )

    def _restore_defaults(self) -> None:
        confirmed = messagebox.askyesno(
            "Restaurar categorías predeterminadas",
            (
                "Se agregarán únicamente las categorías predeterminadas que falten.\n"
                "Las categorías existentes y las creadas por el usuario no se modificarán.\n\n"
                "Antes de restaurar se creará una copia de seguridad automática."
            ),
            parent=self._dialog_parent(),
        )
        if not confirmed:
            return
        try:
            result = restore_missing_default_categories()
        except Exception as exc:
            self.status_label.configure(text=f"Error al restaurar: {exc}")
            messagebox.showerror("Restaurar categorías", str(exc), parent=self._dialog_parent())
            return
        self._reload_category_list()
        if result["restored_count"]:
            preferred = "administracion" if "administracion" in result["restored_names"] else result["restored_names"][0]
            self._select_category(preferred)
            if callable(self.on_change):
                self.on_change()
            self.status_label.configure(
                text=f"Restauradas {result['restored_count']} categorías: {', '.join(result['restored_names'])}"
            )
        else:
            self.status_label.configure(text="No faltaba ninguna categoría predeterminada.")

    def _new_category(self) -> None:
        self.current_category = ""
        self.title_entry.clear()
        self.enabled_switch.set_value(True)
        self._set_textbox(self.description_box, "")
        self._set_target_fields_enabled(False)
        self._set_textbox(self.target_fields_box, "")
        self.discard_selected.clear()
        self._reload_discard_selector()
        self._set_textbox(self.terms_box, "")
        self._set_textbox(self.exclude_box, "")
        self._update_editor_summary(
            title="Nueva categoría",
            meta="Agregar nombre y al menos un término de inclusión.",
            fields=0,
        )
        self._style_category_buttons()
        self._show_tab("general")
        self.status_label.configure(text="Nueva categoría · agregar nombre y al menos un término de inclusión.")

    def _select_category(self, category_name: str) -> None:
        if not category_name or category_name == DEFAULT_CATEGORY_NAME:
            self._new_category()
            return
        rule = get_category_rule(category_name)
        self.current_category = category_name
        self.title_entry.set_value(rule.get("title") or category_name)
        self.enabled_switch.set_value(bool(rule.get("enabled", True)))
        self._set_textbox(self.description_box, str(rule.get("description") or ""))
        target_fields_enabled = str(rule.get("search_mode") or CATEGORY_SEARCH_MODE_ALL_CONTENT) == CATEGORY_SEARCH_MODE_TARGET_FIELDS
        self._set_target_fields_enabled(target_fields_enabled)
        self._set_textbox(self.target_fields_box, _list_to_lines(rule.get("target_fields", [])) if target_fields_enabled else "")
        self.discard_selected = set(str(item) for item in rule.get("discard_categories", []) if str(item).strip())
        self._reload_discard_selector()
        self._set_textbox(self.terms_box, _list_to_lines(rule.get("terms", [])))
        self._set_textbox(self.exclude_box, _list_to_lines(rule.get("exclude_terms", [])))
        enabled_label = "habilitada" if rule.get("enabled", True) else "deshabilitada"
        self._update_editor_summary(
            title=f"Editando · {category_name}",
            meta=f"Categoría {enabled_label} · alcance: {'campos específicos' if target_fields_enabled else 'todo el contenido'}",
            terms=_safe_len(rule.get("terms", [])),
            exclusions=_safe_len(rule.get("exclude_terms", [])),
            discards=_safe_len(rule.get("discard_categories", [])),
            fields=_safe_len(rule.get("target_fields", [])) if target_fields_enabled else 0,
        )
        self._style_category_buttons()
        self.status_label.configure(
            text=(
                f"Editando: {category_name} · términos={len(rule.get('terms', []))} · "
                f"exclusiones={len(rule.get('exclude_terms', []))}"
            )
        )

    def _save_current(self) -> None:
        target_fields_enabled = self._target_fields_enabled()
        target_fields = _lines_to_list(self._get_textbox(self.target_fields_box)) if target_fields_enabled else []
        search_mode = CATEGORY_SEARCH_MODE_TARGET_FIELDS if target_fields_enabled else CATEGORY_SEARCH_MODE_ALL_CONTENT
        if target_fields_enabled and not target_fields:
            self._show_tab("include")
            self.status_label.configure(text="Para limitar dónde buscar, agregar al menos un campo o sección exacta.")
            return
        try:
            saved_key = save_category(
                original_category_name=self.current_category,
                title=self.title_entry.get_value(),
                description=self._get_textbox(self.description_box),
                terms=_lines_to_list(self._get_textbox(self.terms_box)),
                enabled=self.enabled_switch.get_value(),
                exclude_terms=_lines_to_list(self._get_textbox(self.exclude_box)),
                discard_categories=self._selected_discard_categories(),
                search_mode=search_mode,
                target_fields=target_fields,
            )
        except Exception as exc:
            self.status_label.configure(text=f"Error al guardar: {exc}")
            return
        self.current_category = saved_key
        self._reload_category_list()
        self._select_category(saved_key)
        if callable(self.on_change):
            self.on_change()
        self.status_label.configure(text=f"Categoría guardada: {saved_key}")

    def _delete_current(self) -> None:
        if not self.current_category:
            self.status_label.configure(text="No hay categoría seleccionada para eliminar.")
            return
        deleted_name = self.current_category
        confirmed = messagebox.askyesno(
            "Eliminar categoría",
            (
                f"¿Eliminar la categoría '{deleted_name}'?\n\n"
                "Las referencias de descarte hacia ella también se quitarán. "
                "Se creará una copia de seguridad automática antes de eliminar."
            ),
            parent=self._dialog_parent(),
        )
        if not confirmed:
            return
        try:
            delete_category(deleted_name)
        except Exception as exc:
            self.status_label.configure(text=f"Error al eliminar: {exc}")
            messagebox.showerror("Eliminar categoría", str(exc), parent=self._dialog_parent())
            return
        self._reload_category_list()
        self._new_category()
        if callable(self.on_change):
            self.on_change()
        self.status_label.configure(text=f"Categoría eliminada: {deleted_name} · copia de seguridad creada")


def show_category_window(
    parent: Any,
    *,
    font_config: Any,
    on_change: Callable[[], None] | None = None,
    color_theme: str | None = None,
    surface_theme: str | None = None,
    appearance_mode: str | None = None,
) -> CategoryWindow:
    return CategoryWindow(
        parent,
        font_config=font_config,
        on_change=on_change,
        color_theme=color_theme,
        surface_theme=surface_theme,
        appearance_mode=appearance_mode,
    )
