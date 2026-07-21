# Checklist de Release Candidate

Este checklist se completa sobre el artefacto indicado por `APP_VERSION` antes de promoverlo a estable.

## 1. Fuente

- [ ] `APP_VERSION` coincide con la versión objetivo.
- [ ] README y CHANGELOG reflejan la versión.
- [ ] `resources/defaults/` contiene la configuración y categorías de fábrica.
- [ ] `data/` no contiene rutas, historial, categorías ni términos de prueba.
- [ ] No hay `.git`, `build`, `dist`, `release`, `runtime`, `output`, `__pycache__`, `.venv` ni resultados personales.

## 2. Dependencias

- [ ] `requirements.txt` incluye `Jinja2>=3.1.6`, `openpyxl>=3.1.5` y `psutil`.
- [ ] SharedCode utilizado es la versión aprobada.
- [ ] RenderCore y sus templates están disponibles.
- [ ] Los archivos `.spec` contienen los imports necesarios para multiprocessing y GUI.

## 3. Validaciones

```powershell
python -m tools.run_release_validation
```

- [ ] Todos los validadores finalizan correctamente.
- [ ] `compileall` no reporta errores.
- [ ] La CLI sin argumentos muestra ayuda y no genera snapshots.
- [ ] Una búsqueda normal genera solamente la salida solicitada.

## 4. Build Windows

```text
release/SmartFilter/
├─ SmartFilter.exe
├─ SmartFilterCLI.exe
├─ tool_manifest.json
├─ data/
└─ assets/
```

- [ ] GUI abre sin Python instalado.
- [ ] CLI muestra `--help` y ejecuta una búsqueda.
- [ ] `SmartFilterCLI.exe --portable-self-check` finaliza correctamente.
- [ ] Icono visible en ventanas principales y secundarias.
- [ ] CPU y RAM aparecen en el JSON cuando corresponde.
- [ ] Apertura de original, carpeta y Destacado funcionan.
- [ ] Importación y exportación funcionan.
- [ ] Ayuda y Acerca de muestran el canal derivado de la versión.
- [ ] El portable no contiene README ni artefactos de desarrollo.

## 5. Máquina virtual limpia

- [ ] Copiar únicamente `release/SmartFilter/`.
- [ ] Ejecutar SmartFilter.exe sin instalar dependencias.
- [ ] Ejecutar SmartFilterCLI.exe sin instalar dependencias.
- [ ] Probar Automático + Equilibrado.
- [ ] Probar cancelación.
- [ ] Confirmar que no se crean archivos fuera de las rutas previstas.
- [ ] Revisar logs y JSON por errores críticos.

## 6. Contrato y Toolkit

- [ ] El JSON contiene `meta`, `summary`, `report_brief`, `data`, `diagnostics` y `errors`.
- [ ] `tool_manifest.json` apunta a los ejecutables y salidas correctas.
- [ ] El manifest declara RenderCore entre los núcleos utilizados.
- [ ] Toolkit consume el release sin depender del proyecto fuente.

## 7. Promoción

- [ ] El artefacto RC cotidiano fue probado sin incidencias bloqueantes.
- [ ] Cambiar `APP_VERSION` de `x.y.z-rcN` a `x.y.z`.
- [ ] Confirmar que Acerca de y el manifest cambian automáticamente a estable.
- [ ] Registrar la promoción en CHANGELOG.
- [ ] Construir nuevamente desde cero y repetir las pruebas finales.
- [ ] Crear tag o commit identificable.
