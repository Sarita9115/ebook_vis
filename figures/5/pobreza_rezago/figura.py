"""Pobreza y rezago

viz_id: 5.pobreza_rezago
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Pobreza y rezago")
    return fig
