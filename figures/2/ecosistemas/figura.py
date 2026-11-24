"""Los ecosistemas que protege la península

viz_id: 2.ecosistemas

Barras horizontales apiladas con las 10 Áreas Naturales Protegidas (ANP) más
grandes de la península, divididas en superficie terrestre y superficie marina.
Se excluyen las tres áreas marinas de mayor extensión (Caribe Mexicano,
Arrecifes del Golfo de México-Sur y Bajos del Norte), que aplastarían al resto.

Tabla de oro (`datos`): una fila por ANP, ya recortada a Campeche, Yucatán y
Quintana Roo.
    nombre       nombre del ANP
    sup_ha       superficie total en hectáreas
    sterr_ha     superficie terrestre en hectáreas
    smar_ha      superficie marina en hectáreas
    cat_manejo   categoría de manejo (opcional, sale en el hover)
    estado       estado o estados (opcional, sale en el hover)

Fuentes: CONANP (datos.gob.mx, tabla de ANP) y SIMEC. La plantilla muestra
fuentes, fecha y responsable; no van dentro de la figura.
"""

import unicodedata

import pandas as pd
import plotly.graph_objects as go

TITULO = "Los ecosistemas que protege la península"
SUBTITULO = "Las 10 ANP más grandes (sin las 3 áreas marinas de mayor extensión)"

CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
COLOR_TERRESTRE, COLOR_MARINA = "#4a8c5f", "#4590f5"

N_ANP = 10

# Fragmentos (sin acentos ni mayúsculas) de los nombres que se excluyen.
EXCLUIR = ("caribe mexicano", "arrecifes del golfo de mexico", "bajos del norte")


def _sin_acentos(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", str(txt))
    return "".join(c for c in txt if not unicodedata.combining(c)).lower().strip()


def _num(serie: pd.Series) -> pd.Series:
    """Las cifras de CONANP pueden llegar como texto ("728,909")."""
    return pd.to_numeric(serie.astype(str).str.replace(",", "", regex=False).str.strip(),
                         errors="coerce")


def _n(x) -> str:
    return f"{x:,.0f}"


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=20, r=30, t=100, b=20),
    )
    if datos is None or len(datos) == 0:
        return fig

    df = datos.copy()
    for c in ("sup_ha", "sterr_ha", "smar_ha"):
        df[c] = _num(df[c])
    df["sterr_ha"] = df["sterr_ha"].fillna(0)
    df["smar_ha"] = df["smar_ha"].fillna(0)
    df = df.dropna(subset=["sup_ha"])
    df = df[df["sup_ha"] > 0]

    # Se quitan las tres áreas marinas gigantes y se toman las N más grandes.
    nombres_norm = df["nombre"].map(_sin_acentos)
    df = df[~nombres_norm.map(lambda n: any(e in n for e in EXCLUIR))]
    df = df.nlargest(N_ANP, "sup_ha").reset_index(drop=True)
    if df.empty:
        return fig

    nombres = df["nombre"].tolist()
    extra = []
    for _, f in df.iterrows():
        partes = [f"<b>{f['nombre']}</b>"]
        if "cat_manejo" in df.columns and pd.notna(f["cat_manejo"]):
            partes.append(str(f["cat_manejo"]))
        if "estado" in df.columns and pd.notna(f["estado"]):
            partes.append(str(f["estado"]))
        partes.append(f"Terrestre: {_n(f['sterr_ha'])} ha")
        partes.append(f"Marina: {_n(f['smar_ha'])} ha")
        partes.append(f"Total: {_n(f['sup_ha'])} ha")
        extra.append("<br>".join(partes))

    for nombre, col, color in (("Superficie terrestre", "sterr_ha", COLOR_TERRESTRE),
                               ("Superficie marina", "smar_ha", COLOR_MARINA)):
        fig.add_trace(go.Bar(
            y=nombres, x=df[col], name=nombre, orientation="h",
            marker=dict(color=color, line=dict(width=0)),
            customdata=extra, hovertemplate="%{customdata}<extra></extra>",
        ))

    # Etiqueta con el total al final de cada barra.
    fig.add_trace(go.Scatter(
        x=df["sup_ha"], y=nombres, mode="text", showlegend=False, hoverinfo="skip",
        text=[f"{_n(v)} ha" for v in df["sup_ha"]], textposition="middle right",
        textfont=dict(size=13, color=TEXTO_2),
    ))

    fig.update_layout(
        barmode="stack", bargap=0.2,
        title=dict(text=f"{TITULO}<br><sup>{SUBTITULO}</sup>"),
        xaxis=dict(title="Superficie (hectáreas)", tickformat=",", showgrid=True,
                   gridcolor="#e0dccf", griddash="dash", zeroline=False,
                   range=[0, float(df["sup_ha"].max()) * 1.18]),
        yaxis=dict(autorange="reversed", automargin=True, showgrid=False,
                   categoryorder="array", categoryarray=nombres),
        legend=dict(x=0.99, y=0.03, xanchor="right", yanchor="bottom",
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="#d9d4c4", borderwidth=1),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )
    return fig