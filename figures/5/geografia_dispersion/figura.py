"""La geografía de la dispersión

viz_id: 5.geografia_dispersion
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="La geografía de la dispersión")
    return fig
