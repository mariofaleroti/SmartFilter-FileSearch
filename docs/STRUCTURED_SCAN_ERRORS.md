# Errores estructurados de escaneo

Smart Filter conserva los errores no fatales sin llenar la GUI.

Cada detalle incluye:

- `code` / `error_type`
- `path`
- `stage`
- `message`
- `exception_type`
- `source`

El JSON exportado desde la GUI los guarda en `summary.error_details`.
El contrato estándar CLI los guarda en `data.search.error_details` y en la lista superior `errors`.

Las etapas distinguen validación de origen, enumeración de carpetas/archivos, lectura de contenido y análisis de coincidencias.
