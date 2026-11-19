"""Municipios con mayor concentración de población joven

viz_id: 3.poblacion_joven
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Municipios con mayor concentración de población joven")
    return fig
