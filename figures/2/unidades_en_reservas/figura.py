"""Unidades económicas de impacto ambiental o relación con la biodiversidad

viz_id: 2.unidades_en_reservas
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Unidades económicas de impacto ambiental o relación con la biodiversidad")
    return fig
