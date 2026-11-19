"""Relieve y altura edificada de la zona metropolitana de Mérida vistos desde modelos de elevación de 5 m

viz_id: 6.relieve_5m
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Relieve y altura edificada de la zona metropolitana de Mérida vistos desde modelos de elevación de 5 m")
    return fig
