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

from smart_filter.app_info import APP_DISPLAY_NAME, APP_VERSION
from smart_filter.ui.window_icon import apply_window_icon_later

SUPPORTED_FORMATS = ("PDF", "DOCX", "XLSX", "CSV", "TXT", "LOG", "MD", "JSON", "XML", "HTML")
HELP_TABS = ("Inicio", "Criterios", "Categorías", "Resultados", "Rendimiento", "Portable")


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
            "danger_soft": "#fef2f2" if is_light else "#3a171b",
            "danger_text": "#991b1b" if is_light else "#fca5a5",
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
            "danger_soft": "#3a171b",
            "danger_text": "#fca5a5",
        }


def _bullets(items: Iterable[str]) -> str:
    return "\n".join(f"• {item}" for item in items)


def _steps(items: Iterable[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _add_card(
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
    footer: str | None = None,
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
        wraplength=900,
    ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12 if footer else 14))

    if footer:
        ctk.CTkLabel(
            card,
            text=footer,
            font=font_config.tuple("small"),
            text_color=tokens["muted"],
            justify="left",
            anchor="w",
            wraplength=900,
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 13))
    return card


def _add_formats_card(
    ctk: Any,
    parent: Any,
    *,
    row: int,
    font_config: Any,
    tokens: dict[str, str],
) -> None:
    card = _add_card(
        ctk,
        parent,
        row=row,
        title="Formatos compatibles",
        body="Smart Filter analiza contenido textual accesible en estos formatos:",
        font_config=font_config,
        tokens=tokens,
    )
    chips = ctk.CTkFrame(card, fg_color="transparent")
    chips.grid(row=2, column=0, sticky="ew", padx=13, pady=(0, 4))
    for column in range(5):
        chips.grid_columnconfigure(column, weight=1)
    for index, file_format in enumerate(SUPPORTED_FORMATS):
        chip = ctk.CTkFrame(chips, fg_color=tokens["neutral"], corner_radius=7)
        chip.grid(row=index // 5, column=index % 5, sticky="ew", padx=3, pady=3)
        chip.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            chip,
            text=file_format,
            font=font_config.tuple("small"),
            text_color=tokens["text"],
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=5)

    ctk.CTkLabel(
        card,
        text="Todos los archivos significa todos los formatos compatibles, no cualquier extensión del sistema.",
        font=font_config.tuple("small"),
        text_color=tokens["muted"],
        justify="left",
        anchor="w",
        wraplength=900,
    ).grid(row=3, column=0, sticky="ew", padx=16, pady=(5, 13))


def _create_tab_scroll(ctk: Any, tab: Any) -> Any:
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(0, weight=1)
    scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
    scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=8)
    scroll.grid_columnconfigure(0, weight=1)
    return scroll


def _build_start_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title=f"{APP_DISPLAY_NAME} · Versión {APP_VERSION}",
        body=(
            "Smart Filter localiza archivos por nombre y contenido sin modificar los originales. "
            "Puede trabajar con una palabra o frase, una categoría inteligente o la combinación de ambas."
        ),
        font_config=font_config,
        tokens=tokens,
        background=tokens["accent_soft"],
        title_color=tokens["accent"],
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Inicio rápido",
        body=_steps(
            (
                "Elegir Carpeta o Archivo individual.",
                "Seleccionar la ruta que se analizará.",
                "Escribir una palabra/frase, elegir una categoría o combinar ambas.",
                "Definir alcance, tipos de archivo y filtros opcionales.",
                "Ejecutar Buscar; durante la tarea el botón permite Cancelar.",
                "Revisar resultados y usar Abrir, Carpeta, Destacado o Exportar.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Elegir el origen",
        body=_bullets(
            (
                "Carpeta: recorre la ruta elegida y sus subcarpetas respetando exclusiones y reglas de escaneo.",
                "Archivo individual: analiza un documento concreto; es ideal para validar criterios o categorías.",
                "Una raíz como C:\\ o / puede tardar varios minutos y requiere más recursos que una carpeta específica.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_formats_card(ctk, parent, row=3, font_config=font_config, tokens=tokens)


def _build_criteria_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title="Tres formas de buscar",
        body=_bullets(
            (
                "Palabra/frase: busca el texto indicado después de normalizar mayúsculas, acentos y formato.",
                "Categoría: busca cualquiera de los términos incluidos en la categoría elegida.",
                "Palabra/frase + categoría: exige que el archivo cumpla ambos criterios.",
            )
        ),
        footer="Con categoría como único criterio, Smart Filter agrupa las coincidencias por archivo y conserva todas sus ubicaciones.",
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Alcance de búsqueda",
        body=_bullets(
            (
                "Nombre y contenido: revisa ambos lugares.",
                "Solo nombre: no abre el contenido y suele ser la opción más rápida.",
                "Solo contenido: ignora coincidencias exclusivas del nombre del archivo.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Filtros opcionales",
        body=_bullets(
            (
                "Contexto: agrega una segunda condición para reducir resultados demasiado amplios.",
                "Descarte: excluye archivos relacionados con otra categoría configurada.",
                "Exclusión temporal: descarta palabras o frases solo durante la búsqueda actual.",
                "Exclusiones persistentes: omiten nombres flexibles o rutas exactas desde Configuración.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=3,
        title="Escaneo amplio seguro",
        body=(
            "Al buscar desde una unidad o raíz, Smart Filter puede omitir automáticamente carpetas de sistema, "
            "temporales, cachés, dependencias de desarrollo y salidas de compilación. La finalidad es reducir ruido, "
            "errores de permisos y trabajo sin valor, no ocultar resultados dentro de una carpeta normal."
        ),
        footer="Para búsquedas precisas, comenzar por una carpeta concreta y habilitar solo los formatos necesarios.",
        font_config=font_config,
        tokens=tokens,
        background=tokens["success_soft"],
        title_color=tokens["success_text"],
    )


def _build_categories_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title="Qué representa una categoría",
        body=(
            "Una categoría reúne términos de inclusión, términos de descarte y reglas de alcance. "
            "Permite expresar una idea completa —por ejemplo, Administración o Soporte técnico— sin escribir "
            "manualmente todas sus variantes en cada búsqueda."
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Limitar dónde buscar",
        body=_bullets(
            (
                "Restringe los términos de la categoría a campos, columnas, claves o secciones reales.",
                "Campo: valor analiza únicamente el valor asociado.",
                "Un encabezado independiente abre un bloque hasta el siguiente encabezado reconocible.",
                "XLSX/CSV usan encabezados de columna; JSON/XML usan claves o etiquetas.",
                "Una palabra casual dentro de una oración no se interpreta como sección.",
                "Si el campo configurado no existe, la categoría no vuelve silenciosamente a todo el documento.",
            )
        ),
        footer=(
            "Ejemplo válido: EXPERIENCIA seguido por un bloque de texto. Ejemplo no válido: "
            "“Se requiere experiencia administrativa”."
        ),
        font_config=font_config,
        tokens=tokens,
        background=tokens["accent_soft"],
        title_color=tokens["accent"],
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Administración segura",
        body=_bullets(
            (
                "Exportar permite guardar una categoría o toda la base en un JSON portable.",
                "Importar ofrece agregar solo nuevas, combinar y actualizar, o reemplazar toda la base.",
                "Restaurar predeterminadas agrega únicamente las categorías faltantes y no pisa las existentes.",
                "Modificar, eliminar, importar o restaurar crea un backup automático antes del cambio.",
                "Los backups se guardan en data/backups/categories y se conservan las 30 copias más recientes.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=3,
        title="Categorías de descarte",
        body=(
            "En la pestaña Descartar se seleccionan desde una lista filtrable. La categoría actual no puede "
            "apuntarse a sí misma y las referencias inexistentes se eliminan al guardar. Los términos manuales "
            "de descarte y las categorías completas continúan siendo conceptos separados."
        ),
        font_config=font_config,
        tokens=tokens,
    )


def _build_results_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title="Cómo leer las métricas",
        body=_bullets(
            (
                "Candidatos: archivos compatibles aceptados por el escaneo.",
                "Leídos: archivos cuyo contenido se procesó correctamente.",
                "Archivos encontrados: archivos únicos que cumplieron los criterios.",
                "Caracteres: volumen total de texto procesado durante la búsqueda.",
                "Sin coincidencia: candidatos analizados que no cumplieron la búsqueda.",
                "Incidencias: advertencias y errores; rojo tenue en cero y rojo intenso cuando requieren atención.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Acciones sobre un resultado",
        body=_bullets(
            (
                "Abrir: abre siempre la ruta real del archivo original con la aplicación asociada, sin crear una copia temporal.",
                "Carpeta: abre la ubicación contenedora.",
                "Destacado: genera una vista HTML temporal con RenderCore y no modifica el original.",
                "Doble clic: abre el visor HTML destacado o el original según la opción configurada.",
                "Copiar: permite copiar rutas, resultados o archivos según la acción elegida.",
            )
        ),
        footer="Destacado usa el visor HTML, incluso para PDF y XLSX; Excel o el lector PDF se reservan para Abrir.",
        font_config=font_config,
        tokens=tokens,
        background=tokens["success_soft"],
        title_color=tokens["success_text"],
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Importar y exportar resultados",
        body=_bullets(
            (
                "Importar carga JSON o CSV previamente exportados para volver a examinarlos.",
                "Exportar selección guarda únicamente las filas elegidas.",
                "Exportar todo conserva el conjunto completo de resultados.",
                "El JSON incluye contrato estándar, diagnósticos, incidencias y telemetría cuando está habilitada.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=3,
        title="Advertencias controladas",
        body=(
            "Una búsqueda puede finalizar con advertencias por permisos, archivos bloqueados o documentos dañados "
            "y conservar todos los resultados válidos. La tarjeta Incidencias resume el estado; el JSON exportado "
            "contiene el detalle técnico completo."
        ),
        font_config=font_config,
        tokens=tokens,
        background=tokens["warning_soft"],
        title_color=tokens["warning_text"],
    )


def _build_performance_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title="Configuración recomendada",
        body=_bullets(
            (
                "Modo: Automático.",
                "Perfil: Equilibrado.",
                "Monitor de CPU y memoria: activado cuando se requiere diagnóstico.",
                "Cronología reducida: activada para conservar una muestra periódica sin inflar el JSON.",
            )
        ),
        footer="Equilibrado es el punto de partida recomendado para uso cotidiano.",
        font_config=font_config,
        tokens=tokens,
        background=tokens["accent_soft"],
        title_color=tokens["accent"],
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Perfiles de recursos",
        body=_bullets(
            (
                "Bajo consumo: prioriza que el equipo permanezca disponible durante búsquedas largas.",
                "Equilibrado: combina velocidad y margen para el sistema.",
                "Alto rendimiento: prioriza terminar antes y puede usar más CPU y RAM.",
                "Manual técnico: permite ajustar procesos, lectores, núcleos reservados y lotes pendientes.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Cómo trabaja el motor",
        body=(
            "El escáner descubre candidatos mientras los lectores procesan archivos en paralelo. En búsquedas amplias, "
            "el análisis puede distribuirse entre procesos; en carpetas normales puede utilizar hilos. El backpressure "
            "limita el trabajo pendiente para evitar un crecimiento descontrolado de memoria."
        ),
        font_config=font_config,
        tokens=tokens,
    )
    _add_card(
        ctk,
        parent,
        row=3,
        title="Cancelar y diagnosticar",
        body=_bullets(
            (
                "Cancelar detiene escaneo, lectores y análisis pendiente de forma cooperativa.",
                "La telemetría registra CPU y RAM del proceso principal y de los analizadores hijos.",
                "Un pico temporal de memoria no implica una fuga; conviene revisar la evolución completa.",
                "Para comparar perfiles, usar la misma ruta, criterios, tipos y exclusiones.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )


def _build_portable_tab(ctk: Any, parent: Any, font_config: Any, tokens: dict[str, str]) -> None:
    _add_card(
        ctk,
        parent,
        row=0,
        title="Modo portable y privacidad",
        body=_bullets(
            (
                "Todo el análisis se realiza localmente en el equipo.",
                "Smart Filter no envía archivos ni resultados a servicios externos.",
                "La configuración y las categorías se conservan dentro de la carpeta data.",
                "Para trasladarlo, copiar la carpeta SmartFilter completa y no solamente SmartFilter.exe.",
                "SmartFilterCLI.exe permite ejecutar búsquedas automatizadas desde consola.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
        background=tokens["success_soft"],
        title_color=tokens["success_text"],
    )
    _add_card(
        ctk,
        parent,
        row=1,
        title="Limitación principal: OCR",
        body=_bullets(
            (
                "Esta versión no incorpora OCR.",
                "Los PDF con texto real se analizan normalmente.",
                "Los PDF escaneados sin capa de texto no producen coincidencias por contenido.",
                "Las imágenes JPG y PNG no se procesan por contenido.",
            )
        ),
        footer="Un PDF puede abrirse correctamente y aun así no contener texto extraíble.",
        font_config=font_config,
        tokens=tokens,
        background=tokens["danger_soft"],
        title_color=tokens["danger_text"],
    )
    _add_card(
        ctk,
        parent,
        row=2,
        title="Otras limitaciones conocidas",
        body=_bullets(
            (
                "Archivos protegidos, dañados, bloqueados o sin permisos pueden registrarse como incidencias.",
                "La calidad del resultado depende del texto realmente accesible para cada reader.",
                "Las búsquedas sobre discos completos pueden requerir varios minutos.",
                "Todos los archivos no incluye extensiones que Smart Filter no sabe interpretar.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
        background=tokens["warning_soft"],
        title_color=tokens["warning_text"],
    )
    _add_card(
        ctk,
        parent,
        row=3,
        title="Buenas prácticas",
        body=_bullets(
            (
                "Comenzar por una carpeta concreta antes de buscar en una unidad completa.",
                "Restringir tipos cuando se conoce el formato objetivo.",
                "Probar primero el criterio principal y luego agregar contexto o descarte.",
                "Exportar categorías después de ajustes importantes.",
                "Revisar el JSON cuando una búsqueda finaliza con incidencias.",
                "Conservar Equilibrado como perfil predeterminado salvo una necesidad concreta.",
            )
        ),
        font_config=font_config,
        tokens=tokens,
    )


def show_help_window(
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
            title="Ayuda de Smart Filter",
            subtitle="Guía completa de búsqueda, categorías, resultados, rendimiento y modo portable.",
            width=1040,
            height=760,
            min_width=860,
            min_height=620,
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

    tabs = ctk.CTkTabview(
        frame,
        fg_color=tokens["card"],
        segmented_button_fg_color=tokens["neutral"],
        segmented_button_selected_color=tokens["accent"],
        segmented_button_selected_hover_color=tokens["accent"],
        border_width=1,
        border_color=tokens["border"],
        corner_radius=10,
    )
    tabs.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    tab_frames: dict[str, Any] = {}
    for tab_name in HELP_TABS:
        tab_frames[tab_name] = _create_tab_scroll(ctk, tabs.add(tab_name))

    _build_start_tab(ctk, tab_frames["Inicio"], font_config, tokens)
    _build_criteria_tab(ctk, tab_frames["Criterios"], font_config, tokens)
    _build_categories_tab(ctk, tab_frames["Categorías"], font_config, tokens)
    _build_results_tab(ctk, tab_frames["Resultados"], font_config, tokens)
    _build_performance_tab(ctk, tab_frames["Rendimiento"], font_config, tokens)
    _build_portable_tab(ctk, tab_frames["Portable"], font_config, tokens)

    close_button = ActionButton(
        window.footer_frame,
        "Cerrar",
        command=window.close,
        style="primary",
        font_config=font_config,
    )
    close_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
    return window
