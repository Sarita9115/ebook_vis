"""IED hacia Yucatán por año, ranking y origen (2018-2025)

viz_id: 4.ied_ranking_origen
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="IED hacia Yucatán por año, ranking y origen (2018-2025)")
    return fig
