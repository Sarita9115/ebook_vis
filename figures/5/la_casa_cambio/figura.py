"""La casa cambió

viz_id: 5.la_casa_cambio
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="La casa cambió")
    return fig
