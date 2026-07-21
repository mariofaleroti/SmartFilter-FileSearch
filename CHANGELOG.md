# Historial de cambios


## [1.0.31] - 2026-07-21

### Versión estable

- La tarjeta principal `Ocurrencias` vuelve a ser `Caracteres`, mostrando `content_text_chars_count` como volumen de texto procesado.
- **Abrir** entrega directamente la ruta original de DOCX/XLSX a Word o Excel y deja de crear copias temporales.
- **Destacado** conserva el visor HTML temporal como acción independiente.
- Canal de publicación derivado automáticamente como `stable`.


## [1.0.31-rc3]

### Correcciones de estabilización
- Corregido `validate_excel_original_open`: ahora valida los textos y el flujo real vigente de doble clic, Abrir y Destacado.
- `BUILD_PORTABLE_WINDOWS.ps1` se distribuye con UTF-8 BOM para mostrar correctamente los mensajes en Windows PowerShell 5.1.
 - 2026-07-21

### Estabilización

- Canal de versión derivado automáticamente: RC, estable o desarrollo según `APP_VERSION`.
- CLI sin argumentos muestra ayuda y ya no genera snapshots internos.
- Las búsquedas CLI generan únicamente la salida solicitada; los snapshots pasan a `tools.write_development_snapshots`.
- Dependencias alineadas con RenderCore: `Jinja2>=3.1.6` y `openpyxl>=3.1.5`.
- Manifest actualizado para declarar RenderCore.
- Árbol fuente limpiado de releases, runtime, cachés, documentación histórica y validadores obsoletos.
- Se unifica `BUILD_WINDOWS_RELEASE.cmd` como único CMD oficial de construcción.

- Separación formal entre plantillas inmutables de fábrica (`resources/defaults`) y datos modificables del usuario (`data`).
- Release portable generado siempre desde configuración y categorías limpias, nunca desde el estado de desarrollo.
- Estado inicial sin rutas, palabra/frase, categoría seleccionada, historial ni filtros personales.
- Tipo inicial generalizado a `Todos los archivos`, con modo `Carpeta`, alcance `Nombre y contenido` y rendimiento `Automático · Equilibrado`.
- Categorías oficiales reducidas a las 10 predeterminadas; se eliminaron categorías y términos de prueba.
- Defaults de fábrica empaquetados dentro de GUI y CLI para primer inicio y restauración.
- Validadores nuevos para impedir releases con datos personales o defaults desalineados.

## [1.0.31-rc2] - 2026-07-21

### Mejorado

- La ventana **Ayuda** deja de ser un bloque único de texto y pasa a una guía navegable por pestañas.
- Se incorporan áreas específicas para Inicio, Criterios, Categorías, Resultados, Rendimiento y Portable.
- La ayuda integrada cubre alcance, filtros, secciones estructurales, backups de categorías, métricas, visor HTML, perfiles de recursos, privacidad y limitaciones.
- Se aclara dentro de la aplicación que **Abrir** usa el original y **Destacado** genera HTML, también para PDF y XLSX.
- La limitación de OCR y las buenas prácticas quedan visibles sin depender del README del repositorio.
- La guía de usuario corrige numeración y alinea nombres de métricas con la interfaz actual.

### Validado

- Presencia de seis áreas navegables y tarjetas desplazables.
- Cobertura semántica equivalente a la guía de usuario y al README operativo.
- Compilación de la ventana y conservación del release sin README adicional.

## [1.0.31-rc1] - 2026-07-21

### Mejorado

- La ventana **Acerca de** deja atrás el texto técnico de desarrollo y presenta propósito, capacidades, formatos, privacidad, modo portable y limitaciones conocidas.
- La descripción del producto se vuelve estable y orientada al usuario.
- La limitación de OCR queda visible dentro de la aplicación.
- El creador de release usa un único flujo: `BUILD_WINDOWS_RELEASE.cmd` delega en `BUILD_PORTABLE_WINDOWS.ps1`.
- PowerShell se posiciona en la raíz, comprueba códigos de salida, SharedCode, templates, ejecutables, manifest y ZIP versionado.
- Se elimina la actualización automática de pip durante cada build.
- Los validadores de versión dejan de depender de un número fijo.

### Cambiado

- El portable ya no incluye `README_RELEASE.md`, `README.txt` ni otro README duplicado. La información operativa queda centralizada en **Ayuda** y **Acerca de**.
- `tool_manifest.json`, el snapshot y el checklist reflejan la estructura portable real.

### Validado

- Coincidencia dinámica entre `APP_VERSION`, manifest y nombre del ZIP.
- Rechazo de releases con documentación duplicada o elementos de desarrollo.
- Compilación de la ventana Acerca de y presencia de todos los alcances y limitaciones declarados.

## [1.0.30-dev] - 2026-07-20

### Corregido

- `Limitar dónde buscar` deja de interpretar frases casuales como secciones por comenzar con el nombre configurado.
- Los encabezados se reconocen por estructura real: etiqueta/valor, título independiente, Markdown, numeración o formato de encabezado.
- Las secciones de documentos generales terminan ante el siguiente encabezado reconocible, aunque no pertenezca al vocabulario típico de CV.
- XLSX, CSV, DOCX, JSON y XML preservan relaciones `campo: valor` para aplicar el alcance con precisión.
- El modo de compatibilidad para contenido aplanado solo se activa cuando varias etiquetas conocidas demuestran una estructura documental real.

### Validado

- CV con `Experiencia`, `Experiencia laboral` y campos escalares.
- Informes con secciones numeradas, Markdown y encabezados generales.
- Rechazo de frases como `Experiencia administrativa requerida para el puesto`.
- Alcance estructurado en CSV, XLSX, DOCX, JSON y XML.
- Equivalencia del motor local y multiprocessing mediante los validadores existentes.

## [1.0.29-dev] - 2026-07-17

### Corregido

- El portable incluye explícitamente `render_core/templates`, evitando el error `generic_report.html.j2` al generar vistas destacadas.
- El botón **Destacado** vuelve a generar y abrir el visor HTML profesional para PDF, XLSX y el resto de formatos soportados.
- El doble clic deja de crear o abrir libros Excel temporales: usa el mismo visor HTML que **Destacado** o abre el original según la preferencia.
- La preferencia histórica `Abrir copia destacada` migra automáticamente a `Abrir vista destacada HTML`.

### Validado

- Renderizado HTML real de un PDF y un XLSX mediante RenderCore.
- Inclusión obligatoria de templates Jinja en los `.spec` GUI y CLI.
- Autoprueba del ejecutable ampliada con `highlight_html=ok`; el build falla si falta el perfil HTML.
- El botón **Abrir** conserva la apertura exclusiva del archivo original.

## [1.0.28-dev] - 2026-07-17

### Corregido

- Las vistas destacadas XLSX reemplazan caracteres de control incompatibles con XML sin modificar el archivo original.
- Las copias temporales incompletas se eliminan cuando la generación falla.
- El ZIP portable deja de usar el nombre histórico fijo `v1.0.5` y toma la versión actual.

### Agregado

- Autoprueba `SmartFilterCLI.exe --portable-self-check` sobre el ejecutable empaquetado.
- Validación de versión, agrupación por archivo, dependencia `openpyxl` y generación XLSX dentro del portable.
- El build se detiene si el ejecutable no supera la autoprueba.

### Diagnosticado

- El portable `1.0.27-dev` inspeccionado sí contenía el motor actual y SharedCode; el error observado provenía de caracteres inválidos para hojas XLSX, no de módulos ausentes.

Este archivo resume los cambios funcionales principales de Smart Filter. Los documentos técnicos de `docs/` conservan el detalle de cada corte y sus validaciones.

## [1.0.27-dev] - 2026-07-17

### Agregado

- Exportación de una categoría o de toda la base mediante contrato JSON estándar.
- Importación con modos agregar nuevas, combinar/actualizar y reemplazar todas.
- Vista previa de importación con conflictos y categorías que serían retiradas.
- Backups automáticos antes de modificar, eliminar, importar o restaurar categorías.
- Restauración segura de categorías predeterminadas faltantes.
- Selector filtrable y múltiple para categorías de descarte.

### Corregido

- Se impiden autorreferencias y referencias de descarte hacia categorías inexistentes.
- La eliminación solicita confirmación con el nombre exacto de la categoría.

## [1.0.26-dev] - 2026-07-17

### Mejorado

- `Incidencias` conserva una identidad roja tenue incluso cuando su valor es cero.
- Cuando existen incidencias, la tarjeta aumenta claramente la intensidad de fondo, borde y texto.
- Se agregan variantes específicas para tema claro y oscuro, manteniendo contraste y jerarquía visual.

### Validado

- Estado sin incidencias visible sin parecer una alarma activa.
- Estado con incidencias claramente diferenciable.
- El cambio no altera los contadores ni el motor de búsqueda.

## [1.0.25-dev] - 2026-07-17

### Mejorado

- El panel final separa `Archivos encontrados` de `Ocurrencias`.
- `Readers` se reemplaza por `Leídos` y usa lecturas correctas cuando la métrica está disponible.
- La tarjeta técnica `Caracteres` se reemplaza por `Sin coincidencia`.
- Se elimina la tarjeta ambigua `Descartados` del resumen ejecutivo; el contador sigue disponible en el detalle y el JSON.
- `Incidencias` separa visualmente el estado normal del estado con problemas.
- Las tarjetas de candidatos, lecturas y no coincidencias quedan neutrales para reducir ruido visual.

### Validado

- Correspondencia exacta entre cada tarjeta y los contadores de `SearchSummary`.
- Diferencia visible entre archivos únicos y ocurrencias totales.
- Compatibilidad con búsquedas nuevas e importación de resultados.

## [1.0.24-dev] - 2026-07-17

### Corregido

- `Limitar dónde buscar` aplica realmente los términos de categoría solo a los campos o secciones configurados.
- El modo limitado deja de evaluar el nombre del archivo y el contenido ajeno a esos campos para la categoría.
- Las ocurrencias y vistas previas respetan el mismo alcance aplicado por la decisión de coincidencia.
- La ruta normal y multiprocessing comparten exactamente el mismo extractor de alcance.
- Los lectores que entregan contenido aplanado, como XLSX y DOCX, pueden delimitar secciones por marcadores de campo.
- Si no se encuentra un campo configurado, no existe fallback silencioso al documento completo.

### Validado

- Diferencia real entre `Todo el contenido` y `Solo campos o secciones indicadas`.
- Secciones por líneas, campos escalares y contenido aplanado.
- Equivalencia entre análisis local y análisis por procesos.

## [1.0.23-dev] - 2026-07-16

### Corregido

- La telemetría conserva una instancia `psutil.Process` por PID.
- La CPU de los procesos analizadores deja de aparecer permanentemente en cero.
- La CPU total de Smart Filter suma correctamente proceso principal e hijos.
- Se evita la advertencia falsa `cpu_parallel_low_utilization` causada por muestras inválidas.

### Validado

- Medición real de CPU por proceso analizador.
- Búsqueda completa en equipo físico y máquina virtual.
- Equivalencia de resultados y estabilidad del pipeline.

## [1.0.22-dev] - 2026-07-16

### Agregado

- Perfiles `Bajo consumo`, `Equilibrado` y `Alto rendimiento`.
- Modo `Manual técnico` para procesos, lectores, reserva de núcleos y lotes pendientes.
- Monitor de CPU, RAM, procesos, fases y cronología mediante `psutil`.
- Bloque `performance` en exportaciones JSON de la GUI.

### Corregido

- Backpressure estricto: el número de lotes pendientes no puede superar el límite configurado.

## [1.0.21-dev] - 2026-07-16

### Agregado

- Análisis CPU paralelo con procesos persistentes para búsquedas de raíz o rutas amplias.
- Lotes acotados por cantidad de archivos y volumen de texto.
- Fallback local de lotes fallidos.
- Cancelación cooperativa de productor, lectores y procesos.
- Compatibilidad de multiprocessing con Windows y PyInstaller.

## [1.0.20-dev] - 2026-07-16

### Mejorado

- Visor documental profesional basado en RenderCore.
- Cabecera, métricas, navegación, filtro local y sidebar sticky.
- Acciones para abrir original, abrir carpeta y copiar ruta.

## [1.0.19-dev] - 2026-07-16

### Agregado

- Resultados agrupados por archivo cuando una categoría es el único criterio.
- Conservación de todas las ubicaciones y ocurrencias dentro de cada archivo agrupado.
- Destacado HTML para PDF, DOCX, XLSX, CSV y formatos de texto.

## [1.0.18-dev] - 2026-07-16

### Corregido

- El botón `Abrir` abre siempre el original, incluidos archivos XLSX.
- El doble clic conserva el modo de apertura configurable.
- `Destacado` trabaja sobre una copia temporal sin modificar el archivo original.

## [1.0.17-dev] - 2026-07-16

### Corregido

- Apertura portable de archivos mediante PlatformCore.
- Apertura confiable de PDF con la aplicación predeterminada en Windows.

## [1.0.16-dev] - 2026-07-16

### Mejorado

- Separación entre archivos coincidentes y ocurrencias totales.
- Métricas GUI, CLI y JSON sin ambigüedad.

## [1.0.15-dev] - 2026-07-16

### Mejorado

- Integración de escaneo, lectura y coincidencias en un único pipeline.
- Eliminación de la segunda pasada global de análisis.
- Liberación temprana del contenido completo de cada archivo.

## Historial anterior

La evolución previa incluye lectores paralelos, cola acotada, escaneo amplio seguro, errores estructurados, progreso en vivo, importación/exportación, categorías, tooltips, configuración visual y pulidos de interfaz. El detalle se conserva en los documentos técnicos de `docs/` y en el historial Git del proyecto.
