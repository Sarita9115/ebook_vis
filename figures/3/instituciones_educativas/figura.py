"""Disponibilidad de instituciones educativas en Yucatán

viz_id: 3.instituciones_educativas
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Disponibilidad de instituciones educativas en Yucatán")
    return fig
