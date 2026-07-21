# Integridad del portable y sanitización del destacado XLSX

## Diagnóstico confirmado

El portable recuperado desde el historial Git fue inspeccionado directamente. El ejecutable contenía `1.0.27-dev` y los módulos `candidate_analysis`, `result_action_service` y `app_info` coincidían byte por byte con el build actual. PyInstaller sí había incluido el motor y SharedCode.

El error al crear una vista destacada para ciertos TXT/LOG no era una dependencia ausente. Algunos documentos conservan caracteres de control como `NUL` (`\x00`) o `BEL` (`\x07`). Esos caracteres pueden existir en logs, reportes de antivirus, salida de consola o archivos parcialmente binarios, pero no son válidos en el XML interno de una hoja XLSX. `openpyxl` rechaza la celda con `IllegalCharacterError`.

## Corrección

Antes de escribir texto en la copia XLSX, Smart Filter reemplaza los controles XML 1.0 no permitidos por el carácter de sustitución `�`. El original nunca se modifica. También elimina cualquier archivo temporal incompleto cuando la generación falla.

## Autoprueba del ejecutable

`SmartFilterCLI.exe --portable-self-check` valida dentro del ejecutable empaquetado:

- versión embebida;
- agrupación de una categoría con dos ocurrencias en una sola fila por archivo;
- disponibilidad real de `openpyxl`;
- creación de una vista XLSX desde texto con caracteres de control.

El build de Windows ejecuta esta prueba después de copiar los ejecutables al release. Si falla, `tools/build_release.py --build-exe` termina con error y no presenta el release como válido.

## Nombre del ZIP

`BUILD_PORTABLE_WINDOWS.ps1` obtiene `APP_VERSION` dinámicamente. El archivo deja de llamarse siempre `SmartFilter_Portable_v1.0.5.zip` y pasa a usar, por ejemplo:

```text
SmartFilter_Portable_v1.0.28-dev.zip
```

Esto evita confundir un build reciente con un paquete anterior.

## Agrupación actual

La agrupación por archivo se aplica cuando la categoría es el único criterio principal. Cuando existe también una palabra/frase, el motor conserva filas por ocurrencia. Esa es una regla funcional del motor, no una diferencia entre desarrollo y portable.
