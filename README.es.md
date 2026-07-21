# Smart Filter

Aplicación de escritorio y CLI rápida, privada y orientada a búsquedas inteligentes por nombre y contenido en múltiples formatos documentales.

[Read in English](README.md)

## De filtrar currículums a buscar en documentos

Smart Filter nació como una herramienta pequeña para localizar y filtrar archivos de currículums. Durante su evolución, el motor de búsqueda, las categorías, los lectores, las acciones sobre resultados, el control de recursos y el flujo portable crecieron hasta convertirlo en una aplicación general de búsqueda local.

Actualmente puede revisar nombres y texto accesible en XLSX, PDF, DOCX, CSV, TXT, LOG, Markdown, JSON, XML, HTML y HTM. Los originales no se modifican y las coincidencias pueden revisarse mediante vistas HTML destacadas.

## Funciones principales

- GUI de escritorio y CLI automatizable.
- Búsqueda por palabra, frase, categoría, nombre, contenido o criterios combinados.
- Categorías configurables, descarte, exclusiones y alcance por campos o secciones.
- Escaneo y lectura paralela acotada con cancelación cooperativa.
- Perfiles de recursos y métricas de CPU y memoria.
- Apertura del archivo original real, carpeta contenedora o vista HTML destacada.
- Exportación JSON y CSV con contrato estándar.
- Portable de Windows y desarrollo fuente en Windows/Linux.
- Procesamiento local sin subir documentos a servicios externos.


## Ayuda integrada

La ayuda de la aplicación organiza la información en **Inicio, Criterios, Categorías, Resultados, Rendimiento y Portable**. Es la referencia operativa del usuario final para comprender criterios, resultados, privacidad y comportamiento del portable.

## Privacidad

El estado del usuario se crea en `data/` durante la ejecución y está excluido de Git. También se ignoran vistas generadas, logs, resultados y artefactos de compilación. Antes de publicar diagnósticos, deben eliminarse rutas, nombres y contenido privado.

## Preparar el desarrollo

Windows:

```bat
SETUP_DEVELOPMENT_WINDOWS.cmd
```

Linux:

```bash
./SETUP_DEVELOPMENT_LINUX.sh
```

El instalador descarga la versión exacta validada de SharedCode Cores:

```text
sharedcode-cores 1.0.0
```

No se necesita una carpeta hermana de SharedCode.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe cli.py --help
```

## Construir el portable de Windows

```bat
BUILD_WINDOWS_RELEASE.cmd
```

El resultado esperado es:

```text
SmartFilter_Portable_v1.0.32.zip
```

## Arquitectura

SharedCode Cores aporta infraestructura reutilizable. Smart Filter conserva su lógica propia: política de búsqueda, categorías, readers, coincidencias, filtros, semántica de resultados y experiencia GUI/CLI.

Repositorio de SharedCode Cores: https://github.com/mariofaleroti/SharedCode-Cores

## Limitaciones

- No incluye OCR en la versión 1.0.32.
- Los PDF sin capa de texto y las imágenes no pueden analizarse por contenido.
- Los archivos bloqueados, protegidos o dañados pueden aparecer como incidencias.
- Una búsqueda sobre un disco completo puede requerir varios minutos.

## Validación

```powershell
python -m tools.run_release_validation
python -m tools.validate_public_repository
```

## Licencia

Smart Filter se publica bajo licencia MIT.
