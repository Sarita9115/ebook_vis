"""La fauna de la península, en tu espacio

viz_id: 2.fauna_nom059
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="La fauna de la península, en tu espacio")
    return fig
