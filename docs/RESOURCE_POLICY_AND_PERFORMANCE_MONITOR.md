# Política de recursos y monitor de rendimiento

Smart Filter 1.0.32 adapta el trabajo al equipo detectado y registra telemetría del proceso principal y de los procesos analizadores.

## Objetivo

La política busca tres cosas:

1. acelerar búsquedas amplias;
2. evitar que Smart Filter se apropie de toda la CPU;
3. mantener acotadas las colas y el contenido temporal en memoria.

La detección utiliza `psutil` para obtener núcleos físicos y lógicos. Cuando `psutil` no está disponible, se usa un cálculo conservador basado en `os.cpu_count()` y el monitor queda deshabilitado.

## Perfiles automáticos

### Bajo consumo

- prioriza la respuesta del sistema;
- usa un proceso de análisis;
- limita lectores y lotes pendientes;
- es apropiado para máquinas virtuales pequeñas, notebooks o trabajo simultáneo.

### Equilibrado

- es el valor predeterminado y recomendado;
- reserva aproximadamente un tercio de los núcleos físicos, con un mínimo razonable;
- limita procesos y lectores para mantener fluidez;
- ofrece la mejor relación general entre tiempo, CPU y memoria.

### Alto rendimiento

- reserva al menos un núcleo físico;
- habilita más procesos y lectores;
- prioriza terminar antes;
- puede aumentar CPU, RAM, temperatura y consumo.

Los números concretos dependen del equipo. La vista previa de Configuración muestra la política efectiva antes de guardar.

## Manual técnico

Permite configurar:

- procesos de análisis;
- lectores concurrentes;
- núcleos físicos reservados;
- máximo de lotes pendientes.

Smart Filter ajusta valores fuera de rango según la topología detectada. El máximo permitido no significa necesariamente que sea la combinación más rápida.

Regla práctica:

```text
más lectores alimentan el pipeline;
más procesos consumen lotes;
más lotes pendientes aumentan paralelismo y memoria temporal.
```

Una configuración desequilibrada, por ejemplo muchos lectores y un solo proceso, puede aumentar memoria sin mejorar proporcionalmente el tiempo total.

## Backpressure

El productor no puede superar `max_pending_batches`. Cuando alcanza el límite, espera la finalización de al menos un lote antes de enviar otro.

Esto evita crecimiento sin control de tareas pendientes y mantiene una relación predecible entre procesos, lotes y memoria.

## Cuándo se usa multiprocessing

El backend de procesos se activa en búsquedas amplias, especialmente raíces de unidad como:

```text
C:\
D:\
/
```

Las carpetas normales pueden continuar con el pipeline integrado basado en hilos. Por eso una búsqueda pequeña puede no mostrar procesos analizadores hijos aunque el monitor esté habilitado.

## Métricas registradas

El monitor toma una muestra por segundo y guarda agregados en `data.performance` y en el bloque `performance` de exportaciones GUI.

### CPU

- promedio, pico y percentil 95 del sistema;
- núcleos promedio, pico y percentil 95 usados por Smart Filter;
- proceso principal;
- conjunto de procesos hijos;
- detalle por PID de cada proceso analizador.

La CPU de Smart Filter se expresa también como porcentaje normalizado sobre los hilos lógicos. Para interpretar carga real resulta más útil observar `smartfilter_average_cores` y `smartfilter_peak_cores`.

### Memoria

- promedio y pico del proceso principal;
- promedio y pico de procesos hijos;
- promedio y pico total del árbol;
- memoria mínima disponible en el sistema.

Los picos pueden corresponder a documentos grandes o lotes que contienen mucho texto. Una caída posterior indica liberación normal; una subida continua durante ejecuciones comparables requeriría investigación.

### Pipeline

- lectores activos;
- capacidad de cola;
- procesos de análisis;
- lotes enviados, completados, fallidos y recuperados por fallback;
- límite y pico real de lotes pendientes.

### Cronología

Cuando está habilitada, conserva una muestra reducida cada 10 segundos con fase, CPU, RAM, memoria disponible y cantidad de procesos hijos.

## Validación de la medición por procesos

Desde 1.0.23-dev, el monitor conserva una instancia `psutil.Process` por PID. Esto permite que `cpu_percent(interval=None)` compare muestras sucesivas y evita lecturas perpetuas en cero.

La suma esperada es:

```text
CPU Smart Filter = CPU proceso principal + CPU procesos hijos
```

Los analizadores pueden alcanzar aproximadamente un núcleo cada uno durante ráfagas sin permanecer saturados toda la ejecución. La lectura, extracción, serialización y espera de disco forman parte del tiempo total.

## Referencia validada en un equipo de 6 núcleos / 12 hilos

En una búsqueda completa sobre `C:\`, la política automática resolvió aproximadamente:

| Perfil | Procesos | Lectores | Reserva | Pendientes |
|---|---:|---:|---:|---:|
| Bajo consumo | 1 | 2 | 3 | 1 |
| Equilibrado | 2 | 4 | 2 | 4 |
| Alto rendimiento | 3 | 6 | 2 | 6 |

También se validó una configuración manual de prueba:

```text
4 procesos · 8 lectores · 1 núcleo reservado · 8 lotes pendientes
```

Esta referencia demuestra el comportamiento en ese equipo y carga concreta; no debe copiarse automáticamente a hardware distinto.

## Recomendaciones

- Mantener `Automático + Equilibrado` como configuración general.
- Usar `Alto rendimiento` cuando la prioridad sea terminar antes.
- Usar `Bajo consumo` en equipos limitados o mientras se realizan otras tareas.
- Cambiar Manual técnico de una variable por vez y comparar búsquedas equivalentes.
- Evaluar tiempo, CPU, RAM, lotes y resultados; no solo el porcentaje de CPU.
- No desactivar el monitor durante pruebas de calibración.
