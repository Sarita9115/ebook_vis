"""Turismo y derrama económica

viz_id: 4.turismo_derrama
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Turismo y derrama económica")
    return fig
