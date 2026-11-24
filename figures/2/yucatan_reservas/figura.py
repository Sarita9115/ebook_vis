"""Yucatán, al lado de sus reservas

viz_id: 2.yucatan_reservas

Columnas que espera `datos` (tabla de oro):
    area          nombre del ANP
    categoria     Reserva Estatal, Parque Estatal, etc.
    superficie_ha superficie en hectáreas (número)
    decreto       fecha de decreto (texto dd/mm/aaaa), opcional
"""

import plotly.graph_objects as go

TITULO = "Yucatán, al lado de sus reservas"
RAIZ = "Áreas naturales protegidas de Yucatán"

# Una categoría = un color (paleta apta para daltonismo).
COLORES = {
    "Reserva Estatal": "#1b7f5c",
    "Parque Estatal": "#e0a030",
    "Área Natural Protegida de Valor Escénico Histórico y Cultural": "#7b5ea7",
}
COLOR_OTRO = "#8a8a8a"


def _limpia_categoria(txt: str) -> str:
    """Corrige erratas conocidas de la fuente (p. ej. 'Reseva Estatal')."""
    txt = str(txt).strip()
    return "Reserva Estatal" if txt == "Reseva Estatal" else txt


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    df = datos.copy()
    df["categoria"] = df["categoria"].map(_limpia_categoria)
    df = df.dropna(subset=["superficie_ha"])
    df = df[df["superficie_ha"] > 0].sort_values("superficie_ha", ascending=False)

    total = float(df["superficie_ha"].sum())
    decretos = df["decreto"] if "decreto" in df else [""] * len(df)

    ids = ["raiz"] + [f"anp{i}" for i in range(len(df))]
    labels = [RAIZ] + df["area"].tolist()
    parents = [""] + ["raiz"] * len(df)
    values = [total] + df["superficie_ha"].tolist()
    colores = ["#f2f2f2"] + [COLORES.get(c, COLOR_OTRO) for c in df["categoria"]]

    detalle = [f"<b>{RAIZ}</b><br>{total:,.0f} ha en {len(df)} áreas"]
    for (_, fila), dec in zip(df.iterrows(), decretos):
        pct = fila["superficie_ha"] / total * 100
        extra = f"<br>Decreto: {dec}" if dec else ""
        detalle.append(
            f"<b>{fila['area']}</b><br>{fila['categoria']}"
            f"<br>{fila['superficie_ha']:,.2f} ha ({pct:.1f} % del total)"
            f"{extra}"
        )

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(colors=colores, line=dict(width=2, color="white")),
            customdata=detalle,
            hovertemplate="%{customdata}<extra></extra>",
            texttemplate="<b>%{label}</b><br>%{value:,.0f} ha",
            textposition="middle center",
            textfont=dict(color="white", size=14),
            tiling=dict(pad=4),
            root_color="#f2f2f2",
        )
    )

    # Leyenda manual: el treemap no genera leyenda por color.
    for categoria, color in COLORES.items():
        if categoria in set(df["categoria"]):
            fig.add_trace(
                go.Scatter(
                    x=[None], y=[None], mode="markers",
                    marker=dict(size=12, color=color, symbol="square"),
                    name=categoria, showlegend=True, hoverinfo="skip",
                )
            )

    fig.update_layout(
        title=TITULO,
        legend=dict(orientation="h", y=-0.02, x=0, font=dict(size=11)),
        margin=dict(t=60, l=10, r=10, b=50),
        uniformtext=dict(minsize=9, mode="hide"),
    )
    return fig


if __name__ == "__main__":
    # Prueba local con los datos de SANPY (SDS Yucatán). No es la tabla de oro.
    import pandas as pd

    prueba = pd.DataFrame(
        [
            ("Dzilam", "Reserva Estatal", 69039.29, "24/01/1989"),
            ("El Palmar", "Reserva Estatal", 47931.45, "29/01/1990"),
            ("Ciénagas y manglares de la costa norte de Yucatán", "Reserva Estatal", 54776.726, "19/03/2010"),
            ("Kabah", "Parque Estatal", 949.76, "9/06/1993"),
            ("San Juan Bautista Tabi y Anexa Sacnité", "Área Natural Protegida de Valor Escénico Histórico y Cultural", 1355.74, "7/06/1994"),
            ("Lagunas de Yalahau", "Parque Estatal", 5683.28, "8/06/1999"),
            ("Biocultural del Puuc", "Reseva Estatal", 135848.85, "1/11/2011"),
            ("Ich Kool Balamtun", "Parque Estatal", 452.32, "31/08/2017"),
            ("Geohidrológica Anillo de Cenotes", "Reserva Estatal", 219207.83, "19/10/2013"),
        ],
        columns=["area", "categoria", "superficie_ha", "decreto"],
    )
    figura(prueba).show()
