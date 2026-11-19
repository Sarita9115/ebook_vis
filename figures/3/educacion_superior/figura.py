"""Evolución de la población con educación superior

viz_id: 3.educacion_superior
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Evolución de la población con educación superior")
    return fig
