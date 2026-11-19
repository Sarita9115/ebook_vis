"""Unidades económicas, empleo y producción en Yucatán (Censos Económicos 2019 y 2024)

viz_id: 4.censos_economicos
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Unidades económicas, empleo y producción en Yucatán (Censos Económicos 2019 y 2024)")
    return fig
