"""Cada tipo de negocio situado en cada reserva natural

viz_id: 2.negocios_en_reservas
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Cada tipo de negocio situado en cada reserva natural")
    return fig
