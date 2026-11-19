"""Comparativa de población alfabetizada en los municipios de Yucatán

viz_id: 3.alfabetizacion
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Comparativa de población alfabetizada en los municipios de Yucatán")
    return fig
