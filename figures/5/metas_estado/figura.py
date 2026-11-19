"""Las metas del estado

viz_id: 5.metas_estado
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Las metas del estado")
    return fig
