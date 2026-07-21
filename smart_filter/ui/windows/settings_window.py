from __future__ import annotations

from typing import Any, Callable, Mapping
from tkinter import colorchooser, filedialog

from gui_core import (
    APPEARANCE_LABEL_OPTIONS,
    COLOR_THEME_LABEL_OPTIONS,
    SURFACE_THEME_LABEL_OPTIONS,
    ActionButton,
    GuiPreferences,
    LabeledComboBox,
    LabeledEntry,
    LabeledSwitch,
    SecondaryWindow,
    SecondaryWindowConfig,
    get_accent_colors,
    get_surface_colors,
    normalize_appearance_label,
    normalize_appearance_value,
    normalize_color_theme,
    normalize_color_theme_label,
    normalize_surface_theme,
    normalize_surface_theme_label,
    require_customtkinter,
)

from smart_filter.domain.search_config import get_search_file_type_options, get_search_scope_options
from smart_filter.engine.resource_policy import resolve_resource_policy
from smart_filter.domain.scan_exclusions import (
    BROAD_SCAN_ENABLED_KEY,
    BROAD_SCAN_OPTIONS,
)
from smart_filter.ui.tooltips import SmartTooltip
from smart_filter.ui.window_icon import apply_window_icon_later
from smart_filter.services.settings_service import (
    clear_saved_discard_terms,
    clear_search_history,
    get_app_font_family_options,
    get_default_settings_data,
    get_app_font_size_options,
    get_highlight_cell_color_options,
    get_highlight_text_color_options,
    get_max_content_file_size_options,
    get_metric_card_size_options,
    get_metric_card_style_options,
    get_open_result_mode_options,
    get_processing_mode_options,
    get_resource_profile_options,
    get_results_density_options,
    get_settings,
    load_gui_preferences,
    load_settings,
    save_gui_preferences,
    save_settings,
    write_settings_data,
)


SETTINGS_TAB_NAMES = [
    "Búsqueda",
    "Rendimiento",
    "Salida",
    "Destacado",
    "Visual",
    "Experiencia",
    "Exclusiones",
]


SETTINGS_TAB_DETAILS = {
    "Búsqueda": "Motor, alcance y lectura",
    "Rendimiento": "CPU, memoria y perfiles",
    "Salida": "Exportar y copiar",
    "Destacado": "Vista temporal",
    "Visual": "Tema, color y métricas",
    "Experiencia": "Recordar uso",
    "Exclusiones": "Escaneo seguro e ignorados",
}


ACCENT_PREVIEW_KEYS = [
    ("primary", "Principal"),
    ("hover", "Hover"),
    ("selected", "Selección"),
]


SURFACE_PREVIEW_KEYS = [
    ("root", "Raíz"),
    ("sidebar", "Sidebar"),
    ("content", "Contenido"),
    ("card", "Tarjeta"),
    ("neutral", "Neutral"),
    ("table_heading", "Tabla"),
]

# Smart Filter reserva el verde para estados/resultados.
# Por eso se oculta la base visual "Bosque", que compite visualmente
# con las tarjetas de métricas en estilo Estado.
DISABLED_SURFACE_THEME_LABELS = {"Bosque"}
SMARTFILTER_SURFACE_THEME_LABEL_OPTIONS = tuple(
    option for option in SURFACE_THEME_LABEL_OPTIONS if option not in DISABLED_SURFACE_THEME_LABELS
)
SMARTFILTER_DEFAULT_SURFACE_THEME_LABEL = "Onyx"


def _safe_surface_theme_label(value: str | None) -> str:
    label = normalize_surface_theme_label(normalize_surface_theme(value or SMARTFILTER_DEFAULT_SURFACE_THEME_LABEL))
    if label in DISABLED_SURFACE_THEME_LABELS or label not in SMARTFILTER_SURFACE_THEME_LABEL_OPTIONS:
        return SMARTFILTER_DEFAULT_SURFACE_THEME_LABEL
    return label


CUSTOM_ACCENT_PRESETS = (
    ("Azul", "#1f6aa5"),
    ("Cian", "#0891b2"),
    ("Índigo", "#4f46e5"),
    ("Violeta", "#7c3aed"),
    ("Fucsia", "#c026d3"),
    ("Rojo", "#dc2626"),
    ("Naranja", "#ea580c"),
    ("Ámbar", "#d97706"),
)
CUSTOM_ACCENT_LABELS = tuple(label for label, _hex in CUSTOM_ACCENT_PRESETS)
CUSTOM_ACCENT_HEX_BY_LABEL = {label: hex_value for label, hex_value in CUSTOM_ACCENT_PRESETS}
CUSTOM_ACCENT_LABEL_BY_HEX = {hex_value.casefold(): label for label, hex_value in CUSTOM_ACCENT_PRESETS}
DEFAULT_CUSTOM_ACCENT_LABEL = "Azul"
DEFAULT_CUSTOM_SURFACE_HEX = "#1b2430"
ADVANCED_COLOR_SWITCH_WIDTH = 235
ADVANCED_COLOR_BUTTON_WIDTH = 150


def _normalize_hex_color(value: Any) -> str:
    raw = str(value or "").strip().lstrip("#")
    if len(raw) == 3 and all(character in "0123456789abcdefABCDEF" for character in raw):
        raw = "".join(character * 2 for character in raw)
    if len(raw) == 6 and all(character in "0123456789abcdefABCDEF" for character in raw):
        return f"#{raw.lower()}"
    return CUSTOM_ACCENT_HEX_BY_LABEL[DEFAULT_CUSTOM_ACCENT_LABEL]


def _custom_accent_hex_for_label(label: Any) -> str:
    return CUSTOM_ACCENT_HEX_BY_LABEL.get(str(label), CUSTOM_ACCENT_HEX_BY_LABEL[DEFAULT_CUSTOM_ACCENT_LABEL])


def _custom_accent_label_for_hex(value: Any) -> str:
    clean = _normalize_hex_color(value)
    return CUSTOM_ACCENT_LABEL_BY_HEX.get(clean.casefold(), "Personalizado")


def _lines_to_list(value: str) -> list[str]:
    clean_items: list[str] = []
    seen: set[str] = set()
    for raw_line in str(value or "").replace(";", "\n").splitlines():
        for part in raw_line.split(","):
            clean = part.strip()
            lookup = clean.casefold()
            if not clean or lookup in seen:
                continue
            clean_items.append(clean)
            seen.add(lookup)
    return clean_items


def _list_to_lines(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "\n".join(str(item).strip() for item in values if str(item).strip())


def _clean_ignore_item(value: Any) -> str:
    return str(value or "").strip()


def _prefixed_ignore_lines(keywords: Any, paths: Any, *, keyword_label: str = "Nombre", path_label: str = "Ruta") -> str:
    lines: list[str] = []
    for item in _lines_to_list(_list_to_lines(keywords) if isinstance(keywords, list) else str(keywords or "")):
        lines.append(f"{keyword_label}: {item}")
    if isinstance(paths, str):
        path_values = _lines_to_list(paths)
    else:
        path_values = list(paths or []) if isinstance(paths, list) else []
    seen = {line.casefold() for line in lines}
    for item in path_values:
        clean = _clean_ignore_item(item)
        if not clean:
            continue
        line = f"{path_label}: {clean}"
        lookup = line.casefold()
        if lookup in seen:
            continue
        lines.append(line)
        seen.add(lookup)
    return "\n".join(lines)


def _parse_prefixed_ignore_lines(value: str, *, keyword_label: str = "Nombre", path_label: str = "Ruta") -> tuple[list[str], list[str]]:
    keywords: list[str] = []
    paths: list[str] = []
    keyword_prefix = f"{keyword_label}:".casefold()
    path_prefix = f"{path_label}:".casefold()
    seen_keywords: set[str] = set()
    seen_paths: set[str] = set()
    for raw_line in str(value or "").replace(";", "\n").splitlines():
        clean = raw_line.strip()
        if not clean:
            continue
        lookup = clean.casefold()
        target = "keyword"
        if lookup.startswith(path_prefix):
            clean = clean[len(f"{path_label}:"):].strip()
            target = "path"
        elif lookup.startswith(keyword_prefix):
            clean = clean[len(f"{keyword_label}:"):].strip()
        if not clean:
            continue
        if target == "path":
            path_lookup = clean.casefold()
            if path_lookup not in seen_paths:
                paths.append(clean)
                seen_paths.add(path_lookup)
        else:
            keyword_lookup = clean.casefold()
            if keyword_lookup not in seen_keywords:
                keywords.append(clean)
                seen_keywords.add(keyword_lookup)
    return keywords, paths


def _contrast_text_color(hex_color: str | None) -> str:
    """Return black/white text color with readable contrast for preview chips."""
    value = str(hex_color or "").strip().lstrip("#")
    if len(value) != 6:
        return "#ffffff"
    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return "#ffffff"
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#111111" if luminance > 0.58 else "#f8fafc"


class ProductSettingsWindow:
    """Configuración propia de Smart Filter sobre servicios reales y GuiCore."""

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
        self.settings = get_settings()
        self.preferences = load_gui_preferences()
        self.palette_chips: dict[str, Any] = {}
        self.settings_tab_buttons: dict[str, Any] = {}
        self.settings_tab_frames: dict[str, Any] = {}
        self.tooltips: list[SmartTooltip] = []
        self.active_settings_tab = "Búsqueda"

        self.window = SecondaryWindow(
            parent,
            SecondaryWindowConfig(
                title="Configuración de Smart Filter",
                subtitle=(
                    "Preferencias de búsqueda, salida, visual y experiencia organizadas en una vista más compacta."
                ),
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
        self._load_values()

    def _visual_tokens(self) -> dict[str, str]:
        try:
            appearance = self.appearance_mode or self.preferences.appearance_mode or "dark"
            surface = dict(get_surface_colors(appearance, self.surface_theme or self.preferences.surface_theme))
            accent = dict(get_accent_colors(self.color_theme or self.preferences.color_theme))
            settings = get_settings()
            is_light = str(appearance).lower() == "light"

            if bool(settings.get("custom_surface_enabled")):
                base = _normalize_hex_color(settings.get("custom_surface_hex") or DEFAULT_CUSTOM_SURFACE_HEX)
                surface["card"] = base
                surface["neutral"] = base
                surface["neutral_hover"] = base
                surface["border"] = "#cbd5e1" if is_light else "#334155"

            if bool(settings.get("custom_accent_enabled")):
                primary = _normalize_hex_color(settings.get("custom_accent_hex") or "#1f6aa5")
                accent["primary"] = primary
                accent["hover"] = primary
                accent["selected"] = primary

            return {
                "card": surface.get("card", "#111827"),
                "neutral": surface.get("neutral", "#202938"),
                "neutral_hover": surface.get("neutral_hover", "#2b3648"),
                "border": surface.get("border", "#334155"),
                "muted_text": surface.get("muted_text", "#94a3b8"),
                "text": "#111827" if is_light else "#f8fafc",
                "accent": accent.get("primary", "#1f6aa5"),
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
                "accent": "#1f6aa5",
                "accent_hover": "#155e91",
                "accent_soft": "#1e3a5f",
            }

    def _section_label(self, parent: Any, row: int, text: str, subtitle: str | None = None) -> int:
        label = self.ctk.CTkLabel(parent, text=text, font=self.font_config.tuple("section", "bold"), anchor="w")
        label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 3))
        row += 1
        if subtitle:
            detail = self.ctk.CTkLabel(
                parent,
                text=subtitle,
                font=self.font_config.tuple("small"),
                text_color=("gray35", "gray72"),
                anchor="w",
                justify="left",
                wraplength=900,
            )
            detail.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            row += 1
        return row

    def _create_tab_frame(self, tab_name: str) -> Any:
        frame = self.ctk.CTkScrollableFrame(self.tab_host_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        self.settings_tab_frames[tab_name] = frame
        return frame

    def _grid_pair(self, left: Any, right: Any | None, row: int, *, pady: tuple[int, int] = (0, 10)) -> int:
        left.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=pady)
        if right is not None:
            right.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=pady)
        return row + 1

    def _build_ignore_actions_frame(
        self,
        parent: Any,
        *,
        add_label: str,
        add_command: Callable[[], None],
        select_label: str,
        select_command: Callable[[], None],
    ) -> Any:
        frame = self.ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        add_button = ActionButton(frame, add_label, command=add_command, style="secondary", font_config=self.font_config)
        add_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        select_button = ActionButton(frame, select_label, command=select_command, style="ghost", font_config=self.font_config)
        select_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self._add_tooltip(add_button, "Agregar el nombre escrito a la lista correspondiente.")
        self._add_tooltip(select_button, "Elegir una ruta exacta desde el sistema.")
        return frame

    def _build_layout(self) -> None:
        root = self.window.content_frame
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        tokens = self._visual_tokens()

        self.nav_frame = self.ctk.CTkFrame(root, width=292, fg_color=tokens["card"], border_width=1, border_color=tokens["border"])
        self.nav_frame.grid(row=0, column=0, sticky="nsw", padx=(12, 8), pady=12)
        self.nav_frame.grid_propagate(False)
        self.nav_frame.grid_columnconfigure(0, weight=1)

        self.nav_title_label = self.ctk.CTkLabel(
            self.nav_frame,
            text="Configuración",
            font=self.font_config.tuple("section", "bold"),
            anchor="w",
        )
        self.nav_title_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 2))

        self.nav_summary_label = self.ctk.CTkLabel(
            self.nav_frame,
            text="7 secciones · preferencias",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
        )
        self.nav_summary_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        for row_index, tab_name in enumerate(SETTINGS_TAB_NAMES, start=2):
            button = self.ctk.CTkButton(
                self.nav_frame,
                text=f"{tab_name} · {SETTINGS_TAB_DETAILS.get(tab_name, '')}",
                anchor="w",
                height=34,
                border_width=1,
                font=self.font_config.tuple("body"),
                command=lambda name=tab_name: self._show_settings_tab(name),
            )
            button.grid(row=row_index, column=0, sticky="ew", padx=10, pady=(0, 7))
            self.settings_tab_buttons[tab_name] = button

        self.right_frame = self.ctk.CTkFrame(root, fg_color=tokens["card"], border_width=1, border_color=tokens["border"])
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)

        self.header_frame = self.ctk.CTkFrame(self.right_frame, fg_color=tokens["neutral"], border_width=1, border_color=tokens["border"])
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.settings_title_label = self.ctk.CTkLabel(
            self.header_frame,
            text="Búsqueda",
            font=self.font_config.tuple("title", "bold"),
            anchor="w",
        )
        self.settings_title_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))

        self.settings_meta_label = self.ctk.CTkLabel(
            self.header_frame,
            text="Motor, alcance y lectura",
            font=self.font_config.tuple("small"),
            text_color=tokens["muted_text"],
            anchor="w",
        )
        self.settings_meta_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 10))

        self.tab_host_frame = self.ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.tab_host_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tab_host_frame.grid_columnconfigure(0, weight=1)
        self.tab_host_frame.grid_rowconfigure(0, weight=1)

        self.search_tab = self._create_tab_frame("Búsqueda")
        self.performance_tab = self._create_tab_frame("Rendimiento")
        self.output_tab = self._create_tab_frame("Salida")
        self.highlight_tab = self._create_tab_frame("Destacado")
        self.visual_tab = self._create_tab_frame("Visual")
        self.experience_tab = self._create_tab_frame("Experiencia")
        self.filters_tab = self._create_tab_frame("Exclusiones")

        self._build_search_tab()
        self._build_performance_tab()
        self._build_output_tab()
        self._build_highlight_tab()
        self._build_visual_tab()
        self._build_experience_tab()
        self._build_filters_tab()
        self._build_footer()
        self._add_settings_tooltips()
        self._show_settings_tab("Búsqueda")

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

    def _add_settings_tooltips(self) -> None:
        tooltip_pairs = (
            (self.default_file_type_combo, "Tipo inicial del formulario principal. Puede cambiarse en cada búsqueda."),
            (self.search_scope_combo, "Alcance inicial para buscar en nombre de archivo, contenido o ambos."),
            (self.max_content_combo, "Límite de lectura por archivo para evitar demoras con archivos demasiado grandes."),
            (self.resource_profile_combo, "Equilibrado es el perfil recomendado. Bajo consumo prioriza respuesta del equipo; Alto rendimiento prioriza velocidad."),
            (self.processing_mode_combo, "Automático calcula una política segura. Manual técnico permite ajustar procesos, lectores, reserva y lotes."),
            (self.performance_monitor_switch, "Muestrea CPU y memoria con bajo costo y guarda agregados en data.performance."),
            (self.performance_timeline_switch, "Agrega una muestra resumida cada 10 segundos para diagnosticar cuellos de botella."),
            (self.manual_analysis_processes_entry, "Procesos reales dedicados a normalización y coincidencias."),
            (self.manual_reader_workers_entry, "Hilos dedicados a lectura y extracción de contenido."),
            (self.manual_reserved_cores_entry, "Núcleos físicos que Smart Filter deja fuera de su presupuesto CPU."),
            (self.manual_pending_batches_entry, "Límite estricto de lotes esperando o ejecutándose en el pool CPU."),
            (self.output_prefix_entry, "Nombre base para crear carpetas de salida al exportar o copiar resultados."),
            (self.auto_open_switch, "Abrir automáticamente la carpeta generada después de guardar resultados."),
            (self.csv_report_switch, "Crear un archivo CSV junto con los resultados guardados."),
            (self.preserve_structure_switch, "Mantener la estructura original de carpetas al copiar archivos encontrados."),
            (self.highlight_switch, "Resaltar coincidencias al abrir la vista temporal de un resultado."),
            (self.open_mode_combo, "Comportamiento aplicado únicamente al abrir un resultado con doble clic."),
            (self.highlight_cell_combo, "Color de fondo usado para marcar coincidencias en vistas destacadas."),
            (self.highlight_text_combo, "Color del texto resaltado en vistas destacadas."),
            (self.appearance_combo, "Modo visual general de la aplicación."),
            (self.color_combo, "Color principal predefinido para botones, selección y elementos destacados."),
            (self.surface_combo, "Base visual predefinida para paneles y fondos."),
            (self.density_combo, "Nivel de compactación visual de la tabla de resultados: compacto, normal o cómodo."),
            (self.font_family_combo, "Fuente usada por la interfaz."),
            (self.font_size_combo, "Escala general de texto de la interfaz."),
            (self.metric_size_combo, "Tamaño de las métricas mostradas al finalizar una búsqueda."),
            (self.metric_style_combo, "Estilo visual aplicado al panel de métricas."),
            (self.custom_accent_switch, "Activar un color principal personalizado elegido desde el selector del sistema."),
            (self.custom_accent_button, "Abrir el selector del sistema para elegir el color principal personalizado."),
            (self.custom_surface_switch, "Activar una base visual personalizada para paneles y fondos propios de Smart Filter."),
            (self.custom_surface_button, "Abrir el selector del sistema para elegir la base visual personalizada."),
            (self.remember_use_switch, "Control general para recordar preferencias de uso entre sesiones."),
            (self.history_switch, "Guardar términos buscados para reutilizarlos luego."),
            (self.mode_switch, "Recordar el último modo usado: carpeta o archivo individual."),
            (self.location_switch, "Recordar la última ruta usada en el formulario principal."),
            (self.search_settings_switch, "Recordar criterios, categoría, alcance y tipos de archivo usados recientemente."),
            (self.ignored_folder_entry, "Agregar nombres flexibles de carpetas a ignorar, por ejemplo node_modules o __pycache__."),
            (self.ignored_file_entry, "Agregar nombres flexibles de archivos a ignorar, por ejemplo temp o backup."),
            (self.ignored_folder_box, "Lista editable de carpetas ignoradas por nombre o ruta exacta."),
            (self.ignored_file_box, "Lista editable de archivos ignorados por nombre o ruta exacta."),
            (self.saved_terms_box, "Términos de descarte guardados por el uso de la aplicación."),
            (self.history_box, "Historial de búsquedas guardadas."),
            (self.restore_defaults_button, "Restaurar preferencias base de Smart Filter sin borrar historial ni descartes guardados."),
            (self.save_button, "Guardar configuración actual."),
            (self.clear_history_button, "Borrar solo el historial de búsquedas."),
            (self.clear_terms_button, "Borrar solo los términos de descarte guardados."),
        )
        for widget, text in tooltip_pairs:
            self._add_tooltip(widget, text)

        self._add_tooltip(
            self.broad_scan_safe_switch,
            "Activa estas exclusiones solo cuando el origen es una raíz de disco o volumen, por ejemplo C:\\, D:\\ o /. "
            "Las búsquedas en carpetas normales mantienen su comportamiento habitual.",
            wraplength=430,
        )
        for option in BROAD_SCAN_OPTIONS:
            switch = self.broad_scan_group_switches.get(option.group_id)
            if switch is not None:
                self._add_tooltip(switch, option.tooltip, wraplength=460)

    def _show_settings_tab(self, tab_name: str) -> None:
        if tab_name not in self.settings_tab_frames:
            tab_name = "Búsqueda"
        self.active_settings_tab = tab_name
        tokens = self._visual_tokens()
        selected_text = _contrast_text_color(tokens["accent"])
        for name, frame in self.settings_tab_frames.items():
            if name == tab_name:
                frame.grid()
            else:
                frame.grid_remove()
        for name, button in self.settings_tab_buttons.items():
            selected = name == tab_name
            try:
                button.configure(
                    fg_color=tokens["accent"] if selected else tokens["neutral"],
                    hover_color=tokens["accent_hover"] if selected else tokens["neutral_hover"],
                    text_color=selected_text if selected else tokens["text"],
                    border_color=tokens["accent"] if selected else tokens["border"],
                )
            except Exception:
                pass
        try:
            self.settings_title_label.configure(text=tab_name)
            self.settings_meta_label.configure(text=SETTINGS_TAB_DETAILS.get(tab_name, ""))
        except Exception:
            pass

    def _style_settings_chrome(self) -> None:
        tokens = self._visual_tokens()
        for widget_name in ("nav_frame", "right_frame"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget.configure(fg_color=tokens["card"], border_color=tokens["border"])
                except Exception:
                    pass
        if hasattr(self, "header_frame"):
            try:
                self.header_frame.configure(fg_color=tokens["neutral"], border_color=tokens["border"])
                self.nav_summary_label.configure(text_color=tokens["muted_text"])
                self.settings_meta_label.configure(text_color=tokens["muted_text"])
            except Exception:
                pass
        self._show_settings_tab(getattr(self, "active_settings_tab", "Búsqueda"))

    def _build_search_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.search_tab,
            row,
            "Búsqueda",
            "Valores por defecto para preparar el formulario principal y limitar la lectura de contenido.",
        )
        self.default_file_type_combo = LabeledComboBox(
            self.search_tab, "Tipo de archivo por defecto", get_search_file_type_options(), font_config=self.font_config
        )
        self.search_scope_combo = LabeledComboBox(
            self.search_tab, "Alcance por defecto", get_search_scope_options(), font_config=self.font_config
        )
        row = self._grid_pair(self.default_file_type_combo, self.search_scope_combo, row)

        self.max_content_combo = LabeledComboBox(
            self.search_tab, "Límite de lectura por archivo", get_max_content_file_size_options(), font_config=self.font_config
        )
        self.max_content_help = self.ctk.CTkLabel(
            self.search_tab,
            text=(
                "Este límite evita que un archivo enorme congele la lectura de contenido. "
                "El recorrido seguro sigue viniendo de FileScanCore; Smart Filter decide qué leer."
            ),
            font=self.font_config.tuple("small"),
            text_color=("gray35", "gray72"),
            anchor="w",
            justify="left",
            wraplength=430,
        )
        row = self._grid_pair(self.max_content_combo, self.max_content_help, row)

    def _build_performance_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.performance_tab,
            row,
            "Uso de recursos",
            "El modo automático reserva capacidad para el sistema y adapta lectores, procesos CPU y colas al equipo detectado.",
        )
        self.resource_profile_combo = LabeledComboBox(
            self.performance_tab,
            "Perfil",
            get_resource_profile_options(),
            font_config=self.font_config,
            command=lambda _value: self._update_performance_preview(),
        )
        self.processing_mode_combo = LabeledComboBox(
            self.performance_tab,
            "Configuración",
            get_processing_mode_options(),
            font_config=self.font_config,
            command=lambda _value: self._toggle_manual_performance_options(),
        )
        row = self._grid_pair(self.resource_profile_combo, self.processing_mode_combo, row)

        self.performance_preview_label = self.ctk.CTkLabel(
            self.performance_tab,
            text="Detectando CPU...",
            font=self.font_config.tuple("body"),
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self.performance_preview_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row += 1

        self.performance_monitor_switch = LabeledSwitch(
            self.performance_tab,
            "Registrar CPU y memoria en el JSON",
            default=True,
            font_config=self.font_config,
        )
        self.performance_timeline_switch = LabeledSwitch(
            self.performance_tab,
            "Guardar cronología reducida cada 10 segundos",
            default=True,
            font_config=self.font_config,
        )
        row = self._grid_pair(self.performance_monitor_switch, self.performance_timeline_switch, row)

        row = self._section_label(
            self.performance_tab,
            row,
            "Control técnico manual",
            "Solo se habilita en Manual técnico. Smart Filter limita valores incompatibles con la CPU detectada.",
        )
        self.manual_analysis_processes_entry = LabeledEntry(
            self.performance_tab, "Procesos de análisis", placeholder="2", font_config=self.font_config
        )
        self.manual_reader_workers_entry = LabeledEntry(
            self.performance_tab, "Lectores", placeholder="4", font_config=self.font_config
        )
        row = self._grid_pair(self.manual_analysis_processes_entry, self.manual_reader_workers_entry, row)

        self.manual_reserved_cores_entry = LabeledEntry(
            self.performance_tab, "Núcleos físicos reservados", placeholder="2", font_config=self.font_config
        )
        self.manual_pending_batches_entry = LabeledEntry(
            self.performance_tab, "Máximo de lotes pendientes", placeholder="4", font_config=self.font_config
        )
        row = self._grid_pair(self.manual_reserved_cores_entry, self.manual_pending_batches_entry, row)

        self.performance_warning_label = self.ctk.CTkLabel(
            self.performance_tab,
            text=(
                "Alto rendimiento y Manual técnico pueden aumentar CPU, RAM, temperatura y consumo. "
                "Equilibrado es el valor recomendado para uso normal."
            ),
            font=self.font_config.tuple("small"),
            text_color=("#8a5b00", "#fbbf24"),
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self.performance_warning_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    def _performance_settings_preview(self) -> dict[str, Any]:
        return {
            "processing_mode": self.processing_mode_combo.get_label(),
            "resource_profile": self.resource_profile_combo.get_label(),
            "manual_analysis_processes": self.manual_analysis_processes_entry.get_value(),
            "manual_reader_workers": self.manual_reader_workers_entry.get_value(),
            "manual_reserved_cores": self.manual_reserved_cores_entry.get_value(),
            "manual_max_pending_batches": self.manual_pending_batches_entry.get_value(),
            "performance_monitor_enabled": self.performance_monitor_switch.get_value(),
            "performance_timeline_enabled": self.performance_timeline_switch.get_value(),
        }

    def _update_performance_preview(self) -> None:
        try:
            policy = resolve_resource_policy(self._performance_settings_preview())
            mode_label = "manual" if policy.manual_override else "automático"
            self.performance_preview_label.configure(
                text=(
                    f"CPU detectada: {policy.physical_cores} núcleos físicos / "
                    f"{policy.logical_cores} hilos · modo {mode_label} · "
                    f"reserva {policy.reserved_system_cores} · "
                    f"Smart Filter: {policy.analysis_processes} proceso(s) CPU + "
                    f"{policy.reader_workers} lector(es) · "
                    f"máximo {policy.max_pending_batches} lotes pendientes."
                )
            )
        except Exception as exc:
            self.performance_preview_label.configure(text=f"No se pudo calcular la política: {exc}")

    def _toggle_manual_performance_options(self) -> None:
        manual = self.processing_mode_combo.get_label() == "Manual técnico"
        widgets = (
            self.manual_analysis_processes_entry,
            self.manual_reader_workers_entry,
            self.manual_reserved_cores_entry,
            self.manual_pending_batches_entry,
        )
        for widget in widgets:
            frame = getattr(widget, "frame", widget)
            try:
                if manual:
                    frame.grid()
                else:
                    frame.grid_remove()
            except Exception:
                pass
        self._update_performance_preview()

    def _build_output_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.output_tab,
            row,
            "Salida y acciones",
            "Preferencias para guardar/exportar resultados sin cambiar el motor de búsqueda.",
        )
        self.output_prefix_entry = LabeledEntry(self.output_tab, "Prefijo carpeta de salida", font_config=self.font_config)
        self.auto_open_switch = LabeledSwitch(self.output_tab, "Abrir carpeta de salida automáticamente", font_config=self.font_config)
        row = self._grid_pair(self.output_prefix_entry, self.auto_open_switch, row)

        self.csv_report_switch = LabeledSwitch(self.output_tab, "Crear reporte CSV al guardar", font_config=self.font_config)
        self.preserve_structure_switch = LabeledSwitch(
            self.output_tab, "Preservar estructura de carpetas al copiar", font_config=self.font_config
        )
        row = self._grid_pair(self.csv_report_switch, self.preserve_structure_switch, row)

    def _build_highlight_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.highlight_tab,
            row,
            "Destacado visual",
            "El botón Destacado y el doble clic visual abren el visor HTML; Abrir conserva el archivo original sin crear copias temporales.",
        )
        self.highlight_switch = LabeledSwitch(
            self.highlight_tab, "Destacar términos al abrir vista temporal", font_config=self.font_config
        )
        self.open_mode_combo = LabeledComboBox(
            self.highlight_tab, "Acción con doble clic", get_open_result_mode_options(), font_config=self.font_config
        )
        row = self._grid_pair(self.highlight_switch, self.open_mode_combo, row)

        self.highlight_cell_combo = LabeledComboBox(
            self.highlight_tab, "Color de celda", get_highlight_cell_color_options(), font_config=self.font_config
        )
        self.highlight_text_combo = LabeledComboBox(
            self.highlight_tab, "Color de texto", get_highlight_text_color_options(), font_config=self.font_config
        )
        row = self._grid_pair(self.highlight_cell_combo, self.highlight_text_combo, row)

    def _build_visual_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.visual_tab,
            row,
            "Paleta visual",
            "Apariencia, color principal, base visual, fuente y densidad de tabla. La vista previa pesada fue removida para dejar esta sección limpia.",
        )
        self.appearance_combo = LabeledComboBox(
            self.visual_tab,
            "Apariencia",
            APPEARANCE_LABEL_OPTIONS,
            font_config=self.font_config,
            command=lambda _value: self._update_palette_preview(),
        )
        self.color_combo = LabeledComboBox(
            self.visual_tab,
            "Color principal",
            COLOR_THEME_LABEL_OPTIONS,
            font_config=self.font_config,
            command=lambda _value: self._update_palette_preview(),
        )
        row = self._grid_pair(self.appearance_combo, self.color_combo, row)

        self.surface_combo = LabeledComboBox(
            self.visual_tab,
            "Base visual",
            SMARTFILTER_SURFACE_THEME_LABEL_OPTIONS,
            font_config=self.font_config,
            command=lambda _value: self._update_palette_preview(),
        )
        self.density_combo = LabeledComboBox(
            self.visual_tab, "Densidad visual", get_results_density_options(), font_config=self.font_config
        )
        row = self._grid_pair(self.surface_combo, self.density_combo, row)

        self.font_family_combo = LabeledComboBox(
            self.visual_tab, "Fuente", get_app_font_family_options(), font_config=self.font_config
        )
        self.font_size_combo = LabeledComboBox(
            self.visual_tab, "Tamaño de fuente", get_app_font_size_options(), font_config=self.font_config
        )
        row = self._grid_pair(self.font_family_combo, self.font_size_combo, row)

        row = self._section_label(
            self.visual_tab,
            row,
            "Panel de métricas",
            "Las cajas superiores aparecen como resumen final al terminar la búsqueda.",
        )
        self.metric_size_combo = LabeledComboBox(
            self.visual_tab,
            "Tamaño de métricas",
            get_metric_card_size_options(),
            font_config=self.font_config,
        )
        self.metric_style_combo = LabeledComboBox(
            self.visual_tab,
            "Estilo de color",
            get_metric_card_style_options(),
            font_config=self.font_config,
        )
        row = self._grid_pair(self.metric_size_combo, self.metric_style_combo, row)

        row = self._section_label(
            self.visual_tab,
            row,
            "Color avanzado",
        )
        self.custom_accent_row_frame = self.ctk.CTkFrame(self.visual_tab, fg_color="transparent")
        self.custom_accent_row_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.custom_accent_row_frame.grid_columnconfigure(0, weight=0, minsize=ADVANCED_COLOR_SWITCH_WIDTH)
        self.custom_accent_row_frame.grid_columnconfigure(1, weight=0, minsize=ADVANCED_COLOR_BUTTON_WIDTH)
        self.custom_accent_row_frame.grid_columnconfigure(2, weight=1)
        self.custom_accent_selected_label = DEFAULT_CUSTOM_ACCENT_LABEL
        self.custom_accent_selected_hex = CUSTOM_ACCENT_HEX_BY_LABEL[DEFAULT_CUSTOM_ACCENT_LABEL]

        self.custom_accent_switch = self.ctk.CTkSwitch(
            self.custom_accent_row_frame,
            text="Usar color principal personalizado",
            command=self._toggle_custom_accent_options,
            font=self.font_config.tuple("small"),
            width=ADVANCED_COLOR_SWITCH_WIDTH,
        )
        self.custom_accent_switch.grid(row=0, column=0, sticky="w", padx=(0, 8))


        self.custom_accent_button = self.ctk.CTkButton(
            self.custom_accent_row_frame,
            text="Elegir color",
            height=30,
            width=ADVANCED_COLOR_BUTTON_WIDTH,
            command=self._open_custom_accent_palette,
            font=self.font_config.tuple("small"),
        )
        self.custom_accent_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.custom_accent_sample = self.ctk.CTkLabel(
            self.custom_accent_row_frame,
            text="Azul · #1f6aa5",
            height=30,
            corner_radius=7,
            font=self.font_config.tuple("small", "bold"),
        )
        self.custom_accent_sample.grid(row=0, column=2, sticky="ew")
        row += 1

        self.custom_surface_row_frame = self.ctk.CTkFrame(self.visual_tab, fg_color="transparent")
        self.custom_surface_row_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.custom_surface_row_frame.grid_columnconfigure(0, weight=0, minsize=ADVANCED_COLOR_SWITCH_WIDTH)
        self.custom_surface_row_frame.grid_columnconfigure(1, weight=0, minsize=ADVANCED_COLOR_BUTTON_WIDTH)
        self.custom_surface_row_frame.grid_columnconfigure(2, weight=1)
        self.custom_surface_selected_hex = DEFAULT_CUSTOM_SURFACE_HEX

        self.custom_surface_switch = self.ctk.CTkSwitch(
            self.custom_surface_row_frame,
            text="Usar base visual personalizada",
            command=self._toggle_custom_surface_options,
            font=self.font_config.tuple("small"),
            width=ADVANCED_COLOR_SWITCH_WIDTH,
        )
        self.custom_surface_switch.grid(row=0, column=0, sticky="w", padx=(0, 8))


        self.custom_surface_button = self.ctk.CTkButton(
            self.custom_surface_row_frame,
            text="Elegir base",
            height=30,
            width=ADVANCED_COLOR_BUTTON_WIDTH,
            command=self._open_custom_surface_palette,
            font=self.font_config.tuple("small"),
        )
        self.custom_surface_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.custom_surface_sample = self.ctk.CTkLabel(
            self.custom_surface_row_frame,
            text="Base visual · #1b2430",
            height=30,
            corner_radius=7,
            font=self.font_config.tuple("small", "bold"),
        )
        self.custom_surface_sample.grid(row=0, column=2, sticky="ew")
        row += 1

        self.visual_help_label = self.ctk.CTkLabel(
            self.visual_tab,
            text=(
                "Los cambios se guardan en ConfigCore. Los modos avanzados de color principal y base visual afectan los "
                "controles propios de Smart Filter y se combinan con las paletas seguras de GuiCore."
            ),
            font=self.font_config.tuple("small"),
            text_color=("gray35", "gray72"),
            justify="left",
            anchor="w",
            wraplength=900,
        )
        self.visual_help_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 8))


    def _normalize_custom_accent_hex(self, value: Any) -> str:
        return _normalize_hex_color(value)

    def _selected_custom_accent_hex(self) -> str:
        return self._normalize_custom_accent_hex(getattr(self, "custom_accent_selected_hex", None))

    def _set_custom_accent_hex(self, value: Any) -> str:
        color = self._normalize_custom_accent_hex(value)
        label = _custom_accent_label_for_hex(color)
        self.custom_accent_selected_label = label
        self.custom_accent_selected_hex = color
        self._update_custom_accent_sample()
        return color

    def _select_custom_accent(self, label: str, color: str, palette_window: Any | None = None) -> None:
        self.custom_accent_selected_label = label if label in CUSTOM_ACCENT_LABELS else DEFAULT_CUSTOM_ACCENT_LABEL
        self.custom_accent_selected_hex = self._normalize_custom_accent_hex(color)
        self._update_custom_accent_sample()
        if palette_window is not None:
            try:
                palette_window.destroy()
            except Exception:
                pass

    def _update_custom_accent_sample(self) -> None:
        color = self._selected_custom_accent_hex()
        text_color = _contrast_text_color(color)
        self.custom_accent_selected_label = _custom_accent_label_for_hex(color)
        self.custom_accent_button.configure(
            fg_color=color,
            hover_color=color,
            text_color=text_color,
        )
        self.custom_accent_sample.configure(
            text=f"Color principal · {color}",
            fg_color=color,
            text_color=text_color,
        )

    def _open_custom_accent_palette(self) -> None:
        current_color = self._selected_custom_accent_hex()
        try:
            _rgb, selected_hex = colorchooser.askcolor(
                color=current_color,
                title="Elegir color principal personalizado",
                parent=self.parent,
            )
        except Exception:
            selected_hex = None

        if selected_hex:
            self._set_custom_accent_hex(selected_hex)

    def _toggle_custom_accent_options(self) -> None:
        enabled = bool(self.custom_accent_switch.get())
        widgets = (
            self.custom_accent_button,
            self.custom_accent_sample,
        )
        if enabled:
            self.custom_accent_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
            self.custom_accent_sample.grid(row=0, column=2, sticky="ew")
            self._update_custom_accent_sample()
            return
        for widget in widgets:
            try:
                widget.grid_remove()
            except Exception:
                pass

    def _normalize_custom_surface_hex(self, value: Any) -> str:
        return _normalize_hex_color(value)

    def _selected_custom_surface_hex(self) -> str:
        return self._normalize_custom_surface_hex(getattr(self, "custom_surface_selected_hex", None) or DEFAULT_CUSTOM_SURFACE_HEX)

    def _set_custom_surface_hex(self, value: Any) -> str:
        color = self._normalize_custom_surface_hex(value)
        self.custom_surface_selected_hex = color
        self._update_custom_surface_sample()
        return color

    def _update_custom_surface_sample(self) -> None:
        color = self._selected_custom_surface_hex()
        text_color = _contrast_text_color(color)
        self.custom_surface_button.configure(
            fg_color=color,
            hover_color=color,
            text_color=text_color,
        )
        self.custom_surface_sample.configure(
            text=f"Base visual · {color}",
            fg_color=color,
            text_color=text_color,
        )

    def _open_custom_surface_palette(self) -> None:
        current_color = self._selected_custom_surface_hex()
        try:
            _rgb, selected_hex = colorchooser.askcolor(
                color=current_color,
                title="Elegir base visual personalizada",
                parent=self.parent,
            )
        except Exception:
            selected_hex = None
        if selected_hex:
            self._set_custom_surface_hex(selected_hex)

    def _toggle_custom_surface_options(self) -> None:
        enabled = bool(self.custom_surface_switch.get())
        widgets = (
            self.custom_surface_button,
            self.custom_surface_sample,
        )
        if enabled:
            self.custom_surface_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
            self.custom_surface_sample.grid(row=0, column=2, sticky="ew")
            self._update_custom_surface_sample()
            return
        for widget in widgets:
            try:
                widget.grid_remove()
            except Exception:
                pass

    def _build_experience_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.experience_tab,
            row,
            "Experiencia",
            "Opciones separadas para recordar historial, modo, ruta y últimos filtros sin depender de un único tick.",
        )
        self.remember_use_switch = LabeledSwitch(self.experience_tab, "Recordar uso general", font_config=self.font_config)
        self.history_switch = LabeledSwitch(self.experience_tab, "Guardar historial de búsquedas", font_config=self.font_config)
        row = self._grid_pair(self.remember_use_switch, self.history_switch, row)

        self.mode_switch = LabeledSwitch(self.experience_tab, "Recordar último modo", font_config=self.font_config)
        self.location_switch = LabeledSwitch(self.experience_tab, "Recordar última carpeta/archivo", font_config=self.font_config)
        row = self._grid_pair(self.mode_switch, self.location_switch, row)

        self.search_settings_switch = LabeledSwitch(
            self.experience_tab, "Recordar última búsqueda/filtros", font_config=self.font_config
        )
        self.search_settings_switch.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    def _build_filters_tab(self) -> None:
        row = 0
        row = self._section_label(
            self.filters_tab,
            row,
            "Escaneo amplio seguro",
            "Se activa únicamente al buscar desde una raíz de disco o volumen. Cada opción poda la carpeta completa antes de recorrer sus subcarpetas.",
        )

        self.broad_scan_safe_switch = LabeledSwitch(
            self.filters_tab,
            "Activar en raíces de disco",
            default=True,
            font_config=self.font_config,
            command=self._toggle_broad_scan_options,
        )
        self.broad_scan_safe_switch.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        row += 1

        self.broad_scan_group_switches: dict[str, LabeledSwitch] = {}
        option_switches: list[LabeledSwitch] = []
        for option in BROAD_SCAN_OPTIONS:
            switch = LabeledSwitch(
                self.filters_tab,
                option.label,
                default=option.default_enabled,
                font_config=self.font_config,
            )
            self.broad_scan_group_switches[option.group_id] = switch
            option_switches.append(switch)

        for index in range(0, len(option_switches), 2):
            left = option_switches[index]
            right = option_switches[index + 1] if index + 1 < len(option_switches) else None
            row = self._grid_pair(left, right, row, pady=(0, 8))

        self.broad_scan_hint_label = self.ctk.CTkLabel(
            self.filters_tab,
            text="Pase el cursor sobre cada opción para ver exactamente qué carpetas excluye.",
            text_color=("gray35", "gray72"),
            font=self.font_config.tuple("small"),
            anchor="w",
        )
        self.broad_scan_hint_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        row += 1

        row = self._section_label(
            self.filters_tab,
            row,
            "Exclusiones manuales",
            "Ignorar carpetas/archivos por nombre flexible o por ruta exacta elegida desde el sistema.",
        )

        self.ignored_folder_entry = LabeledEntry(
            self.filters_tab,
            "Nombre de carpeta a ignorar",
            placeholder="Ej.: node_modules, backup, temporal",
            font_config=self.font_config,
        )
        self.ignored_file_entry = LabeledEntry(
            self.filters_tab,
            "Nombre de archivo a ignorar",
            placeholder="Ej.: .tmp, ~$ , cache",
            font_config=self.font_config,
        )
        row = self._grid_pair(self.ignored_folder_entry, self.ignored_file_entry, row, pady=(0, 6))

        folder_actions = self._build_ignore_actions_frame(
            self.filters_tab,
            add_label="+ Nombre",
            add_command=lambda: self._add_ignored_keyword("folder"),
            select_label="Elegir carpeta",
            select_command=self._choose_ignored_folder_path,
        )
        file_actions = self._build_ignore_actions_frame(
            self.filters_tab,
            add_label="+ Nombre",
            add_command=lambda: self._add_ignored_keyword("file"),
            select_label="Elegir archivo",
            select_command=self._choose_ignored_file_path,
        )
        row = self._grid_pair(folder_actions, file_actions, row, pady=(0, 8))

        self.ignored_folder_list_label = self.ctk.CTkLabel(
            self.filters_tab, text="Carpetas ignoradas", font=self.font_config.tuple("small", "bold"), anchor="w"
        )
        self.ignored_folder_list_label.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(0, 4))
        self.ignored_file_list_label = self.ctk.CTkLabel(
            self.filters_tab, text="Archivos ignorados", font=self.font_config.tuple("small", "bold"), anchor="w"
        )
        self.ignored_file_list_label.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(0, 4))
        row += 1

        self.ignored_folder_box = self.ctk.CTkTextbox(self.filters_tab, height=100, font=self.font_config.tuple("body"), wrap="word")
        self.ignored_folder_box.grid(row=row, column=0, sticky="nsew", padx=(0, 8), pady=(0, 4))
        self.ignored_file_box = self.ctk.CTkTextbox(self.filters_tab, height=100, font=self.font_config.tuple("body"), wrap="word")
        self.ignored_file_box.grid(row=row, column=1, sticky="nsew", padx=(8, 0), pady=(0, 4))
        row += 1

        self.remove_ignored_folder_button = ActionButton(
            self.filters_tab,
            "Quitar seleccionado",
            command=lambda: self._remove_selected_ignore_item("folder"),
            style="ghost",
            font_config=self.font_config,
        )
        self.remove_ignored_folder_button.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        self.remove_ignored_file_button = ActionButton(
            self.filters_tab,
            "Quitar seleccionado",
            command=lambda: self._remove_selected_ignore_item("file"),
            style="ghost",
            font_config=self.font_config,
        )
        self.remove_ignored_file_button.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
        row += 1

        self.ignored_hint_label = self.ctk.CTkLabel(
            self.filters_tab,
            text="Nombre = coincide por texto. Ruta = exclusión exacta; una carpeta excluida no se recorre ni entrega subcarpetas.",
            text_color=("gray35", "gray72"),
            font=self.font_config.tuple("small"),
            anchor="w",
        )
        self.ignored_hint_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        row = self._section_label(
            self.filters_tab,
            row,
            "Datos guardados",
            "Historial y términos de descarte acumulados por el uso. Se pueden limpiar desde los botones inferiores.",
        )
        self.saved_terms_label = self.ctk.CTkLabel(
            self.filters_tab, text="Términos de descarte guardados", font=self.font_config.tuple("small", "bold"), anchor="w"
        )
        self.saved_terms_label.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(0, 4))
        self.history_label = self.ctk.CTkLabel(
            self.filters_tab, text="Historial de búsquedas", font=self.font_config.tuple("small", "bold"), anchor="w"
        )
        self.history_label.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(0, 4))
        row += 1

        self.saved_terms_box = self.ctk.CTkTextbox(self.filters_tab, height=100, font=self.font_config.tuple("body"), wrap="word")
        self.saved_terms_box.grid(row=row, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        self.history_box = self.ctk.CTkTextbox(self.filters_tab, height=100, font=self.font_config.tuple("body"), wrap="word")
        self.history_box.grid(row=row, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        row += 1

        self.status_label = self.ctk.CTkLabel(
            self.filters_tab, text="", text_color="gray", font=self.font_config.tuple("small"), anchor="w"
        )
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    def _toggle_broad_scan_options(self) -> None:
        enabled = self.broad_scan_safe_switch.get_value()
        for switch in self.broad_scan_group_switches.values():
            switch.set_enabled(enabled)

    def _build_footer(self) -> None:
        self.restore_defaults_button = ActionButton(
            self.window.footer_frame, "Restaurar defecto", command=self._restore_defaults, style="ghost", font_config=self.font_config
        )
        self.restore_defaults_button.grid(row=0, column=0, padx=(0, 10), sticky="e")
        self.save_button = ActionButton(self.window.footer_frame, "Guardar", command=self._save, style="primary", font_config=self.font_config)
        self.save_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
        self.clear_history_button = ActionButton(
            self.window.footer_frame, "Borrar historial", command=self._clear_history, style="ghost", font_config=self.font_config
        )
        self.clear_history_button.grid(row=0, column=2, padx=(10, 0), sticky="e")
        self.clear_terms_button = ActionButton(
            self.window.footer_frame, "Borrar descartes", command=self._clear_saved_terms, style="ghost", font_config=self.font_config
        )
        self.clear_terms_button.grid(row=0, column=3, padx=(10, 0), sticky="e")
        self.close_button = ActionButton(self.window.footer_frame, "Cerrar", command=self.window.close, style="secondary", font_config=self.font_config)
        self.close_button.grid(row=0, column=4, padx=(10, 0), sticky="e")

    def _set_textbox(self, widget: Any, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def _get_textbox(self, widget: Any) -> str:
        return str(widget.get("1.0", "end")).strip()

    def _set_keyword_box_from_value(self, widget: Any, value: Any) -> None:
        self._set_textbox(widget, _list_to_lines(_lines_to_list(str(value or ""))))

    def _keyword_box_value(self, widget: Any, pending_value: str = "") -> str:
        values = _lines_to_list(f"{self._get_textbox(widget)}\n{pending_value or ''}")
        return ", ".join(values)

    def _ignored_box_values(self, target: str) -> tuple[list[str], list[str]]:
        box = self.ignored_folder_box if target == "folder" else self.ignored_file_box
        return _parse_prefixed_ignore_lines(self._get_textbox(box))

    def _set_ignored_box_values(self, target: str, keywords: list[str], paths: list[str]) -> None:
        box = self.ignored_folder_box if target == "folder" else self.ignored_file_box
        self._set_textbox(box, _prefixed_ignore_lines(keywords, paths))

    def _add_ignored_keyword(self, target: str) -> None:
        if target == "folder":
            entry = self.ignored_folder_entry
            label = "carpetas"
        else:
            entry = self.ignored_file_entry
            label = "archivos"

        current_keywords, current_paths = self._ignored_box_values(target)
        new_values = _lines_to_list(entry.get_value())
        if not new_values:
            self.status_label.configure(text=f"No hay nombres de {label} para agregar.")
            return

        seen = {item.casefold() for item in current_keywords}
        added = 0
        for value in new_values:
            lookup = value.casefold()
            if lookup in seen:
                continue
            current_keywords.append(value)
            seen.add(lookup)
            added += 1

        self._set_ignored_box_values(target, current_keywords, current_paths)
        entry.set_value("")
        self.status_label.configure(text=f"Nombres de {label} agregados: {added}.")

    def _add_ignored_path(self, target: str, selected_path: str) -> None:
        clean_path = _clean_ignore_item(selected_path)
        if not clean_path:
            return
        current_keywords, current_paths = self._ignored_box_values(target)
        seen = {item.casefold() for item in current_paths}
        if clean_path.casefold() not in seen:
            current_paths.append(clean_path)
        self._set_ignored_box_values(target, current_keywords, current_paths)
        label = "carpeta" if target == "folder" else "archivo"
        self.status_label.configure(text=f"Ruta exacta de {label} agregada. Guardar cambios para conservar la exclusión.")

    def _remove_selected_ignore_item(self, target: str) -> None:
        box = self.ignored_folder_box if target == "folder" else self.ignored_file_box
        label = "carpetas" if target == "folder" else "archivos"
        raw_lines = str(box.get("1.0", "end")).splitlines()
        if not any(line.strip() for line in raw_lines):
            self.status_label.configure(text=f"No hay exclusiones de {label} para quitar.")
            return

        try:
            start_index = box.index("sel.first")
            end_index = box.index("sel.last")
        except Exception:
            start_index = box.index("insert linestart")
            end_index = box.index("insert lineend")

        try:
            start_line = max(1, int(str(start_index).split(".")[0]))
            end_parts = str(end_index).split(".")
            end_line = max(start_line, int(end_parts[0]))
            end_column = int(end_parts[1]) if len(end_parts) > 1 and end_parts[1].isdigit() else 0
        except Exception:
            self.status_label.configure(text=f"Seleccionar una exclusión de {label} para quitar.")
            return

        if end_column == 0 and end_line > start_line:
            end_line -= 1

        total_lines = len(raw_lines)
        start_line = min(start_line, total_lines)
        end_line = min(max(end_line, start_line), total_lines)
        selected_numbers = set(range(start_line, end_line + 1))
        selected_items = [line.strip() for index, line in enumerate(raw_lines, start=1) if index in selected_numbers and line.strip()]
        if not selected_items:
            self.status_label.configure(text=f"Seleccionar una exclusión de {label} para quitar.")
            return

        kept_text = "\n".join(
            line.strip()
            for index, line in enumerate(raw_lines, start=1)
            if index not in selected_numbers and line.strip()
        )
        current_keywords, current_paths = _parse_prefixed_ignore_lines(kept_text)
        self._set_ignored_box_values(target, current_keywords, current_paths)
        self.status_label.configure(text=f"Exclusiones de {label} quitadas: {len(selected_items)}. Guardar cambios para conservar la modificación.")

    def _choose_ignored_folder_path(self) -> None:
        selected = filedialog.askdirectory(title="Elegir carpeta exacta para ignorar")
        if selected:
            self._add_ignored_path("folder", selected)

    def _choose_ignored_file_path(self) -> None:
        selected = filedialog.askopenfilename(title="Elegir archivo exacto para ignorar")
        if selected:
            self._add_ignored_path("file", selected)

    def _ignored_save_values(self, target: str, pending_value: str = "") -> tuple[str, list[str]]:
        keywords, paths = self._ignored_box_values(target)
        seen = {item.casefold() for item in keywords}
        for pending in _lines_to_list(pending_value):
            lookup = pending.casefold()
            if lookup not in seen:
                keywords.append(pending)
                seen.add(lookup)
        return ", ".join(keywords), paths

    def _update_palette_preview(self) -> None:
        try:
            appearance = normalize_appearance_value(self.appearance_combo.get_label())
            accent = normalize_color_theme(self.color_combo.get_label())
            surface = normalize_surface_theme(_safe_surface_theme_label(self.surface_combo.get_label()))
            self.window.apply_visual_preferences(self.font_config, accent, surface, appearance)
            if hasattr(self, "custom_accent_sample"):
                self._update_custom_accent_sample()
            if hasattr(self, "custom_surface_sample"):
                self._update_custom_surface_sample()
            if hasattr(self, "settings_tab_buttons"):
                self._style_settings_chrome()
        except Exception:
            return


    def _load_values(self) -> None:
        settings = get_settings()
        prefs = load_gui_preferences()
        self.settings = settings
        self.preferences = prefs

        self.default_file_type_combo.set_value(str(settings.get("default_file_type")))
        self.search_scope_combo.set_value(str(settings.get("default_search_scope")))
        self.max_content_combo.set_value(str(settings.get("max_content_file_size")))
        self.resource_profile_combo.set_value(str(settings.get("resource_profile", "Equilibrado")))
        self.processing_mode_combo.set_value(str(settings.get("processing_mode", "Automático")))
        self.manual_analysis_processes_entry.set_value(str(settings.get("manual_analysis_processes", 2)))
        self.manual_reader_workers_entry.set_value(str(settings.get("manual_reader_workers", 4)))
        self.manual_reserved_cores_entry.set_value(str(settings.get("manual_reserved_cores", 2)))
        self.manual_pending_batches_entry.set_value(str(settings.get("manual_max_pending_batches", 4)))
        self.performance_monitor_switch.set_value(bool(settings.get("performance_monitor_enabled", True)))
        self.performance_timeline_switch.set_value(bool(settings.get("performance_timeline_enabled", True)))
        self._toggle_manual_performance_options()
        self.output_prefix_entry.set_value(str(settings.get("output_folder_prefix")))
        self.auto_open_switch.set_value(bool(settings.get("auto_open_output_folder")))
        self.csv_report_switch.set_value(bool(settings.get("create_csv_report_on_save")))
        self.preserve_structure_switch.set_value(bool(settings.get("preserve_folder_structure_on_save")))
        self.highlight_switch.set_value(bool(settings.get("highlight_search_terms_on_open")))
        self.open_mode_combo.set_value(str(settings.get("open_result_mode")))
        self.highlight_cell_combo.set_value(str(settings.get("highlight_cell_color")))
        self.highlight_text_combo.set_value(str(settings.get("highlight_text_color")))

        self.appearance_combo.set_value(normalize_appearance_label(prefs.appearance_mode))
        self.color_combo.set_value(normalize_color_theme_label(prefs.color_theme))
        self.surface_combo.set_value(_safe_surface_theme_label(prefs.surface_theme))
        self.density_combo.set_value(str(settings.get("results_density")))
        self.font_family_combo.set_value(str(settings.get("app_font_family")))
        self.font_size_combo.set_value(str(settings.get("app_font_size")))
        self.metric_size_combo.set_value(str(settings.get("metric_card_size")))
        self.metric_style_combo.set_value(str(settings.get("metric_card_style")))
        if bool(settings.get("custom_accent_enabled")):
            self.custom_accent_switch.select()
        else:
            self.custom_accent_switch.deselect()
        self._set_custom_accent_hex(settings.get("custom_accent_hex") or "#1f6aa5")
        self._toggle_custom_accent_options()
        if bool(settings.get("custom_surface_enabled")):
            self.custom_surface_switch.select()
        else:
            self.custom_surface_switch.deselect()
        self._set_custom_surface_hex(settings.get("custom_surface_hex") or DEFAULT_CUSTOM_SURFACE_HEX)
        self._toggle_custom_surface_options()
        self._update_palette_preview()

        self.remember_use_switch.set_value(bool(settings.get("remember_last_use")))
        self.history_switch.set_value(bool(settings.get("save_search_history")))
        self.mode_switch.set_value(bool(settings.get("remember_last_analysis_mode")))
        self.location_switch.set_value(bool(settings.get("remember_last_location")))
        self.search_settings_switch.set_value(bool(settings.get("remember_last_search_settings")))
        self.broad_scan_safe_switch.set_value(bool(settings.get(BROAD_SCAN_ENABLED_KEY, True)))
        for option in BROAD_SCAN_OPTIONS:
            self.broad_scan_group_switches[option.group_id].set_value(
                bool(settings.get(option.setting_key, option.default_enabled))
            )
        self._toggle_broad_scan_options()
        self.ignored_folder_entry.set_value("")
        self.ignored_file_entry.set_value("")
        self._set_textbox(
            self.ignored_folder_box,
            _prefixed_ignore_lines(
                _lines_to_list(settings.get("ignored_folder_keywords") or ""),
                settings.get("ignored_folder_paths") or [],
            ),
        )
        self._set_textbox(
            self.ignored_file_box,
            _prefixed_ignore_lines(
                _lines_to_list(settings.get("ignored_file_keywords") or ""),
                settings.get("ignored_file_paths") or [],
            ),
        )
        self._set_textbox(self.saved_terms_box, _list_to_lines(settings.get("saved_discard_terms", [])))
        self._set_textbox(self.history_box, _list_to_lines(settings.get("search_history", [])))
        self.status_label.configure(
            text=f"Configuración cargada · historial={len(settings.get('search_history', []))} · descartes={len(settings.get('saved_discard_terms', []))}"
        )

    def _save(self) -> None:
        try:
            save_settings(
                default_file_type=self.default_file_type_combo.get_label(),
                default_search_scope=self.search_scope_combo.get_label(),
                auto_open_output_folder=self.auto_open_switch.get_value(),
                theme=self.appearance_combo.get_label(),
                processing_mode=self.processing_mode_combo.get_label(),
                resource_profile=self.resource_profile_combo.get_label(),
                manual_analysis_processes=self.manual_analysis_processes_entry.get_value(),
                manual_reader_workers=self.manual_reader_workers_entry.get_value(),
                manual_reserved_cores=self.manual_reserved_cores_entry.get_value(),
                manual_max_pending_batches=self.manual_pending_batches_entry.get_value(),
                performance_monitor_enabled=self.performance_monitor_switch.get_value(),
                performance_timeline_enabled=self.performance_timeline_switch.get_value(),
                performance_sample_interval_seconds=1.0,
                performance_timeline_interval_seconds=10.0,
                output_folder_prefix=self.output_prefix_entry.get_value(),
                create_csv_report_on_save=self.csv_report_switch.get_value(),
                preserve_folder_structure_on_save=self.preserve_structure_switch.get_value(),
                max_content_file_size=self.max_content_combo.get_label(),
                highlight_search_terms_on_open=self.highlight_switch.get_value(),
                highlight_cell_color=self.highlight_cell_combo.get_label(),
                highlight_text_color=self.highlight_text_combo.get_label(),
                open_result_mode=self.open_mode_combo.get_label(),
                results_density=self.density_combo.get_label(),
                app_font_family=self.font_family_combo.get_label(),
                app_font_size=self.font_size_combo.get_label(),
                custom_accent_enabled=bool(self.custom_accent_switch.get()),
                custom_accent_hex=self._selected_custom_accent_hex(),
                custom_surface_enabled=bool(self.custom_surface_switch.get()),
                custom_surface_hex=self._selected_custom_surface_hex(),
                show_metrics_before_search=False,
                metric_card_size=self.metric_size_combo.get_label(),
                metric_card_style=self.metric_style_combo.get_label(),
                save_search_history=self.history_switch.get_value(),
                remember_last_analysis_mode=self.mode_switch.get_value(),
                remember_last_location=self.location_switch.get_value(),
                remember_last_search_settings=self.search_settings_switch.get_value(),
                remember_last_use=self.remember_use_switch.get_value(),
                ignored_folder_keywords=self._ignored_save_values("folder", self.ignored_folder_entry.get_value())[0],
                ignored_file_keywords=self._ignored_save_values("file", self.ignored_file_entry.get_value())[0],
                ignored_folder_paths=self._ignored_save_values("folder", self.ignored_folder_entry.get_value())[1],
                ignored_file_paths=self._ignored_save_values("file", self.ignored_file_entry.get_value())[1],
                broad_scan_safe_enabled=self.broad_scan_safe_switch.get_value(),
                **{
                    option.setting_key: self.broad_scan_group_switches[option.group_id].get_value()
                    for option in BROAD_SCAN_OPTIONS
                },
            )
            preferences = GuiPreferences(
                appearance_mode=normalize_appearance_value(self.appearance_combo.get_label()),
                color_theme=normalize_color_theme(self.color_combo.get_label()),
                surface_theme=normalize_surface_theme(_safe_surface_theme_label(self.surface_combo.get_label())),
                font_family=self.font_family_combo.get_label(),
                font_size=self.font_size_combo.get_label(),
                table_density=self.density_combo.get_label(),
            ).normalized()
            save_gui_preferences(preferences)
            # Los términos guardados son parte de settings plano; se guardan aquí después de mantener visual.
            current_settings = get_settings()
            current_settings["saved_discard_terms"] = _lines_to_list(self._get_textbox(self.saved_terms_box))
            current_settings["search_history"] = _lines_to_list(self._get_textbox(self.history_box))
            from smart_filter.services.settings_service import write_settings

            write_settings(current_settings)
        except Exception as exc:
            self.status_label.configure(text=f"Error al guardar configuración: {exc}")
            return
        if callable(self.on_change):
            self.on_change()
        self._load_values()
        self.status_label.configure(text="Configuración guardada correctamente.")

    def _restore_defaults(self) -> None:
        current_data = load_settings()
        default_data = get_default_settings_data()
        # Restaurar preferencias de producto sin borrar datos que ya tienen acciones propias.
        default_data["history"]["search_history"] = list(current_data.get("history", {}).get("search_history", []))
        default_data["filters"]["saved_discard_terms"] = list(current_data.get("filters", {}).get("saved_discard_terms", []))
        write_settings_data(default_data)
        self._load_values()
        if callable(self.on_change):
            self.on_change()
        self.status_label.configure(text="Configuración restaurada a los valores por defecto. Historial y descartes guardados se conservaron.")

    def _clear_history(self) -> None:
        clear_search_history()
        self._load_values()
        if callable(self.on_change):
            self.on_change()
        self.status_label.configure(text="Historial de búsquedas borrado.")

    def _clear_saved_terms(self) -> None:
        clear_saved_discard_terms()
        self._load_values()
        if callable(self.on_change):
            self.on_change()
        self.status_label.configure(text="Términos de descarte guardados borrados.")


def show_product_settings_window(
    parent: Any,
    *,
    font_config: Any,
    on_change: Callable[[], None] | None = None,
    color_theme: str | None = None,
    surface_theme: str | None = None,
    appearance_mode: str | None = None,
) -> ProductSettingsWindow:
    return ProductSettingsWindow(
        parent,
        font_config=font_config,
        on_change=on_change,
        color_theme=color_theme,
        surface_theme=surface_theme,
        appearance_mode=appearance_mode,
    )
