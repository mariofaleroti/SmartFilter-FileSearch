from __future__ import annotations

from typing import Any, Iterable

from gui_core import (
    ActionButton,
    SecondaryWindow,
    SecondaryWindowConfig,
    get_accent_colors,
    get_surface_colors,
    require_customtkinter,
)

from smart_filter.app_info import (
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_NAME,
    APP_RELEASE_LABEL,
    APP_TAGLINE,
    APP_VERSION,
)
from smart_filter.ui.window_icon import apply_window_icon_later

SUPPORTED_FORMATS = ("PDF", "DOCX", "XLSX", "CSV", "TXT", "LOG", "MD", "JSON", "XML", "HTML")

MAIN_CAPABILITIES = (
    "Busca archivos por nombre, contenido o ambos criterios.",
    "Combina palabra o frase, categorías inteligentes, descarte y exclusiones.",
    "Agrupa coincidencias por archivo y conserva sus ubicaciones y ocurrencias.",
    "Abre el original o genera una vista HTML destacada sin modificarlo.",
    "Exporta resultados y permite automatizar búsquedas mediante la CLI.",
)

PORTABLE_AND_PRIVACY = (
    "El análisis se realiza localmente en el equipo.",
    "Smart Filter no envía archivos ni resultados a servicios externos.",
    "La configuración y las categorías se conservan dentro de la carpeta data.",
    "Para trasladarlo a otro equipo debe copiarse la carpeta SmartFilter completa, no solamente el ejecutable.",
)

KNOWN_LIMITATIONS = (
    "Esta versión no incorpora OCR.",
    "Los PDF escaneados sin capa de texto y las imágenes JPG o PNG no pueden analizarse por contenido.",
    "Los archivos protegidos, dañados, bloqueados o con permisos insuficientes pueden registrarse como incidencias.",
    "Las búsquedas sobre discos completos pueden requerir varios minutos según el volumen de archivos y el equipo.",
)


def _visual_tokens(
    *,
    color_theme: str | None,
    surface_theme: str | None,
    appearance_mode: str | None,
) -> dict[str, str]:
    try:
        appearance = str(appearance_mode or "dark").lower()
        surface = dict(get_surface_colors(appearance, surface_theme))
        accent = dict(get_accent_colors(color_theme))
        is_light = appearance == "light"
        return {
            "card": surface.get("card", "#f8fafc" if is_light else "#111827"),
            "neutral": surface.get("neutral", "#eef2f7" if is_light else "#1f2937"),
            "border": surface.get("border", "#cbd5e1" if is_light else "#334155"),
            "text": "#111827" if is_light else "#f8fafc",
            "muted": surface.get("muted_text", "#64748b" if is_light else "#94a3b8"),
            "accent": accent.get("primary", "#1f6aa5"),
            "accent_soft": accent.get("selected", "#dbeafe" if is_light else "#1e3a5f"),
            "success_soft": "#dcfce7" if is_light else "#163826",
            "success_text": "#166534" if is_light else "#86efac",
            "warning_soft": "#fff7ed" if is_light else "#3a2616",
            "warning_text": "#9a3412" if is_light else "#fdba74",
        }
    except Exception:
        return {
            "card": "#111827",
            "neutral": "#1f2937",
            "border": "#334155",
            "text": "#f8fafc",
            "muted": "#94a3b8",
            "accent": "#1f6aa5",
            "accent_soft": "#1e3a5f",
            "success_soft": "#163826",
            "success_text": "#86efac",
            "warning_soft": "#3a2616",
            "warning_text": "#fdba74",
        }


def _bullet_text(items: Iterable[str]) -> str:
    return "\n".join(f"• {item}" for item in items)


def _add_section_card(
    ctk: Any,
    parent: Any,
    *,
    row: int,
    title: str,
    body: str,
    font_config: Any,
    tokens: dict[str, str],
    background: str | None = None,
    title_color: str | None = None,
) -> Any:
    card = ctk.CTkFrame(
        parent,
        fg_color=background or tokens["card"],
        border_width=1,
        border_color=tokens["border"],
        corner_radius=10,
    )
    card.grid(row=row, column=0, sticky="ew", padx=2, pady=(0, 10))
    card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        card,
        text=title,
        font=font_config.tuple("section"),
        text_color=title_color or tokens["text"],
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 5))

    ctk.CTkLabel(
        card,
        text=body,
        font=font_config.tuple("body"),
        text_color=tokens["text"],
        justify="left",
        anchor="w",
        wraplength=790,
    ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
    return card


def show_about_window(
    parent: Any,
    *,
    font_config: Any,
    color_theme: str | None = None,
    surface_theme: str | None = None,
    appearance_mode: str | None = None,
) -> SecondaryWindow:
    ctk = require_customtkinter()
    tokens = _visual_tokens(
        color_theme=color_theme,
        surface_theme=surface_theme,
        appearance_mode=appearance_mode,
    )
    window = SecondaryWindow(
        parent,
        SecondaryWindowConfig(
            title="Acerca de Smart Filter",
            subtitle="Información del producto, alcance actual y modo de funcionamiento.",
            width=900,
            height=720,
            min_width=760,
            min_height=580,
            modal=False,
        ),
        font_config=font_config,
    )
    window.apply_visual_preferences(font_config, color_theme, surface_theme, appearance_mode)
    apply_window_icon_later(window)
    apply_window_icon_later(window.content_frame)

    frame = window.content_frame
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)

    scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
    scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    scroll.grid_columnconfigure(0, weight=1)

    hero = ctk.CTkFrame(
        scroll,
        fg_color=tokens["card"],
        border_width=1,
        border_color=tokens["accent"],
        corner_radius=12,
    )
    hero.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 12))
    hero.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        hero,
        text=APP_DISPLAY_NAME,
        font=font_config.tuple("title"),
        text_color=tokens["text"],
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))

    ctk.CTkLabel(
        hero,
        text=APP_TAGLINE,
        font=font_config.tuple("section"),
        text_color=tokens["accent"],
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))

    identity = ctk.CTkFrame(hero, fg_color="transparent")
    identity.grid(row=0, column=1, rowspan=2, sticky="ne", padx=18, pady=16)
    version_badge = ctk.CTkFrame(identity, fg_color=tokens["accent_soft"], corner_radius=8)
    version_badge.grid(row=0, column=0, sticky="e")
    ctk.CTkLabel(
        version_badge,
        text=f"Versión {APP_VERSION}",
        font=font_config.tuple("small"),
        text_color=tokens["text"],
    ).grid(row=0, column=0, padx=10, pady=5)
    ctk.CTkLabel(
        identity,
        text=APP_RELEASE_LABEL,
        font=font_config.tuple("small"),
        text_color=tokens["muted"],
        anchor="e",
    ).grid(row=1, column=0, sticky="e", pady=(5, 0))

    ctk.CTkLabel(
        hero,
        text=APP_DESCRIPTION,
        font=font_config.tuple("body"),
        text_color=tokens["text"],
        justify="left",
        anchor="w",
        wraplength=790,
    ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 17))

    _add_section_card(
        ctk,
        scroll,
        row=1,
        title="Qué permite hacer",
        body=_bullet_text(MAIN_CAPABILITIES),
        font_config=font_config,
        tokens=tokens,
    )

    formats_card = _add_section_card(
        ctk,
        scroll,
        row=2,
        title="Formatos compatibles",
        body="Smart Filter analiza contenido textual accesible en los siguientes formatos:",
        font_config=font_config,
        tokens=tokens,
    )
    formats_frame = ctk.CTkFrame(formats_card, fg_color="transparent")
    formats_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
    for column in range(5):
        formats_frame.grid_columnconfigure(column, weight=1)
    for index, file_format in enumerate(SUPPORTED_FORMATS):
        chip = ctk.CTkFrame(formats_frame, fg_color=tokens["neutral"], corner_radius=7)
        chip.grid(row=index // 5, column=index % 5, sticky="ew", padx=3, pady=3)
        chip.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            chip,
            text=file_format,
            font=font_config.tuple("small"),
            text_color=tokens["text"],
        ).grid(row=0, column=0, sticky="ew", padx=9, pady=5)

    _add_section_card(
        ctk,
        scroll,
        row=3,
        title="Modo portable y privacidad",
        body=_bullet_text(PORTABLE_AND_PRIVACY),
        font_config=font_config,
        tokens=tokens,
        background=tokens["success_soft"],
        title_color=tokens["success_text"],
    )

    _add_section_card(
        ctk,
        scroll,
        row=4,
        title="Alcance y limitaciones conocidas",
        body=_bullet_text(KNOWN_LIMITATIONS),
        font_config=font_config,
        tokens=tokens,
        background=tokens["warning_soft"],
        title_color=tokens["warning_text"],
    )

    _add_section_card(
        ctk,
        scroll,
        row=5,
        title="Identidad técnica",
        body=(
            f"Nombre técnico: {APP_NAME}\n"
            "Smart Filter consume infraestructura reutilizable desde SharedCode y conserva como lógica propia "
            "las categorías, filtros, readers, coincidencias, resultados y acciones del producto. "
            "La Ayuda de la aplicación contiene la guía operativa detallada."
        ),
        font_config=font_config,
        tokens=tokens,
    )

    close_button = ActionButton(
        window.footer_frame,
        "Cerrar",
        command=window.close,
        style="primary",
        font_config=font_config,
    )
    close_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
    return window
