"""Ranking porcentual del crecimiento poblacional de los estados de México

viz_id: 3.ranking_crecimiento
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Ranking porcentual del crecimiento poblacional de los estados de México")
    return fig
