"""Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán

viz_id: 6.gasto_publico
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán")
    return fig
