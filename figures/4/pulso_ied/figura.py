"""El pulso de la inversión extranjera: ritmo de la IED en Yucatán (2020-2025)

viz_id: 4.pulso_ied
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="El pulso de la inversión extranjera: ritmo de la IED en Yucatán (2020-2025)")
    return fig
