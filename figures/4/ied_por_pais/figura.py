"""Inversión extranjera directa (IED) en Yucatán por país de origen

viz_id: 4.ied_por_pais
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Inversión extranjera directa (IED) en Yucatán por país de origen")
    return fig
