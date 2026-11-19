"""Huella construida, altura y densidad empresarial de Mérida

viz_id: 6.huella_construida
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Huella construida, altura y densidad empresarial de Mérida")
    return fig
