# Guía de usuario de Smart Filter

## 1. Objetivo

Smart Filter localiza archivos por nombre y contenido sin modificar los originales. Permite usar criterios simples, categorías inteligentes, filtros opcionales y una vista destacada temporal para revisar coincidencias.

## 2. Elegir el origen

### Carpeta

Recorre la carpeta seleccionada y sus subcarpetas respetando las exclusiones configuradas.

### Archivo individual

Analiza únicamente el archivo seleccionado. Es útil para validar términos o revisar un documento concreto.

## 3. Definir el criterio

Smart Filter acepta tres formas principales:

- **Palabra/frase:** busca exactamente el texto indicado después de normalizar mayúsculas, acentos y formato.
- **Categoría:** busca los términos asociados a esa categoría.
- **Palabra/frase + categoría:** exige la combinación de ambos criterios según la lógica del motor.

Cuando la categoría es el único criterio, los resultados se agrupan por archivo. Cada fila conserva internamente todas las ubicaciones y la cantidad real de ocurrencias.

### Limitar dónde buscar

Desde **Categorías > Incluir y alcance** se puede activar `Limitar dónde buscar` y escribir campos o secciones como `Experiencia`, `Puesto` o `Habilidades`. En ese modo:

- los términos de la categoría se evalúan únicamente dentro de esos campos o secciones;
- las coincidencias del nombre del archivo no rescatan la categoría;
- las secciones ajenas no cuentan;
- si el documento no contiene el campo configurado, la categoría no coincide;
- la palabra/frase principal, el contexto y los descartes conservan sus propias reglas.

Los nombres se comparan sin distinguir mayúsculas ni acentos. También se reconocen variantes controladas, como `Experiencia laboral` cuando el campo configurado es `Experiencia`.

Smart Filter exige una estructura reconocible:

- `Experiencia: Administración de servidores` se interpreta como campo y valor asociado.
- Un encabezado independiente como `EXPERIENCIA`, `## Experiencia` o `1. Experiencia` abre un bloque hasta el siguiente encabezado real.
- Una frase como `Experiencia administrativa requerida para el puesto` no abre una sección.
- En XLSX/CSV se usan encabezados de columna; en JSON/XML, claves o etiquetas; en DOCX/PDF/TXT, encabezados y bloques de texto.

Si no puede demostrar que el campo o la sección existe, la categoría no coincide en ese archivo.

## 4. Alcance

- **Nombre y contenido:** revisa ambos lugares.
- **Solo nombre:** no abre el contenido de los documentos.
- **Solo contenido:** ignora coincidencias exclusivas del nombre.

Buscar solo por nombre suele ser más rápido. Buscar contenido requiere abrir y procesar cada formato compatible.

## 5. Filtros opcionales

### Filtro de contexto

Agrega una segunda condición para reducir resultados. Conviene usarlo únicamente cuando el criterio principal produce demasiadas coincidencias.

### Filtro de descarte

Excluye resultados relacionados con otra categoría configurada.

### Exclusión temporal

Descarta términos puntuales solo durante la búsqueda actual.

### Exclusiones persistentes

En Configuración se pueden mantener nombres flexibles y rutas exactas de carpetas o archivos que no deben analizarse.

## 6. Tipos de archivo compatibles

Smart Filter puede leer:

```text
.xlsx  .pdf  .docx  .csv  .txt  .log
.md    .json .xml   .html .htm
```

La opción `Todos los archivos` significa todos los formatos compatibles, no cualquier extensión existente en el sistema.

## 7. Ejecutar y cancelar

Durante una búsqueda:

- la interfaz mantiene bloqueadas las acciones incompatibles;
- el botón Buscar cambia a Cancelar;
- el progreso muestra actividad y métricas disponibles;
- la cancelación detiene productor, lectores y análisis pendiente de forma cooperativa.

Una búsqueda de raíz como `C:\` o `/` puede tardar varios minutos y generar advertencias controladas por permisos o documentos dañados.

## 8. Administrar, respaldar y transportar categorías

La ventana **Categorías** ofrece:

- **Exportar** la categoría seleccionada o toda la base a un contrato JSON estándar.
- **Importar** en modo agregar solo nuevas, combinar y actualizar, o reemplazar todas.
- **Restaurar predeterminadas** para recuperar únicamente las categorías faltantes.
- Backups automáticos antes de guardar cambios sobre una categoría existente, eliminar, importar o restaurar.
- Selector filtrable de categorías de descarte, sin escritura manual ni autorreferencias.

Los backups se guardan en `data/backups/categories/` y también pueden importarse desde la misma ventana.

## 9. Interpretar resultados

Las métricas principales distinguen:

- **Archivos encontrados:** archivos únicos con al menos una coincidencia.
- **Caracteres:** volumen total de texto procesado durante la búsqueda.
- **Candidatos:** archivos compatibles considerados por el motor.
- **Leídos:** archivos cuyo contenido se procesó correctamente.
- **Sin coincidencia:** candidatos analizados que no cumplieron los criterios.
- **Incidencias:** advertencias y errores registrados durante el escaneo o la lectura.

Una búsqueda puede finalizar con advertencias y aun así ser correcta. Los accesos denegados y errores de lectura controlados quedan detallados en el JSON.

## 10. Acciones disponibles

### Abrir

Abre siempre la ruta real del archivo original con la aplicación predeterminada del sistema. Para DOCX y XLSX no crea copias temporales.

### Doble clic

Abre la vista HTML destacada o el archivo original, según la opción elegida en Configuración.

### Carpeta

Abre la ubicación contenedora del archivo.

### Destacado

Genera una vista HTML temporal en el navegador. Resalta términos, muestra ubicaciones y permite navegar entre coincidencias. El original no se modifica; PDF y XLSX también usan este visor.

### Importar

Carga resultados previamente exportados en JSON o CSV para volver a examinarlos dentro de Smart Filter.

### Exportar selección / Exportar todo

Guarda resultados en formatos compatibles. La exportación JSON incluye el contrato estándar, diagnósticos y métricas de rendimiento cuando están habilitadas.

## 11. Rendimiento

La configuración recomendada para uso normal es:

```text
Configuración: Automático
Perfil: Equilibrado
Monitor: Activado
Cronología: Activada
```

`Bajo consumo` mantiene mayor disponibilidad del equipo. `Alto rendimiento` termina antes en equipos con margen suficiente. `Manual técnico` está destinado a pruebas controladas y usuarios que comprendan el efecto de procesos, lectores, memoria y backpressure.

La explicación completa está en `docs/RESOURCE_POLICY_AND_PERFORMANCE_MONITOR.md`.

## 12. Modo portable, privacidad y limitaciones

- El análisis se realiza localmente y Smart Filter no envía archivos ni resultados a servicios externos.
- Para trasladar el portable se debe copiar la carpeta `SmartFilter` completa, no solamente el ejecutable.
- La configuración y las categorías se conservan dentro de `data/`.
- La versión actual no incorpora OCR. Los PDF escaneados sin capa de texto y las imágenes JPG/PNG no pueden analizarse por contenido.
- Los archivos protegidos, dañados, bloqueados o sin permisos pueden registrarse como incidencias.

## 13. Buenas prácticas

- Comenzar por una carpeta concreta antes de buscar en una unidad completa.
- Restringir tipos de archivo cuando se conoce el formato objetivo.
- Usar el filtro de contexto después de comprobar el criterio principal.
- Mantener Equilibrado como perfil predeterminado.
- Revisar el JSON cuando una búsqueda completa termina con advertencias.
- No interpretar un pico temporal de RAM como fuga sin observar la evolución completa.
