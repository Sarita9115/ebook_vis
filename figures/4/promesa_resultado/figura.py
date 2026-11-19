"""Promesa contra resultado: empleos anunciados y empleo formal en el IMSS

viz_id: 4.promesa_resultado
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Promesa contra resultado: empleos anunciados y empleo formal en el IMSS")
    return fig
