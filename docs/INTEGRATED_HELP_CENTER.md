# Ayuda integrada de Smart Filter

Smart Filter reemplaza la ayuda rápida de texto por una guía operativa navegable dentro de la aplicación.

## Objetivo

La ventana **Ayuda** es la referencia principal del usuario final. Debe permitir comprender el producto sin abrir el README del repositorio ni documentación de desarrollo.

## Estructura

La guía se divide en seis áreas:

- **Inicio:** propósito, flujo principal, origen y formatos compatibles.
- **Criterios:** palabra/frase, categorías, combinación, alcance, filtros y escaneo amplio seguro.
- **Categorías:** alcance estructural, importación, exportación, backups, restauración y descarte cruzado.
- **Resultados:** métricas, agrupación, acciones, visor HTML, importación, exportación e incidencias.
- **Rendimiento:** perfiles, configuración recomendada, pipeline, cancelación y telemetría.
- **Portable:** privacidad local, traslado correcto, CLI, OCR, limitaciones y buenas prácticas.

## Reglas de presentación

- No usar un único bloque largo de texto.
- Cada área debe ser desplazable de forma independiente.
- Las explicaciones se presentan en tarjetas breves con títulos claros.
- Las advertencias de OCR e incidencias deben distinguirse visualmente.
- **Abrir** y **Destacado** deben describirse como acciones diferentes.
- La ayuda debe adaptarse a tema claro, oscuro y a las preferencias visuales de GuiCore.

## Alcance del release

El portable continúa sin README adicional. La información del usuario final se mantiene dentro de **Ayuda** y **Acerca de**; el README del repositorio sigue orientado a desarrollo, arquitectura y mantenimiento.
