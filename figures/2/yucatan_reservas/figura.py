"""Yucatán, al lado de sus reservas

viz_id: 2.yucatan_reservas
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Yucatán, al lado de sus reservas")
    return fig
