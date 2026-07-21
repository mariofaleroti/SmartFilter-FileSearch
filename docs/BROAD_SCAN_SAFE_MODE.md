# Escaneo amplio seguro

## Objetivo

Smart Filter activa este perfil únicamente cuando el origen es una raíz de disco o volumen, por ejemplo `C:\`, `D:\` o `/`.

La GUI permite activar o desactivar siete grupos:

- Sistema operativo.
- Temporales y cachés.
- Dependencias de desarrollo.
- Salidas de compilación.
- Resultados generados por Smart Filter.
- Aplicaciones instaladas.
- Datos compartidos del sistema.

Cada switch tiene un tooltip que enumera las carpetas incluidas. Los resultados anteriores se excluyen por defecto para evitar duplicados. Aplicaciones instaladas y datos compartidos permanecen desactivados por defecto por el riesgo de falsos negativos.

`bin` no se excluye globalmente: en instalaciones como JDK, .NET o Android contiene herramientas legítimas y no siempre representa una salida de compilación.

## Arquitectura

- FileScanCore implementa una política neutral y reutilizable de exclusión.
- Smart Filter define nombres, patrones, grupos, valores por defecto y textos.
- La exclusión se aplica antes de agregar la carpeta al recorrido.
- Una carpeta excluida no se abre ni entrega sus subcarpetas al escáner.
- Las exclusiones manuales por ruta exacta usan el mismo mecanismo de poda.

## Métricas JSON

`scan_stats` agrega:

- `broad_scan_root_detected`
- `broad_scan_safe_enabled`
- `automatic_exclusion_groups`
- `automatic_excluded_directories_count`
- `automatic_excluded_directories_by_group`
- `manual_excluded_directories_count`
- `exclusion_samples`
- `skipped_directories_breakdown`
- `link_or_reparse_skipped_directories_count`
- `unclassified_skipped_directories_count`

Las métricas de readers separan:

- lecturas correctas;
- errores controlados del lector;
- fallos inesperados del trabajador;
- archivos omitidos por tamaño;
- tareas correctas o fallidas del pool.


## Incidencias y estado final

Los problemas repetidos sobre una misma ruta se fusionan. Por ejemplo, un acceso denegado detectado al enumerar archivos y subcarpetas se guarda como una sola incidencia con `stages`, `occurrences_count` y el número de duplicados fusionados.

Una búsqueda que termina y solo encuentra accesos denegados o archivos inválidos usa `completed_with_warnings`. `completed_with_errors` queda reservado para fallos críticos, como una ruta de origen inválida o un fallo inesperado del trabajador.
