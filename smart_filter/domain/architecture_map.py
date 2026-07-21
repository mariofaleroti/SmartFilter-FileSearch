from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SharedCodeFeed:
    area: str
    smartfilter_part: str
    sharedcode_core: str
    responsibility: str
    smartfilter_keeps: str
    status: str = "Diseño aprobado"

    def to_row(self, index: int) -> dict[str, Any]:
        return {
            "index": index,
            "area": self.area,
            "smartfilter_part": self.smartfilter_part,
            "sharedcode_core": self.sharedcode_core,
            "responsibility": self.responsibility,
            "smartfilter_keeps": self.smartfilter_keeps,
            "status": self.status,
        }


SHAREDCODE_FEEDS: tuple[SharedCodeFeed, ...] = (
    SharedCodeFeed(
        area="GUI",
        smartfilter_part="Ventana principal, sidebar, cards, tabla, progreso, diálogos",
        sharedcode_core="GuiCore",
        responsibility="Estructura visual reusable, controles comunes, preferencias visuales y tabla base.",
        smartfilter_keeps="Flujo de búsqueda, textos propios, acciones de resultados, categorías y experiencia de producto.",
        status="Paso 1 finalizado",
    ),
    SharedCodeFeed(
        area="Fechas",
        smartfilter_part="Timestamps, nombres de ejecución, updated_at, duración",
        sharedcode_core="DateTimeCore",
        responsibility="UTC/local, formato ISO, run timestamps y pares de fecha consistentes.",
        smartfilter_keeps="Decidir qué fecha mostrar y en qué contexto del producto.",
        status="Paso 2 finalizado",
    ),
    SharedCodeFeed(
        area="Configuración",
        smartfilter_part="settings.json, preferencias visuales, opciones de experiencia",
        sharedcode_core="ConfigCore + JsonContractCore + DateTimeCore",
        responsibility="Lectura/escritura JSON robusta, contrato estándar, validación de envelope y timestamps UTC/local.",
        smartfilter_keeps="Validación semántica de opciones propias: modos, filtros, historial y comportamiento.",
        status="Paso 2 finalizado",
    ),
    SharedCodeFeed(
        area="Categorías",
        smartfilter_part="Base de categorías inteligentes",
        sharedcode_core="ConfigCore + JsonContractCore + DateTimeCore",
        responsibility="Persistencia estándar, contrato JSON, validación de envelope y fechas de actualización.",
        smartfilter_keeps="Matching semántico, términos, exclusiones, descarte y administración de categorías.",
        status="Paso 2 finalizado",
    ),
    SharedCodeFeed(
        area="Escaneo",
        smartfilter_part="Recorrido seguro de carpetas antes de leer archivos",
        sharedcode_core="FileScanCore",
        responsibility="Caminar carpetas de forma segura, evitar rutas técnicas, symlinks/reparse points y errores de acceso.",
        smartfilter_keeps="Extensiones soportadas, exclusiones guardadas, filtros de descarte, lectores y coincidencias.",
        status="Paso 5 finalizado",
    ),
    SharedCodeFeed(
        area="CLI / runtime",
        smartfilter_part="Ejecuciones externas para Toolkit y reportes JSON",
        sharedcode_core="ToolRuntimeCore + LoggingCore",
        responsibility="run_id, carpetas output/log/temp, errores comunes y logs estructurados.",
        smartfilter_keeps="Argumentos propios de búsqueda, resultados y reglas del motor.",
        status="Próximo bloque",
    ),
    SharedCodeFeed(
        area="JSON ecosistema",
        smartfilter_part="Resultados, diagnósticos, errores, report_brief",
        sharedcode_core="JsonContractCore",
        responsibility="Envelope estándar meta/summary/report_brief/data/diagnostics/errors.",
        smartfilter_keeps="Contenido real de resultados y resumen funcional del análisis.",
    ),
    SharedCodeFeed(
        area="Release",
        smartfilter_part="release/SmartFilter limpio",
        sharedcode_core="ReleaseCore",
        responsibility="Copiado limpio, exclusiones de desarrollo y preparación de paquete.",
        smartfilter_keeps="Manifest, entrypoints propios, assets y decisiones de distribución.",
        status="Final de migración",
    ),
)


SMARTFILTER_OWNERSHIP: tuple[str, ...] = (
    "Categorías inteligentes y su lógica de coincidencia.",
    "Filtros de descarte, exclusiones puntuales y exclusiones guardadas.",
    "Lectores específicos y normalización orientada a búsqueda.",
    "Motor de búsqueda, scoring/coincidencias y experiencia de resultados.",
    "Acciones sobre tabla: abrir original, abrir copia destacada, tooltips y exportación.",
    "Ventanas propias de Categorías, Configuración, Ayuda y Acerca de.",
)


def get_sharedcode_feed_rows() -> list[dict[str, Any]]:
    return [item.to_row(index) for index, item in enumerate(SHAREDCODE_FEEDS, start=1)]
