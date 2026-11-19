"""Concentración industrial en el corredor Mérida, Umán y Hunucmá

viz_id: 6.corredor_industrial
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Concentración industrial en el corredor Mérida, Umán y Hunucmá")
    return fig
