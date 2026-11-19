"""Atracción de capital, empleo y evolución de las unidades económicas en Yucatán

viz_id: 6.atraccion_capital
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Atracción de capital, empleo y evolución de las unidades económicas en Yucatán")
    return fig
