"""Sobres contra maletines: remesas e inversión extranjera en Yucatán (2020-2025)

viz_id: 4.remesas_ied
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Sobres contra maletines: remesas e inversión extranjera en Yucatán (2020-2025)")
    return fig
