# Entrega de visualizaciones UPY — Equipo 1

Este paquete reemplaza directamente los cuatro módulos `figura.py` ya existentes y actualiza las filas correspondientes del catálogo.

## Archivos incluidos

- `figures/1/gobierno_universitario/figura.py`
- `figures/1/trayectoria_estudiantil/figura.py`
- `figures/1/financiamiento_infraestructura/figura.py`
- `figures/1/carreras_modalidades/figura.py`
- `catalog/catalog.csv`

## Uso

Cada módulo expone `figura(datos) -> plotly.graph_objects.Figure`.

- Si `datos` es `None` o un DataFrame vacío, usa los datos documentales incluidos en el módulo para renderizar una figura reproducible.
- Si se pasa un DataFrame, debe tener las columnas descritas en el docstring del módulo. Así podrá conectarse posteriormente a la tabla de oro sin cambiar la función de visualización.
- Los datos base no son una serie inventada: cada punto tiene su fuente y su limitación descrita en el docstring y en el catálogo.

## Criterios de interpretación

1. **Gobierno:** los años muestran la fecha de documentos o hitos, no fechas de nombramiento ni periodos completos de rectoría. El gráfico no afirma una fecha exacta de inicio/fin de cada gestión.
2. **Trayectoria:** 481 corresponde a matrícula 2022 de Data México; 530 es la matrícula descrita como actual en una publicación de 2023. No se presentan como una serie anual homogénea. El desglose por carrera, sexo y egresados es el de 2022.
3. **Financiamiento:** se comparan estados de actividades del primer trimestre de 2025 y 2026. No se deben interpretar como presupuesto anual autorizado. Los activos son saldos contables al 31 de marzo de 2026, no inversión ejercida durante el trimestre.
4. **Carreras:** la oferta actual y la doble titulación se toman del portal de la UPY. La página de Ciberseguridad anuncia modalidad mixta, pero en la misma ficha aparece también “presencial”; la visualización conserva explícitamente esa discrepancia.

## Validación local

Desde la raíz del repositorio, con el entorno virtual activo:

```bash
python - <<'PY'
import importlib.util
from pathlib import Path
import plotly.graph_objects as go

paths = [
    Path('figures/1/gobierno_universitario/figura.py'),
    Path('figures/1/trayectoria_estudiantil/figura.py'),
    Path('figures/1/financiamiento_infraestructura/figura.py'),
    Path('figures/1/carreras_modalidades/figura.py'),
]
for i, path in enumerate(paths):
    spec = importlib.util.spec_from_file_location(f'figura_{i}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fig = module.figura(None)
    assert isinstance(fig, go.Figure), path
    print(f'OK: {path} — {len(fig.data)} trazas')
PY
```

Los CSV/XLSX originales no se agregan al repositorio, de acuerdo con el `readme.md` del proyecto.
