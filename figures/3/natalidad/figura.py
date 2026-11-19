"""Natalidad y crecimiento poblacional de los municipios de Yucatán

viz_id: 3.natalidad
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Natalidad y crecimiento poblacional de los municipios de Yucatán")
    return fig
