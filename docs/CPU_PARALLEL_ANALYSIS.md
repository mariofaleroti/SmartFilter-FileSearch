# Análisis CPU paralelo — Smart Filter 1.0.21-dev

## Objetivo

Separar el trabajo principalmente I/O de los lectores del trabajo CPU de normalización y coincidencias sin volver a retener el contenido completo de todos los candidatos.

## Política de activación

```text
Ruta normal
→ pipeline integrado anterior (4 trabajadores por hilos)

Raíz amplia: C:\, D:\, /
→ 4 lectores por hilos
→ lotes acotados
→ procesos CPU persistentes
```

La variable `SMARTFILTER_CPU_ANALYSIS` existe para validación y diagnóstico:

```text
auto    comportamiento predeterminado
always  fuerza procesos en cualquier carpeta
on      igual que always
off     desactiva procesos
```

No es una opción visual de usuario en este corte.

## Procesos recomendados

```text
1–4 CPU lógicos   → 1 proceso
5–12              → 2 procesos
13–20             → 3 procesos
más de 20         → 4 procesos
```

El límite deja capacidad para Windows/Linux, GUI, lectores y aplicaciones abiertas.

## Lotes y memoria

Cada lote se cierra al alcanzar cualquiera de estos límites:

```text
64 candidatos
4 MiB de contenido extraído
```

Hay como máximo dos lotes pendientes por proceso. Durante este modo, la cola lectora baja de 40 a 16. El proceso retorna solamente resultados compactos; el texto extraído se libera después del análisis.

## Tolerancia a fallos

- Un error de coincidencia individual vuelve como incidencia estructurada.
- Si un lote o el pool falla, Smart Filter registra una advertencia y reanaliza el lote localmente.
- El orden final se reconstruye con la secuencia original del candidato.
- Los archivos originales nunca se modifican.

## Cancelación

Durante una búsqueda, el botón `Buscar` cambia a `Cancelar`.

La cancelación:

1. detiene el productor de candidatos;
2. deja de alimentar lectores;
3. cancela tareas y lotes aún no iniciados;
4. descarta resultados parciales;
5. restaura la GUI sin mostrar un error.

Las lecturas o procesos que ya estaban ejecutando una llamada terminan naturalmente, pero no bloquean el retorno de la GUI.

## Métricas nuevas

`scan_stats` incluye:

```text
analysis_backend
analysis_processes_count
analysis_batch_max_items
analysis_batch_max_content_chars
analysis_batches_submitted_count
analysis_batches_completed_count
analysis_batches_failed_count
analysis_fallback_batches_count
analysis_peak_pending_batches_count
analysis_worker_pids
analysis_pipeline_elapsed_seconds
analysis_candidates_per_second
analysis_payload_content_chars_count
analysis_cancelled
```

## PyInstaller

`app.py` y `cli.py` llaman `multiprocessing.freeze_support()` bajo el guard de entrada. Ambos `.spec` incluyen explícitamente los módulos de análisis paralelo requeridos por los procesos generados en Windows.

## Evolución 1.0.22-dev

El número de procesos deja de depender únicamente de hilos lógicos. La política usa núcleos físicos, reserva de sistema y perfil de recursos. El límite de lotes pendientes se aplica como backpressure estricto y el monitor registra CPU/RAM en `data.performance`.
