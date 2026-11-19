"""Expansión urbana en Mérida

viz_id: 3.expansion_merida
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Expansión urbana en Mérida")
    return fig
