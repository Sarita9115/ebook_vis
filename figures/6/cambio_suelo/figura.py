"""Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida

viz_id: 6.cambio_suelo
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida")
    return fig
