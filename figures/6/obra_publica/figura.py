"""Obra pública e infraestructura para el desarrollo económico por municipio

viz_id: 6.obra_publica
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Obra pública e infraestructura para el desarrollo económico por municipio")
    return fig
