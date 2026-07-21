# Alcance estricto de categorías por campos o secciones

## Objetivo

`Limitar dónde buscar` restringe únicamente los términos de la categoría. No limita el escaneo del archivo, la palabra/frase principal, el contexto ni las exclusiones.

La opción expresa una condición estructural:

> El documento debe contener un campo, columna, clave o encabezado reconocible con el nombre configurado, y el término de la categoría debe aparecer dentro de su valor o bloque asociado.

No significa «encontrar esa palabra en cualquier frase y analizar todo lo posterior».

## Formas reconocidas

### Campo o etiqueta con valor

```text
Experiencia: Administración de servidores
```

Se analiza únicamente `Administración de servidores`.

### Encabezado independiente

```text
1. INCIDENCIAS
Error de permisos
Servicio detenido

2. ACCIONES
Reinicio controlado
```

Configurar `Incidencias` analiza el bloque hasta `2. ACCIONES`.

Se admiten encabezados exactos, Markdown, numeración, mayúsculas y títulos visualmente aislados.

### Archivos estructurados

Los readers conservan relaciones campo-valor:

```text
XLSX/CSV  → Experiencia: Administración de servidores
JSON/XML  → incidencias: / detalle: Error administrativo
DOCX      → párrafos separados y tablas con encabezados
PDF/TXT   → líneas y encabezados del documento
```

## Rechazo de falsas secciones

```text
Experiencia administrativa requerida para el puesto.
```

Aunque comience con `Experiencia`, es una oración completa y no una etiqueta ni encabezado exacto. El alcance queda vacío.

La antigua compatibilidad con texto aplanado solo se activa cuando aparecen varias etiquetas conocidas y se puede demostrar una estructura tipo formulario o CV.

## Variantes controladas

Se mantienen equivalencias previsibles:

```text
Experiencia ↔ Experiencia laboral ↔ Experiencia profesional
Perfil ↔ Perfil laboral ↔ Perfil profesional
Formación ↔ Formación académica ↔ Educación ↔ Estudios
Habilidades ↔ Competencias ↔ Conocimientos
```

No se usan prefijos abiertos. Por eso `Experiencia administrativa requerida` no se convierte en una variante de `Experiencia`.

## Ausencia de estructura

Cuando el campo o sección no existe:

- la categoría no coincide;
- no se vuelve al documento completo;
- no se registra una incidencia técnica;
- la palabra/frase principal conserva su alcance independiente.

## Validación

```bash
python -m tools.validate_category_section_detection
python -m tools.validate_category_target_fields_scope
```

Las pruebas cubren CV, informes generales, Markdown, secciones numeradas, campos escalares, rechazo de frases casuales, readers estructurados y la ruta multiprocessing.
