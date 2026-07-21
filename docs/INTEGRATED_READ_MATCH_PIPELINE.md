# Pipeline integrado de lectura y coincidencias

Smart Filter 1.0.15-dev elimina la separación anterior entre lectura y análisis.

## Flujo

```text
Escáner único
  → cola acotada de 40
  → 4 trabajadores
      → abrir archivo
      → extraer texto
      → evaluar términos y ocurrencias
      → guardar resultados compactos
      → liberar el texto completo
```

La política de coincidencias sigue perteneciendo a Smart Filter. SharedCode continúa aportando únicamente el recorrido seguro y el pool acotado de trabajadores.

## Compatibilidad

- Se conservan los resultados por ocurrencia y línea.
- Se conservan exclusiones, contexto, categorías y filtros de descarte.
- `scan_and_read_elapsed_seconds` se mantiene por compatibilidad, pero en este modo incluye el análisis integrado.
- `match_analysis_elapsed_seconds` queda en `0.0` porque ya no existe una segunda pasada.
- `match_analysis_worker_elapsed_seconds_total` informa la suma de tiempo consumido por los trabajadores; no representa tiempo de pared.
