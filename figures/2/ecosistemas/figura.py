"""Los ecosistemas que protege la península

viz_id: 2.ecosistemas
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Los ecosistemas que protege la península")
    return fig
