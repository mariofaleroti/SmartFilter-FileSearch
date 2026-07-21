# Portabilidad y seguridad de categorías

Smart Filter 1.0.27-dev convierte la ventana Categorías en un administrador portable y recuperable.

## Exportar

Se puede exportar la categoría seleccionada o toda la base. El archivo usa el contrato estándar:

```text
meta
summary
report_brief
data
diagnostics
errors
```

`data.categories` conserva términos, exclusiones, categorías de descarte, estado, alcance y campos. Al exportar una sola categoría, también se incluyen sus dependencias de descarte para no perder referencias.

## Importar

La importación solo acepta contratos `category_database` o `category_export` válidos.

- **Agregar solo nuevas:** conserva todo y omite nombres existentes.
- **Combinar y actualizar:** agrega nuevas y reemplaza las que tengan el mismo nombre.
- **Reemplazar todas:** usa únicamente las categorías del archivo.

Antes de aplicar se muestra una vista previa con nuevas, coincidencias de nombre y categorías que serían retiradas.

## Backups automáticos

Se crea una copia exacta de `data/categories.json` antes de:

- modificar una categoría existente;
- renombrarla;
- eliminarla;
- importar;
- restaurar predeterminadas faltantes.

Ruta:

```text
data/backups/categories/
```

Se conservan las 30 copias más recientes. Son contratos completos y pueden importarse desde la misma ventana.

## Restaurar predeterminadas

**Restaurar predeterminadas** agrega únicamente las categorías base que falten. No sobrescribe categorías existentes y no elimina categorías creadas por el usuario.

Esto permite recuperar, por ejemplo, `administracion` después de una eliminación accidental sin perder otros cambios.

## Categorías de descarte

Las referencias cruzadas se seleccionan desde una lista filtrable. Smart Filter:

- excluye la categoría actual de la lista;
- evita duplicados;
- elimina referencias a categorías inexistentes;
- actualiza referencias cuando una categoría cambia de nombre;
- elimina referencias cuando una categoría se borra.
