"""Sobres contra maletines: remesas e inversión extranjera en Yucatán (2020-2025)

viz_id: 4.remesas_ied

Tabla de oro (`datos`): una fila por año completo desde 2020.
  anio, remesas_mdd (Banxico), ied_mdd (Secretaría de Economía), veces (remesas / IED), y los metadatos.

Gráfico de iconos: cada sobre son 50 millones de dólares que mandan los migrantes a sus familias; cada maletín,
50 millones que traen las empresas extranjeras. El último icono de cada fila se recorta a la fracción que falta.

Fuente primaria: Banco de México, ingresos por remesas por entidad (API pública de Data México).
Secundaria: Secretaría de Economía, estadística oficial de la IED por entidad federativa.
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "Sobres contra maletines: remesas e inversión extranjera en Yucatán (2020-2025)"
UNIDAD = 50      # millones de dólares por icono
ALTO_FILA = 1.75

# Paso a paso: qué años se resaltan (None = todos).
PASOS = {1: [2020, 2021], 2: [2022], 3: [2023, 2024, 2025]}


def _rect(x0, y0, w, h):
    return [x0, x0 + w, x0 + w, x0, x0], [y0, y0, y0 + h, y0 + h, y0]


def _iconos(valor, y, tipo):
    """Polígonos de una fila de sobres o maletines. Devuelve (cuerpos, detalles en blanco, asas)."""
    cuerpos, detalles, asas = [], [], []
    n = valor / UNIDAD
    for k in range(int(np.ceil(n))):
        frac = min(1.0, n - k)
        if frac < 0.06:
            continue
        w = 0.82 * frac
        if tipo == "sobre":
            cuerpos.append(_rect(k, y, w, 0.52))
            if frac > 0.6:  # solapa del sobre
                detalles.append(([k + 0.03, k + 0.41, k + 0.79], [y + 0.50, y + 0.22, y + 0.50]))
        else:
            cuerpos.append(_rect(k, y, w, 0.46))
            if frac > 0.6:
                asas.append(([k + 0.28, k + 0.28, k + 0.54, k + 0.54], [y + 0.46, y + 0.57, y + 0.57, y + 0.46]))
                detalles.append(_rect(k + 0.35, y + 0.19, 0.12, 0.08))
    return cuerpos, detalles, asas


def _traza(formas, **kw):
    xs, ys = [], []
    for fx, fy in formas:
        xs += list(fx) + [None]
        ys += list(fy) + [None]
    return go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", **kw)


def figura(datos, paso: int | None = None) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro.

    paso (1-3) resalta un grupo de años de la lectura guiada; None muestra todos por igual.
    """
    fig = e.base(go.Figure(), TITULO, alto=640)
    fig.update_layout(margin=dict(l=20, r=20, t=110, b=30))
    if datos is None or len(datos) == 0:
        return fig

    d = datos.sort_values("anio").reset_index(drop=True)
    n = len(d)
    resaltados = PASOS.get(paso)
    imax_ied = int(d.ied_mdd.idxmax())

    for i, r in d.iterrows():
        base = (n - 1 - i) * ALTO_FILA
        op = 1.0 if (resaltados is None or r.anio in resaltados) else 0.2
        ys, ym = base + 0.8, base + 0.08
        cuerpos, solapas, _ = _iconos(r.remesas_mdd, ys, "sobre")
        fig.add_trace(_traza(cuerpos, fill="toself", fillcolor=e.AGUA, line=dict(color=e.AGUA, width=0.5),
                             opacity=op))
        fig.add_trace(_traza(solapas, line=dict(color=e.PAPEL, width=1.4), opacity=op))
        cuerpos, broches, asas = _iconos(r.ied_mdd, ym, "maletin")
        fig.add_trace(_traza(asas, line=dict(color=e.AZUL, width=2.2), opacity=op))
        fig.add_trace(_traza(cuerpos, fill="toself", fillcolor=e.AZUL, line=dict(color=e.AZUL, width=0.5),
                             opacity=op))
        fig.add_trace(_traza(broches, fill="toself", fillcolor=e.PAPEL, line=dict(color=e.PAPEL, width=0.5),
                             opacity=op))

        # Cifras al final de cada fila y el año a la izquierda.
        for valor, y, extra in [(r.remesas_mdd, ys, ""),
                                (r.ied_mdd, ym, "   ← único año en que ganó la inversión"
                                 if i == imax_ied and r.ied_mdd > r.remesas_mdd else "")]:
            fig.add_annotation(x=valor / UNIDAD + 0.25, y=y + 0.25, text=f"{valor:,.0f}{extra}", showarrow=False,
                               xanchor="left", font=dict(family=e.LETRA, size=12.5, color=e.TINTA),
                               opacity=max(op, 0.45))
        fig.add_annotation(x=-0.35, y=base + 0.66, text=f"<b>{r.anio}</b>", showarrow=False, xanchor="right",
                           font=dict(family=e.LETRA, size=15, color=e.TINTA), opacity=max(op, 0.45))
        # Tooltip de la fila.
        fig.add_trace(go.Scatter(
            x=[0.4], y=[base + 0.6], mode="markers", marker=dict(size=40, color="rgba(0,0,0,0)"),
            hovertemplate=(f"<b>{r.anio}</b><br>Remesas: {r.remesas_mdd:,.1f} mdd<br>"
                           f"Inversión extranjera: {r.ied_mdd:,.1f} mdd<br>"
                           f"Por cada dólar de inversión llegaron {r.veces:,.1f} de remesas<extra></extra>")))

    # Leyenda (los iconos de muestra se dibujan arriba, sobre el área de la figura).
    total_r, total_i = d.remesas_mdd.sum(), d.ied_mdd.sum()
    tope = n * ALTO_FILA + 0.2
    for k, (tipo, texto) in enumerate([("sobre", "remesas · cada sobre = 50 mdd"),
                                       ("maletin", "inversión extranjera · cada maletín = 50 mdd")]):
        x0 = k * 8.5
        cuerpos, det, asas = _iconos(UNIDAD, 0, tipo)
        mover = lambda f: ([v + x0 for v in f[0]], [v + tope for v in f[1]])  # noqa: E731
        color = e.AGUA if tipo == "sobre" else e.AZUL
        fig.add_trace(_traza([mover(f) for f in asas], line=dict(color=color, width=2.2)))
        fig.add_trace(_traza([mover(f) for f in cuerpos], fill="toself", fillcolor=color,
                             line=dict(color=color, width=0.5)))
        fig.add_trace(_traza([mover(f) for f in det], line=dict(color=e.PAPEL, width=1.4),
                             fill="toself" if tipo == "maletin" else None,
                             fillcolor=e.PAPEL if tipo == "maletin" else None))
        fig.add_annotation(x=x0 + 1.05, y=tope + 0.27, text=texto, showarrow=False, xanchor="left",
                           font=dict(family=e.LETRA, size=12.5, color=e.TINTA))

    lado = [
        (0.88, f"<b>{total_r / total_i:.1f}×</b>", 48, e.TINTA),
        (0.72, f"más dinero llegó en sobres<br>que en maletines ({d.anio.min()}-{d.anio.max()})", 14, e.TINTA_2),
        (0.52, f"<b>{total_r:,.0f} mdd</b>", 19, e.AGUA),
        (0.45, "en remesas", 12.5, e.TINTA_2),
        (0.34, f"<b>{total_i:,.0f} mdd</b>", 19, e.AZUL),
        (0.27, "en inversión extranjera", 12.5, e.TINTA_2),
        (0.14, "<i>Los sobres crecieron cada año;<br>los maletines llegaron de golpe<br>en 2022.</i>", 12.5,
         e.TINTA_2),
    ]
    for y, t, tam, color in lado:
        fig.add_annotation(text=t, xref="paper", yref="paper", x=0.80, y=y, xanchor="left", yanchor="top",
                           align="left", showarrow=False, font=dict(family=e.LETRA, size=tam, color=color))

    ancho = max(d.remesas_mdd.max(), d.ied_mdd.max()) / UNIDAD + 5
    fig.update_xaxes(visible=False, range=[-1.6, ancho], domain=[0, 0.78])
    fig.update_yaxes(visible=False, range=[-0.2, tope + 0.8], scaleanchor="x", scaleratio=1)
    return fig
