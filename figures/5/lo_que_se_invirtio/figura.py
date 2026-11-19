"""Lo que se invirtió

viz_id: 5.lo_que_se_invirtio
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Lo que se invirtió")
    return fig
