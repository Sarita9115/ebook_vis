"""El entorno de la escuela

viz_id: 5.entorno_escuela
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="El entorno de la escuela")
    return fig
