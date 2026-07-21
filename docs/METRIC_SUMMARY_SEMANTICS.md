# Semántica del resumen final de búsqueda

Smart Filter 1.0.32 presenta seis tarjetas al finalizar una búsqueda. Cada una responde a una pregunta distinta y usa un contador concreto.

| Tarjeta | Fuente | Significado |
|---|---|---|
| Candidatos | `scan_stats.candidates_count` | Archivos aceptados por el escaneo para ser evaluados. |
| Leídos | `scan_stats.reader_succeeded_count` | Archivos cuyo contenido fue leído correctamente. Usa `readers_executed_count` solo como compatibilidad con resultados antiguos. |
| Archivos encontrados | `matched_candidates_count` | Archivos únicos con al menos una coincidencia. |
| Caracteres | `scan_stats.content_text_chars_count` | Volumen total de texto procesado por los lectores durante la búsqueda. |
| Sin coincidencia | `no_match_count` | Candidatos analizados que no cumplieron los criterios. |
| Incidencias | `scan_stats.issues_count` | Advertencias o errores registrados. Mantiene rojo tenue con cero y refuerza fondo, borde y texto cuando el valor es mayor que cero. |

## Ejemplo

Una búsqueda puede aceptar 3.098 candidatos, leer correctamente 3.098 archivos, encontrar 2.321 archivos y procesar 2.151.089 caracteres. Las ubicaciones internas de coincidencia siguen disponibles en el JSON y en el detalle de cada resultado, pero no se muestran como tarjeta principal porque su interpretación depende del formato del documento.

## Estado visual de Incidencias

- **Cero incidencias:** rojo tenue para conservar identidad semántica sin comunicar alarma activa.
- **Una o más incidencias:** rojo intenso y mayor contraste para señalar atención requerida.
- Existen variantes independientes para tema claro y oscuro.
