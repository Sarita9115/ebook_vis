"""Participación estudiantil y comunidad

viz_id: 1.participacion_estudiantil
El formato de fuentes agrupa los enlaces de este equipo en siete títulos.
Esta carpeta sigue el título del relato y no abre una carpeta extra.
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Participación estudiantil y comunidad")
    return fig
