"""Equipo 5 · Dibujo que se adapta a la figura de "Treinta años aprendiendo".

No toca figures/5/treinta_anos/figura.py. Toma los puntos de la línea (los mismos datos de oro) y dibuja, como
capa de imagen de Plotly debajo de los datos, una colina y un camino que siguen esa línea, con palmas, letreros,
personas y una escuela. Si algo falla, la figura se muestra sin dibujo.

La geometría es fija: la figura mide 1100 x 640 px con márgenes l=80, r=150, t=30, b=70, ejes x 1997-2031 y
y 0-17.5. Con eso cada dato (año, grado) cae en un píxel conocido y el dibujo queda alineado.
"""
from __future__ import annotations

import base64

W, H = 1100, 640
L, R, T, B = 80, 150, 30, 70
PW, PH = W - L - R, H - T - B                      # área de la gráfica en px
X0, X1, Y0, Y1 = 1997.0, 2031.0, 0.0, 17.5         # rangos de los ejes de la figura
INK, SELVA, TRONCO = "#1d2a22", "#4f7a57", "#7a5a3c"
COLINA_1, COLINA_2, CAMINO = "#cfe2c0", "#b4d0a1", "#ecd49b"


TEXTURA = True   # textura de lápiz y papel sobre los dibujos; ponla en False para verlos lisos
_FILTRO = '<defs><filter id="tx" x="-4%" y="-4%" width="108%" height="108%" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="7" result="ond"/><feDisplacementMap in="SourceGraphic" in2="ond" scale="2.2" xChannelSelector="R" yChannelSelector="G" result="mano"/><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="3" result="grano"/><feColorMatrix in="grano" type="matrix" values="0 0 0 0 0.16  0 0 0 0 0.12  0 0 0 0 0.08  0 0 0 -3.4 1.3" result="puntos"/><feComposite in="puntos" in2="mano" operator="in" result="manchas"/><feTurbulence type="fractalNoise" baseFrequency="0.02 0.06" numOctaves="2" seed="11" result="veta"/><feColorMatrix in="veta" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1.1 0.58" result="luz"/><feComposite in="luz" in2="mano" operator="in" result="luces"/><feMerge><feMergeNode in="mano"/><feMergeNode in="luces"/><feMergeNode in="manchas"/></feMerge></filter></defs>'


def con_textura(svg: str) -> str:
    """Envuelve el dibujo en un filtro SVG: trazo con temblor de mano y granito de papel."""
    if not TEXTURA or 'id="tx"' in svg:
        return svg
    i = svg.index(">", svg.index("<svg")) + 1
    return svg[:i] + _FILTRO + '<g filter="url(#tx)">' + svg[i:svg.rindex("</svg>")] + "</g>" + svg[svg.rindex("</svg>"):]


def px(anio: float) -> float:
    return L + (anio - X0) / (X1 - X0) * PW


def py(valor: float) -> float:
    return T + (Y1 - valor) / (Y1 - Y0) * PH


def _suave(p: list[tuple[float, float]]) -> str:
    """Curva de Catmull-Rom que pasa por los puntos, como trazo SVG."""
    d = f"M{p[0][0]:.1f} {p[0][1]:.1f}"
    for i in range(len(p) - 1):
        p0, p1, p2, p3 = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, len(p) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def _y_en(p: list[tuple[float, float]], x: float) -> float:
    for (xa, ya), (xb, yb) in zip(p, p[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * (x - xa) / ((xb - xa) or 1)
    return p[0][1] if x < p[0][0] else p[-1][1]


def _palma(x, y, h=110):
    hojas = "".join(f'<path d="M0 0 Q{dx*.5} {-34-abs(dx)*.1} {dx} {dy}" fill="none" stroke="{SELVA}" stroke-width="8" stroke-linecap="round"/>'
                    for dx, dy in [(-62, 16), (-48, -16), (-20, -32), (20, -32), (48, -16), (62, 16)])
    return (f'<g transform="translate({x:.1f},{y:.1f})"><path d="M0 0 Q6 {-h/2} -2 {-h}" fill="none" stroke="{TRONCO}" '
            f'stroke-width="8" stroke-linecap="round"/><g transform="translate(-2,{-h})">{hojas}</g></g>')


CREMA, ARCILLA, OCRE, TIERRA = "#f4ead2", "#b36f43", "#d9b35c", "#7a5338"


def _alux(x, y, s=0.4, acc="", sombrero=True, brazo_der=(40, -48), flip=False):
    """Un alux (duende de la milpa) con los pies en (x, y). `acc` dibuja un accesorio en coordenadas del alux."""
    f = -1 if flip else 1
    hat = (f'<ellipse cx="0" cy="-129" rx="50" ry="11" fill="{OCRE}" stroke="{INK}" stroke-width="2.8"/>'
           f'<path d="M-28 -130 Q-26 -166 0 -168 Q26 -166 28 -130Z" fill="{OCRE}" stroke="{INK}" stroke-width="2.8"/>'
           f'<path d="M-28 -136 Q0 -128 28 -136 L28 -130 Q0 -122 -28 -130Z" fill="{SELVA}" stroke="{INK}" stroke-width="2"/>') if sombrero else ""
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s*f},{s})" stroke-linejoin="round" stroke-linecap="round">'
            f'<ellipse cx="0" cy="2" rx="34" ry="6" fill="#000" opacity=".12"/>'
            f'<ellipse cx="-13" cy="-5" rx="13" ry="7" fill="{TIERRA}" stroke="{INK}" stroke-width="2.4"/>'
            f'<ellipse cx="13" cy="-5" rx="13" ry="7" fill="{TIERRA}" stroke="{INK}" stroke-width="2.4"/>'
            f'<path d="M-27 -12 Q-30 -48 -21 -80 L21 -80 Q30 -48 27 -12 Q0 -4 -27 -12Z" fill="{CREMA}" stroke="{INK}" stroke-width="2.6"/>'
            f'<rect x="-24" y="-58" width="48" height="8" rx="3" fill="#b8472f" stroke="{INK}" stroke-width="2"/>'
            f'<line x1="-20" y1="-72" x2="-40" y2="-48" stroke="{ARCILLA}" stroke-width="10"/>'
            f'<line x1="20" y1="-72" x2="{brazo_der[0]}" y2="{brazo_der[1]}" stroke="{ARCILLA}" stroke-width="10"/>'
            f'<circle cx="-40" cy="-48" r="7" fill="{ARCILLA}" stroke="{INK}" stroke-width="2.2"/>'
            f'<circle cx="{brazo_der[0]}" cy="{brazo_der[1]}" r="7" fill="{ARCILLA}" stroke="{INK}" stroke-width="2.2"/>'
            f'<path d="M-30 -108 L-42 -128 L-24 -118Z" fill="{ARCILLA}" stroke="{INK}" stroke-width="2.4"/>'
            f'<path d="M30 -108 L42 -128 L24 -118Z" fill="{ARCILLA}" stroke="{INK}" stroke-width="2.4"/>'
            f'<circle cx="0" cy="-104" r="31" fill="{ARCILLA}" stroke="{INK}" stroke-width="2.8"/>'
            f'<circle cx="-11" cy="-106" r="7.5" fill="#fff" stroke="{INK}" stroke-width="2"/><circle cx="11" cy="-106" r="7.5" fill="#fff" stroke="{INK}" stroke-width="2"/>'
            f'<circle cx="-9" cy="-106" r="3.6" fill="{INK}"/><circle cx="13" cy="-106" r="3.6" fill="{INK}"/>'
            f'<path d="M-9 -90 Q0 -83 9 -90" fill="none" stroke="{INK}" stroke-width="2.6"/>'
            f'{hat}{acc}</g>')


AZADON = (f'<line x1="40" y1="-44" x2="58" y2="-140" stroke="{TIERRA}" stroke-width="6"/>'
          f'<path d="M50 -140 L78 -146 L74 -128 L58 -126Z" fill="#9aa39c" stroke="{INK}" stroke-width="2.6"/>')
MOCHILA = f'<rect x="-44" y="-78" width="22" height="38" rx="6" fill="#2f6f8a" stroke="{INK}" stroke-width="2.6"/>'
BIRRETE = (f'<path d="M-34 -128 L0 -142 L34 -128 L0 -114Z" fill="{INK}" stroke="{INK}" stroke-width="2"/>'
           f'<rect x="-20" y="-124" width="40" height="12" fill="{INK}"/><path d="M34 -128 L40 -108" stroke="{OCRE}" stroke-width="3"/>'
           f'<circle cx="40" cy="-106" r="4" fill="{OCRE}"/>')
DIPLOMA = (f'<rect x="30" y="-62" width="36" height="12" rx="6" fill="#f4ead2" stroke="{INK}" stroke-width="2.4" transform="rotate(-25 48 -56)"/>'
           f'<rect x="44" y="-64" width="6" height="16" fill="#b8472f" transform="rotate(-25 48 -56)"/>')
MALETIN = (f'<path d="M34 -66 q10 -12 20 0" fill="none" stroke="{INK}" stroke-width="3.4"/>'
           f'<rect x="24" y="-64" width="46" height="32" rx="4" fill="{TIERRA}" stroke="{INK}" stroke-width="2.8"/>'
           f'<rect x="44" y="-52" width="6" height="8" fill="{OCRE}" stroke="{INK}" stroke-width="1.6"/>')


def _libros(x, y, alturas=(16, 32, 48)):
    """Escalera de libros: la última columna es la más alta."""
    colores = ("#b8472f", "#2f6f8a", "#d9b35c")
    return "".join(f'<rect x="{x + i * 34:.1f}" y="{y - h:.1f}" width="34" height="{h}" fill="{colores[i % 3]}" stroke="{INK}" stroke-width="2.4"/>'
                   f'<rect x="{x + i * 34 + 4:.1f}" y="{y - h + 5:.1f}" width="26" height="4" fill="#fff" opacity=".55"/>' for i, h in enumerate(alturas))


def _moneda(x, y, r=8):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#f1c84b" stroke="{INK}" stroke-width="2"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r/2.2:.1f}" fill="none" stroke="{INK}" stroke-width="1.4" opacity=".6"/>')


def _retono(x, y, h):
    return (f'<g transform="translate({x:.1f},{y:.1f})" fill="none" stroke-linecap="round"><path d="M0 0 L0 {-h}" stroke="{SELVA}" stroke-width="4"/>'
            f'<path d="M0 {-h*.6} q-14 -6 -18 -16 q12 -2 18 16 M0 {-h*.85} q14 -6 18 -16 q-12 -2 -18 16" fill="{SELVA}" stroke="{INK}" stroke-width="1.6"/></g>')


def _letrero(x, y):
    return (f'<g transform="translate({x:.1f},{y:.1f})" stroke="{INK}" stroke-width="2.4" fill="#f1e2b8" stroke-linejoin="round">'
            f'<path d="M0 0 L0 -40" fill="none"/><path d="M0 -38 L24 -38 L31 -32 L24 -26 L0 -26Z"/></g>')



# ======================================================================================================== detalles
# Pasto, rocas, henequén y construcciones con textura dibujada (no solo filtro). Todo es determinista (semillas fijas).
import random

_gid = [0]


def _grad(c1: str, c2: str, horizontal: bool = False):
    """Degradado lineal; devuelve (definición, referencia). Los ids no se repiten dentro de un mismo SVG."""
    _gid[0] += 1
    i = f"dg{_gid[0]}"
    a = 'x2="1" y2="0"' if horizontal else 'x2="0" y2="1"'
    return f'<defs><linearGradient id="{i}" x1="0" y1="0" {a}><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>', f"url(#{i})"


_VERDES = ["#2f5d3a", "#3f7a3a", "#5c9a45", "#86b958"]


def _pasto(x, y, ancho, n=6, semilla=1, flores=True, alto=1.0):
    """Matas de pasto (varias hojas curvas por mata) y, de vez en cuando, una florecita."""
    r = random.Random(semilla)
    out = []
    for i in range(n):
        bx = x - ancho / 2 + ancho * (i + r.random() * 0.8) / n
        hb = r.uniform(9, 21) * alto
        for _ in range(r.randint(3, 6)):
            ang, h = r.uniform(-0.75, 0.75), hb * r.uniform(0.65, 1.2)
            tx, ty = bx + ang * h, y - h
            out.append(f'<path d="M{bx:.1f} {y:.1f} Q{bx + ang * h * .3 + r.uniform(-3, 3):.1f} {y - h * .6:.1f} {tx:.1f} {ty:.1f}" '
                       f'fill="none" stroke="{r.choice(_VERDES)}" stroke-width="{r.uniform(1.5, 2.8):.1f}" stroke-linecap="round"/>')
        if flores and r.random() < 0.2:
            fx, fy = bx + r.uniform(-6, 6), y - hb * 1.25
            col = r.choice(["#f4d35e", "#ffffff", "#e8833a", "#d96c8a"])
            out.append(f'<path d="M{bx:.1f} {y:.1f} Q{bx:.1f} {y - hb:.1f} {fx:.1f} {fy:.1f}" fill="none" stroke="#3f7a3a" stroke-width="1.5"/>'
                       f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="3" fill="{col}" stroke="{INK}" stroke-width="0.8"/>')
    return "".join(out)


def _roca(x, y, s=1.0, semilla=1, musgo=True):
    """Roca con volumen: degradado, luz arriba a la izquierda, grietas, sombra y un poco de musgo."""
    r = random.Random(semilla)
    j = lambda v: v + r.uniform(-2.5, 2.5)
    pts = [(-24, 0), (-27, -9), (-17, -21), (2, -26), (19, -20), (27, -8), (23, 0)]
    d = "M" + " L".join(f"{j(px_):.1f} {j(py_):.1f}" for px_, py_ in pts) + "Z"
    defs, fill = _grad("#c9c3b2", "#8d8878")
    luz = f'<path d="M-18 -9 L-11 -19 L2 -22 L-4 -13Z" fill="#e9e4d4" opacity=".7"/>'
    grietas = f'<path d="M6 -22 L3 -13 L8 -8 M-12 -6 L-6 -2" fill="none" stroke="#5d594d" stroke-width="1.4" stroke-linecap="round"/>'
    mus = (f'<path d="M-22 -8 q4 -8 12 -9 q-4 4 -2 9Z" fill="#6aa163" opacity=".85"/>' if musgo and r.random() < .7 else "")
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})">{defs}<ellipse cx="2" cy="2" rx="30" ry="5" fill="#000" opacity=".16"/>'
            f'<path d="{d}" fill="{fill}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>{luz}{grietas}{mus}</g>')


def _piedritas(x, y, ancho, n=8, semilla=2):
    r = random.Random(semilla)
    return "".join(f'<ellipse cx="{x + r.uniform(-ancho / 2, ancho / 2):.1f}" cy="{y + r.uniform(-3, 4):.1f}" rx="{r.uniform(2, 4.4):.1f}" ry="{r.uniform(1.4, 2.6):.1f}" '
                   f'fill="{r.choice(["#b9b3a0", "#9d978a", "#d4cdb8"])}" stroke="#5d594d" stroke-width="0.8"/>' for _ in range(n))


def _henequen(x, y, s=1.0, semilla=3):
    """Henequén (agave): rosetas de hojas largas y puntiagudas, la planta de Yucatán."""
    r = random.Random(semilla)
    defs, fill = _grad("#8fc08a", "#3f7a5a")
    hojas = []
    for ang in sorted([-78, -58, -38, -18, 2, 22, 42, 62, 80]):
        a = ang + r.uniform(-4, 4)
        L = r.uniform(52, 72)
        import math
        tx, ty = math.sin(math.radians(a)) * L * 0.9, -math.cos(math.radians(a)) * L
        cx_, cy_ = math.sin(math.radians(a)) * L * 0.35, -math.cos(math.radians(a)) * L * 0.55
        nx, ny = math.cos(math.radians(a)) * 6, math.sin(math.radians(a)) * 6
        hojas.append(f'<path d="M{-nx:.1f} {ny:.1f} Q{cx_ - nx * 1.8:.1f} {cy_ + ny * 1.8:.1f} {tx:.1f} {ty:.1f} Q{cx_ + nx * 1.8:.1f} {cy_ - ny * 1.8:.1f} {nx:.1f} {-ny:.1f}Z" '
                     f'fill="{fill}" stroke="{INK}" stroke-width="1.8" stroke-linejoin="round"/>'
                     f'<path d="M0 -4 Q{cx_:.1f} {cy_:.1f} {tx * .92:.1f} {ty * .92:.1f}" fill="none" stroke="#d7ecc9" stroke-width="1.3" opacity=".7"/>')
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({s})">{defs}<ellipse cx="0" cy="2" rx="26" ry="5" fill="#000" opacity=".14"/>{"".join(hojas)}</g>'


def _techo_palma(ancho=124, semilla=5):
    """Techo de palma por capas, con hebras claras y oscuras y flecos en el borde."""
    r = random.Random(semilla)
    defs, fill = _grad("#e0c36e", "#a9823a")
    forma = f"M{-ancho} -70 Q{-ancho + 14} -150 0 -168 Q{ancho - 14} -150 {ancho} -70 Q{ancho / 2} -92 0 -92 Q{-ancho / 2} -92 {-ancho} -70Z"
    hebras = ""
    for i in range(-15, 16):
        x0 = i * ancho / 15
        col, w = (("#7d5d22", 1.7) if i % 2 else ("#f1dc9a", 1.3))
        hebras += (f'<path d="M{x0 * .42:.1f} {-158 + abs(i) * 0.9:.1f} Q{x0 * .85:.1f} {-122 + r.uniform(-4, 4):.1f} {x0 * 1.02:.1f} {-84 + abs(i) * 0.9:.1f}" '
                   f'fill="none" stroke="{col}" stroke-width="{w}" opacity=".7" stroke-linecap="round"/>')
    flecos = "".join(f'<path d="M{x0:.1f} {-88 + (abs(x0) / ancho) ** 2 * 18:.1f} l2.4 9 l2.4 -9" fill="#a9823a" stroke="{INK}" stroke-width="1.1"/>'
                     for x0 in [(-ancho * .93) + k * (ancho * 1.86 / 16) for k in range(17)])
    capas = f'<path d="M{-ancho * .8:.1f} -112 Q0 -132 {ancho * .8:.1f} -112" fill="none" stroke="#7d5d22" stroke-width="2" opacity=".5"/>' \
            f'<path d="M{-ancho * .9:.1f} -96 Q0 -112 {ancho * .9:.1f} -96" fill="none" stroke="#7d5d22" stroke-width="2" opacity=".5"/>'
    return f'{defs}<path d="{forma}" fill="{fill}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>{hebras}{capas}{flecos}'


def _casa_barro(x, y, s=0.62):
    """Casa maya de barro: base de piedra, pared de bajareque con grietas, puerta de madera y techo de palma."""
    r = random.Random(9)
    defs, pared = _grad("#ecd9b0", "#cdb386")
    piedras = ""
    px_ = -100
    while px_ < 98:
        w = r.uniform(14, 24)
        piedras += (f'<rect x="{px_:.1f}" y="{-20 + r.uniform(-1, 1):.1f}" width="{w - 2:.1f}" height="{r.uniform(15, 19):.1f}" rx="5" '
                    f'fill="{r.choice(["#a99b86", "#bbae98", "#948773"])}" stroke="{INK}" stroke-width="1.6"/>')
        px_ += w
    manchas = "".join(f'<path d="M{r.uniform(-90, 90):.1f} {r.uniform(-76, -30):.1f} l{r.uniform(8, 22):.1f} {r.uniform(-1, 1):.1f}" stroke="#b29a6c" stroke-width="2" stroke-linecap="round" opacity=".6"/>' for _ in range(16))
    grietas = f'<path d="M62 -84 L58 -66 L66 -52 L60 -36" fill="none" stroke="#7d6a48" stroke-width="2" stroke-linecap="round"/><path d="M-70 -80 L-66 -64 L-72 -50" fill="none" stroke="#7d6a48" stroke-width="2" stroke-linecap="round"/>'
    puerta = (f'<rect x="-17" y="-66" width="34" height="48" rx="3" fill="#2c2a26" stroke="{INK}" stroke-width="3"/>'
              f'<rect x="-21" y="-70" width="42" height="7" fill="#8a5a38" stroke="{INK}" stroke-width="2"/>'
              f'<path d="M-20 -62 L-20 -18 M20 -62 L20 -18" stroke="#8a5a38" stroke-width="4"/>')
    ventana = (f'<rect x="52" y="-60" width="26" height="22" fill="#2c2a26" stroke="{INK}" stroke-width="2.4"/>'
               f'<path d="M65 -60 L65 -38 M52 -49 L78 -49" stroke="#8a5a38" stroke-width="3"/>')
    pasto = _pasto(0, -1, 230, 12, semilla=4)
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" stroke-linejoin="round">{defs}'
            f'<ellipse cx="0" cy="4" rx="128" ry="9" fill="#000" opacity=".12"/>'
            f'<path d="M-100 -2 L-100 -70 Q-100 -86 -80 -86 L80 -86 Q100 -86 100 -70 L100 -2Z" fill="{pared}" stroke="{INK}" stroke-width="3.6"/>'
            f'{manchas}{grietas}{piedras}{puerta}{ventana}{_techo_palma()}{pasto}</g>')


def _casa_buena(x, y, s=0.62):
    """Casa moderna de dos pisos con voladizo: ventanales de vidrio, paneles solares, madera, tinaco e internet."""
    d_muro, muro = _grad("#fbfaf4", "#dedacd")
    d_vid, vidrio = _grad("#d6eef6", "#7fb6cc")
    d_vid2, vidrio2 = _grad("#bfe0ec", "#6aa6bf")
    d_pan, panel = _grad("#3d5a8a", "#1f3358")
    tablas = "".join(f'<line x1="{xx}" y1="-60" x2="{xx}" y2="-2" stroke="#8a5a30" stroke-width="1.3"/>' for xx in range(-68, -42, 5))
    reflejo = lambda x0, y0, w, h: (f'<path d="M{x0 + w * .15} {y0 + h} L{x0 + w * .45} {y0} L{x0 + w * .6} {y0} L{x0 + w * .3} {y0 + h}Z" fill="#fff" opacity=".45"/>'
                                    f'<path d="M{x0 + w * .68} {y0 + h} L{x0 + w * .84} {y0} L{x0 + w * .9} {y0} L{x0 + w * .74} {y0 + h}Z" fill="#fff" opacity=".3"/>')
    paneles = "".join(f'<path d="M{xx} -122 l16 0 l5 -14 l-16 0Z" fill="{panel}" stroke="{INK}" stroke-width="1.8"/>'
                      f'<path d="M{xx + 5} -122 l5 -14 M{xx + 11} -122 l5 -14" stroke="#9fb6dc" stroke-width="0.9"/>' for xx in (-8, 12, 32))
    arbustos = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" stroke="{INK}" stroke-width="1.6"/>'
                       for cx, cy, r, col in ((-76, -6, 9, "#4f8a4a"), (-70, -11, 7, "#6aa163"), (74, -6, 9, "#4f8a4a"), (80, -3, 6, "#86b958")))
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" stroke-linejoin="round">{d_muro}{d_vid}{d_vid2}{d_pan}'
            f'<circle cx="0" cy="-52" r="92" fill="#ffd978" opacity=".26"/><ellipse cx="0" cy="4" rx="100" ry="8" fill="#000" opacity=".13"/>'
            # planta baja y piso alto (voladizo hacia la derecha)
            f'<rect x="-72" y="-62" width="144" height="62" fill="{muro}" stroke="{INK}" stroke-width="3.2"/>'
            f'<rect x="-72" y="-62" width="30" height="62" fill="#c98a52" stroke="{INK}" stroke-width="2.6"/>{tablas}'
            f'<rect x="-28" y="-114" width="108" height="52" fill="{muro}" stroke="{INK}" stroke-width="3.2"/>'
            # ventanales
            f'<rect x="-34" y="-54" width="58" height="48" fill="{vidrio}" stroke="{INK}" stroke-width="3"/>'
            f'<path d="M-5 -54 L-5 -6 M-34 -30 L24 -30" stroke="{INK}" stroke-width="2.2"/>{reflejo(-34, -54, 58, 48)}'
            f'<rect x="-12" y="-104" width="84" height="32" fill="{vidrio2}" stroke="{INK}" stroke-width="3"/>'
            f'<path d="M16 -104 L16 -72 M44 -104 L44 -72" stroke="{INK}" stroke-width="2.2"/>{reflejo(-12, -104, 84, 32)}'
            f'<rect x="-12" y="-72" width="84" height="3" fill="{INK}"/><path d="M-6 -72 L-6 -62 M16 -72 L16 -62 M38 -72 L38 -62 M60 -72 L60 -62" stroke="{INK}" stroke-width="1.6"/>'
            # puerta, lámpara y número
            f'<rect x="34" y="-50" width="26" height="50" fill="#3b3f45" stroke="{INK}" stroke-width="3"/><rect x="38" y="-46" width="5" height="34" fill="#5a6068"/>'
            f'<circle cx="55" cy="-24" r="2.4" fill="#e0c070"/><circle cx="66" cy="-42" r="3.4" fill="#ffe08a" stroke="{INK}" stroke-width="1.2"/>'
            # techos planos con alero, paneles solares, tinaco y antena
            f'<rect x="-80" y="-68" width="68" height="6" fill="#4a4f55" stroke="{INK}" stroke-width="2.4"/>'
            f'<rect x="-36" y="-120" width="124" height="7" fill="#4a4f55" stroke="{INK}" stroke-width="2.6"/>{paneles}'
            f'<rect x="-60" y="-96" width="22" height="26" rx="10" fill="#6fb6d8" stroke="{INK}" stroke-width="2.4"/><rect x="-60" y="-96" width="22" height="6" rx="3" fill="#fff" opacity=".45"/>'
            f'<path d="M-49 -70 L-49 -62" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M80 -120 L80 -142 M80 -142 l-7 6 M80 -142 l7 6" stroke="{INK}" stroke-width="2.4" fill="none"/>'
            f'<path d="M68 -152 q12 -10 24 0" fill="none" stroke="{SELVA}" stroke-width="2.8"/><path d="M62 -160 q18 -16 36 0" fill="none" stroke="{SELVA}" stroke-width="2.4"/>'
            f'{arbustos}{_pasto(0, -1, 160, 8, semilla=6)}</g>')


def _escuela(x, y, s=1.0):
    """Escuela de ladrillo con techo de teja, ventanas con vidrio, reloj, puerta y bandera."""
    defs, muro = _grad("#f0dcc0", "#d3b998")
    ladrillos = "".join(f'<line x1="-30" y1="{yy}" x2="30" y2="{yy}" stroke="#b59a79" stroke-width="1"/>' for yy in range(-38, 0, 7))
    ladrillos += "".join(f'<line x1="{xx}" y1="{yy}" x2="{xx}" y2="{yy + 7}" stroke="#b59a79" stroke-width="1"/>'
                         for k, yy in enumerate(range(-44, -2, 7)) for xx in range(-30 + (6 if k % 2 else 0), 30, 12))
    tejas = "".join(f'<path d="M{-37 + k * 6.2:.1f} -44 q3 5 6 0" fill="none" stroke="#7d2f22" stroke-width="1.3"/>' for k in range(12))
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" stroke-linejoin="round" stroke="{INK}" stroke-width="2.6">{defs}'
            f'<ellipse cx="0" cy="3" rx="42" ry="5" fill="#000" stroke="none" opacity=".13"/>'
            f'<rect x="-30" y="-44" width="60" height="44" fill="{muro}"/><g stroke="none">{ladrillos}</g>'
            f'<path d="M-38 -44 L0 -72 L38 -44Z" fill="#c4614a"/><g stroke="none">{tejas}</g><circle cx="0" cy="-56" r="5.5" fill="#fff" stroke-width="1.8"/>'
            f'<path d="M0 -56 L0 -59 M0 -56 L2.4 -55" stroke-width="1.2"/>'
            f'<rect x="-26" y="-34" width="14" height="12" fill="#9fc5d6" stroke-width="2"/><rect x="12" y="-34" width="14" height="12" fill="#9fc5d6" stroke-width="2"/>'
            f'<rect x="-7" y="-26" width="14" height="26" fill="#8a5a38"/><rect x="-10" y="-2" width="20" height="3" fill="#bdb5a0" stroke-width="1.4"/>'
            f'<line x1="0" y1="-72" x2="0" y2="-90"/><path d="M0 -90 l16 5 l-16 5Z" fill="{OCRE}" stroke-width="1.6"/>'
            f'{_pasto(0, 0, 80, 5, semilla=8, flores=False)}</g>')


# ============================================================================================ ambiente (cielo y árboles)
import math


def _nube(x, y, w=150.0):
    """Nube con contorno solo por fuera (se dibuja el borde grueso y luego el relleno blanco encima)."""
    forma = (f'<circle cx="{-.30 * w:.1f}" cy="{-.02 * w:.1f}" r="{.15 * w:.1f}"/><circle cx="{-.10 * w:.1f}" cy="{-.12 * w:.1f}" r="{.20 * w:.1f}"/>'
             f'<circle cx="{.14 * w:.1f}" cy="{-.14 * w:.1f}" r="{.21 * w:.1f}"/><circle cx="{.34 * w:.1f}" cy="{-.02 * w:.1f}" r="{.16 * w:.1f}"/>'
             f'<rect x="{-.42 * w:.1f}" y="{-.04 * w:.1f}" width="{.86 * w:.1f}" height="{.14 * w:.1f}" rx="{.07 * w:.1f}"/>')
    return (f'<g transform="translate({x:.1f},{y:.1f})"><g fill="#c3d0d8" stroke="#c3d0d8" stroke-width="5">{forma}</g>'
            f'<g fill="#ffffff">{forma}</g><ellipse cx="{.02 * w:.1f}" cy="{.07 * w:.1f}" rx="{.34 * w:.1f}" ry="{.035 * w:.1f}" fill="#dce8ee"/></g>')


def _sol(x, y, r=34.0):
    defs, fill = _grad("#fff0a6", "#f4b93a")
    rayos = "".join(f'<line x1="{math.cos(a) * r * 1.25:.1f}" y1="{math.sin(a) * r * 1.25:.1f}" x2="{math.cos(a) * r * 1.62:.1f}" y2="{math.sin(a) * r * 1.62:.1f}" '
                    f'stroke="#f2b632" stroke-width="3.2" stroke-linecap="round"/>' for a in [k * math.pi / 6 for k in range(12)])
    return (f'<g transform="translate({x:.1f},{y:.1f})">{defs}<circle r="{r * 1.9:.1f}" fill="#ffe9a0" opacity=".28"/>{rayos}'
            f'<circle r="{r:.1f}" fill="{fill}" stroke="#e0a02a" stroke-width="2.4"/><circle cx="{-r * .3:.1f}" cy="{-r * .3:.1f}" r="{r * .35:.1f}" fill="#fff" opacity=".35"/></g>')


def _pajaros(x, y, s=1.0):
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round">'
            f'<path d="M0 0 q7 -8 14 0 q7 -8 14 0"/><path d="M34 -16 q6 -7 12 0 q6 -7 12 0"/><path d="M-14 -22 q5 -6 10 0 q5 -6 10 0"/></g>')


def _mariposa(x, y, s=1.0, c1="#e8833a", c2="#f4d35e"):
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" stroke="{INK}" stroke-width="1.4" stroke-linejoin="round">'
            f'<path d="M0 0 Q-14 -16 -16 -4 Q-14 8 0 3Z" fill="{c1}"/><path d="M0 0 Q14 -16 16 -4 Q14 8 0 3Z" fill="{c1}"/>'
            f'<path d="M0 3 Q-9 14 -5 9 Q-2 6 0 3Z" fill="{c2}"/><path d="M0 3 Q9 14 5 9 Q2 6 0 3Z" fill="{c2}"/>'
            f'<circle cx="-9" cy="-4" r="2" fill="#fff" stroke="none"/><circle cx="9" cy="-4" r="2" fill="#fff" stroke="none"/>'
            f'<path d="M0 -4 L0 8 M0 -4 Q-3 -10 -6 -11 M0 -4 Q3 -10 6 -11" fill="none"/></g>')


def _ceiba(x, y, s=1.0):
    """Ceiba, el árbol sagrado maya: tronco con raíces tablares y espinas, copa ancha de varias capas."""
    d1, tronco = _grad("#b79b78", "#7d6648", True)
    d2, copa = _grad("#7fb96a", "#3f7a3a")
    d3, copa2 = _grad("#5c9a45", "#2f5d3a")
    espinas = "".join(f'<path d="M{xx:.1f} {yy:.1f} l2 -4 l2 4" fill="#5d4a33"/>' for xx, yy in [(-6, -40), (4, -52), (-3, -66), (6, -78), (-5, -90), (2, -30)])
    bolas1 = "".join(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{copa2}" stroke="{INK}" stroke-width="2"/>' for cx, cy, rr in
                     [(-46, -112, 26), (-20, -128, 30), (16, -132, 32), (46, -116, 27), (0, -108, 30)])
    bolas2 = "".join(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{copa}" stroke="{INK}" stroke-width="1.8"/>' for cx, cy, rr in
                     [(-34, -126, 20), (8, -142, 22), (36, -128, 20), (-8, -118, 21)])
    luces = "".join(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#c9e8a8" opacity=".6"/>' for cx, cy in [(-40, -134), (2, -150), (30, -138), (-16, -124)])
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" stroke-linejoin="round">{d1}{d2}{d3}<ellipse cx="0" cy="4" rx="50" ry="6" fill="#000" opacity=".14"/>'
            f'<path d="M-22 2 Q-10 -14 -8 -40 L-9 -100 L9 -100 L8 -40 Q10 -14 24 2Z" fill="{tronco}" stroke="{INK}" stroke-width="2.6"/>{espinas}'
            f'{bolas1}{bolas2}{luces}</g>')


def _monte(cresta, seed=12):
    """Silueta del monte (selva baja) detrás de las colinas: copas redondas oscuras sobre la cresta."""
    r = random.Random(seed)
    d, c = _grad("#6a9c63", "#4d7f4f")
    out = d
    x0 = cresta[0][0]
    while x0 < cresta[-1][0]:
        out += f'<circle cx="{x0:.1f}" cy="{_y_en(cresta, x0) - 18 + r.uniform(-4, 4):.1f}" r="{r.uniform(15, 27):.1f}" fill="{c}" opacity=".85"/>'
        x0 += r.uniform(16, 30)
    return out


def svg_treinta_anos(anios: list[float], valores: list[float]) -> str:
    """Historia de izquierda a derecha: del trabajo en la milpa a la escuela, el título y el empleo."""
    pts = [(px(a), py(v)) for a, v in zip(anios, valores)]
    if len(pts) < 2:
        raise ValueError("faltan puntos")
    base = T + PH                                                         # eje x
    tope = base - 14
    # Colina y camino siguen la línea de datos, por debajo de ella (los rótulos y la línea quedan libres).
    colina = [(L, min(pts[0][1] + 112, tope))] + [(x, min(y + 112, tope)) for x, y in pts] + [(L + PW, min(pts[-1][1] + 112, tope))]
    colina2 = [(x, min(y + 38, base - 6)) for x, y in colina]
    camino = [(x, min(y + 88, tope - 4)) for x, y in colina[:]]
    camino = [(x, min(yc, yh + 26)) for (x, yc), (_, yh) in zip(camino, colina)]
    cuerpo = (f'<path d="{_suave(colina)} L{L+PW} {base} L{L} {base}Z" fill="{COLINA_1}"/>'
              f'<path d="{_suave(colina2)} L{L+PW} {base} L{L} {base}Z" fill="{COLINA_2}"/>'
              f'<path d="{_suave(camino)}" fill="none" stroke="{CAMINO}" stroke-width="20" stroke-linecap="round"/>'
              f'<path d="{_suave(camino)}" fill="none" stroke="#fffaf0" stroke-width="2.3" stroke-dasharray="12 11"/>')

    def frac(f):
        return pts[0][0] + (pts[-1][0] - pts[0][0]) * f

    def suelo(x):                                                         # y del camino en x
        return _y_en(camino, x) - 2

    # Detalle: pasto sobre las dos colinas, piedritas y rocas junto al camino, henequén
    detalle = ""
    for k, xg in enumerate(range(L + 6, L + PW - 10, 46)):
        detalle += _pasto(xg, _y_en(colina, xg) + 5, 40, 3, semilla=100 + k)
        detalle += _pasto(xg + 22, _y_en(colina2, xg + 22) + 6, 40, 2, semilla=300 + k, flores=False)
    for k, xr in enumerate((frac(.17), frac(.52), frac(.83), frac(1.0) + 40)):
        detalle += _roca(xr, _y_en(camino, xr) + 22, 0.62 + 0.12 * (k % 2), semilla=k + 2)
    for k, xr in enumerate((frac(.08), frac(.30), frac(.6), frac(.92))):
        detalle += _piedritas(xr, _y_en(camino, xr) + 15, 40, 7, semilla=50 + k)
    for k, xr in enumerate((frac(.0) + 20, frac(.58))):
        detalle += _henequen(xr, _y_en(colina, xr) + 8, 0.52, semilla=k + 1)
    # Franja de tierra abajo (corte del terreno) con piedritas y raíces, y pasto repartido por la colina
    r_ = random.Random(21)
    onda = [(L + k * 40, base - 26 + r_.uniform(-3, 3)) for k in range(int(PW / 40) + 2)]
    onda = [(min(x, L + PW), y) for x, y in onda]
    defs_t, rel_t = _grad("#9a7149", "#6f4f31")
    detalle += (f'{defs_t}<path d="{_suave(onda)} L{L + PW} {base} L{L} {base}Z" fill="{rel_t}"/>'
                f'<path d="{_suave(onda)}" fill="none" stroke="#5b3f26" stroke-width="2.4"/>')
    for k in range(34):
        xx, yy = r_.uniform(L + 8, L + PW - 8), r_.uniform(base - 20, base - 4)
        detalle += f'<ellipse cx="{xx:.1f}" cy="{yy:.1f}" rx="{r_.uniform(2.5, 6):.1f}" ry="{r_.uniform(1.8, 3.6):.1f}" fill="{r_.choice(["#c9b99a", "#a89677", "#d8cbb0"])}" stroke="#5b3f26" stroke-width="0.9"/>'
    for k in range(18):
        xx = r_.uniform(L + 10, L + PW - 10)
        detalle += f'<path d="M{xx:.1f} {base - 26:.1f} q{r_.uniform(-8, 8):.1f} 12 {r_.uniform(-12, 12):.1f} {r_.uniform(18, 24):.1f}" fill="none" stroke="#e8d8b8" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>'
    for k in range(26):
        xg = r_.uniform(L + 6, L + PW - 6)
        detalle += _pasto(xg, min(base - 28, _y_en(colina2, xg) + r_.uniform(14, 90)), 34, 2, semilla=500 + k, flores=k % 4 == 0)
    cuerpo += detalle

    # 1. Origen: trabajo en la milpa, choza de palma
    x1 = frac(.03) + 38
    cuerpo += _casa_barro(x1 - 8, _y_en(colina, x1 - 8) + 6) + "".join(_retono(x1 + 58 + i * 16, suelo(x1 + 58) + 2, 16 + i * 5) for i in range(3))
    cuerpo += _alux(x1 + 118, suelo(x1 + 118), 0.40, AZADON)
    # 2. Camino a la escuela: mochila y escuelita
    x2 = frac(.34)
    cuerpo += _alux(x2, suelo(x2), 0.40, MOCHILA, flip=True) + _escuela(x2 + 78, _y_en(colina, x2 + 78) + 4, 0.78)
    # 3. Estudiar: escalera de libros, birrete y diploma
    x3 = frac(.66)
    base3 = suelo(x3 + 30)
    cuerpo += _libros(x3 - 4, base3 + 2) + _alux(x3 + 98, base3 + 2 - 48, 0.40, BIRRETE + DIPLOMA, sombrero=False)
    # 4. Resultado: empleo (maletín), casa con luz y monedas
    x4 = pts[-1][0] + 8
    cuerpo += _casa_buena(min(x4 + 82, L + PW - 48), _y_en(colina, x4 + 82) + 6, 0.55)
    cuerpo += _alux(x4 + 8, suelo(x4 + 8), 0.40, MALETIN)
    cuerpo += "".join(_moneda(x4 + 40 + i * 20, suelo(x4 + 40) + 22 - (i % 2) * 8) for i in range(3))
    # Ambiente: cielo (sol, nubes, pájaros) y monte detrás de todo; mariposas sobre el pasto
    cielo = (_sol(L + PW - 78, T + 70, 30) + _nube(L + 150, T + 66, 150) + _nube(L + 440, T + 112, 120) + _nube(L + 610, T + 54, 130)
             + _pajaros(L + 300, T + 160, 1.0) + _pajaros(L + 580, T + 150, .8) + _pajaros(L + 700, T + 175, .9))
    monte = _monte([(L, colina[0][1] - 4)] + [(x, y - 4) for x, y in colina[1:]])
    cuerpo = cielo + monte + cuerpo
    cuerpo += (_mariposa(frac(.22), _y_en(colina, frac(.22)) - 26, 1.1) + _mariposa(frac(.7), _y_en(colina, frac(.7)) - 34, 1.0, "#d96c8a", "#f4d35e")
               + _mariposa(frac(.97), _y_en(colina, frac(.97)) - 30, .9, "#6fb6d8", "#ffffff"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" preserveAspectRatio="none">'
            f'<defs><clipPath id="m"><rect x="{L}" y="{T}" width="{PW}" height="{PH}"/></clipPath></defs>'
            f'<g clip-path="url(#m)">{cuerpo}</g></svg>')


def decorar_treinta(fig) -> None:
    """Agrega el dibujo como capa de imagen debajo de los datos. Usa los puntos de la línea de la propia figura."""
    traza = next(t for t in fig.data if getattr(t, "mode", None) and "lines" in t.mode)
    anios, valores = list(map(float, traza.x)), list(map(float, traza.y))
    uri = "data:image/svg+xml;base64," + base64.b64encode(con_textura(svg_treinta_anos(anios, valores)).encode("utf-8")).decode("ascii")
    fig.add_layout_image(dict(
        source=uri, xref="paper", yref="paper", x=-L / PW, y=1 + T / PH, sizex=W / PW, sizey=H / PH,
        xanchor="left", yanchor="top", sizing="stretch", layer="below", opacity=1))


# ====================================================================================================== las otras tres
# Mismo método que "treinta_anos": el dibujo va como capa de imagen de Plotly, pegado a los elementos de la gráfica.
# Cada figura mide 1100 px de ancho con los márgenes de GEOM; con eso cada elemento cae en un píxel conocido.
from pathlib import Path

PIEZAS = Path(__file__).resolve().parents[1] / "assets" / "5" / "piezas"
# nombre: (ancho del dibujo, alto, pad) en unidades del SVG; pad = lo que sobra bajo el punto de apoyo
_META = {"alux_sankey": (100, 126, 14), "escuela": (96, 104, 8), "casa_palma": (264, 196, 18),
         "casa_moderna": (200, 182, 14), "alux_foco": (200, 196, 18), "alux_riega": (200, 178, 26)}
GEOM = {  # tamaño de la figura en la página y márgenes (px)
    "lo_que_se_invirtio": dict(h=640, l=30, r=60, t=70, b=30),
    "la_casa_cambio": dict(h=700, l=170, r=60, t=140, b=130),
    "pobreza_rezago": dict(h=720, l=80, r=60, t=30, b=120),
}


def _pieza_uri(nombre: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode((PIEZAS / f"{nombre}.svg").read_bytes()).decode("ascii")


def _poner(fig, g: dict, nombre: str, cx: float, y_suelo: float, ancho: float, anclaje: str = "bottom") -> None:
    """Pone una pieza centrada en x=cx con su punto de apoyo en y=y_suelo (px de la figura, desde arriba)."""
    w, h, pad = _META[nombre]
    k = ancho / w
    pw, ph = W - g["l"] - g["r"], g["h"] - g["t"] - g["b"]
    fig.add_layout_image(dict(
        source=_pieza_uri(nombre), xref="paper", yref="paper",
        x=(cx - g["l"]) / pw, y=1 - (y_suelo + pad * k - g["t"]) / ph, sizex=ancho / pw, sizey=h * k / ph,
        xanchor="center", yanchor=anclaje, sizing="contain", layer="below", opacity=1))



def _suelo(y0, y1, w=W, semilla=21):
    """Franja de pasto con tierra abajo, matas, florecitas y piedritas; ocupa de y0 a y1 en todo el ancho."""
    r = random.Random(semilla)
    d1, verde = _grad("#9cc47a", "#6aa163")
    d2, tierra = _grad("#a9805a", "#7a5738")
    onda = " ".join(f"L{x} {y0 + r.uniform(-3, 3):.1f}" for x in range(0, int(w) + 30, 30))
    cuerpo = (d1 + d2 + f'<path d="M0 {y0 + 6} {onda} L{w} {y1} L0 {y1}Z" fill="{verde}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>'
              f'<rect x="0" y="{y1 - 9}" width="{w}" height="9" fill="{tierra}"/>')
    cuerpo += _piedritas(w / 2, y1 - 4, w * .96, int(w / 24), semilla + 1)
    cuerpo += _pasto(w / 2, y0 + 8, w, int(w / 26), semilla + 2, True, .8)
    return cuerpo


def _fondo(fig, g: dict, cuerpo: str) -> None:
    """Capa de ambiente a todo lo ancho y alto de la figura (cielo, monte, suelo); va debajo de todo lo demás."""
    h = g["h"]
    pw, ph = W - g["l"] - g["r"], h - g["t"] - g["b"]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" preserveAspectRatio="none"><g>{cuerpo}</g></svg>')
    uri = "data:image/svg+xml;base64," + base64.b64encode(con_textura(svg).encode("utf-8")).decode("ascii")
    fig.add_layout_image(dict(
        source=uri, xref="paper", yref="paper", x=-g["l"] / pw, y=1 + g["t"] / ph, sizex=W / pw, sizey=h / ph,
        xanchor="left", yanchor="top", sizing="stretch", layer="below", opacity=1))


ROOT_MITAD = 0.40   # la barra "Sector educativo" ocupa de 0.10 a 0.90 de la altura del área (medido en la figura real)


def decorar_inversion(fig) -> None:
    """Alux sobre la barra del presupuesto y una escuelita junto a cada institución que recibe dinero."""
    g = GEOM["lo_que_se_invirtio"]
    pw, ph = W - g["l"] - g["r"], g["h"] - g["t"] - g["b"]
    h = g["h"]
    _fondo(fig, g, (_sol(985, 82, 28) + _nube(300, 42, 130) + _nube(600, 96, 110) + _nube(790, 40, 105)
                    + _pajaros(430, 82, .9) + _pajaros(720, 70, 1.0) + _pajaros(900, 175, .8)
                    + _mariposa(925, 262, 1.1) + _mariposa(1010, 215, .9, "#d96c8a", "#f4d35e") + _mariposa(160, 590, .9, "#6fb6d8", "#ffffff")
                    + _suelo(h - 28, h - 1, W, 31) + _henequen(140, h - 12, .6, 4) + _roca(330, h - 8, .6, 8) + _ceiba(1002, h - 8, .62)
                    + _henequen(560, h - 12, .5, 6)))
    nodo = next(t for t in fig.data if t.type == "sankey").node
    xs, ys = list(map(float, nodo.x)), list(map(float, nodo.y))
    x_min, x_max = min(xs), max(xs)
    raiz_y = ys[xs.index(x_min)]
    _poner(fig, g, "alux_sankey", g["l"] + x_min * pw + 30, g["t"] + (raiz_y - ROOT_MITAD) * ph + 3, 70)
    for x, y in zip(xs, ys):
        if x >= x_max - 1e-6:
            _poner(fig, g, "escuela", g["l"] + x * pw + 9 + 28, g["t"] + y * ph + 15, 36)


def decorar_casa(fig) -> None:
    """Casa de palma junto a "Hogar rural", casa con luz e internet junto a "Hogar urbano" y el alux con el foco al centro."""
    g = GEOM["la_casa_cambio"]
    suelo = g["t"] - 8
    h = g["h"]
    _fondo(fig, g, (_monte([(0, 84), (W, 84)], 14) + _sol(1052, 62, 19) + _nube(96, 56, 120) + _nube(520, 40, 105) + _nube(780, 70, 95)
                    + _pajaros(430, 50, .9) + _pajaros(740, 36, .8) + _mariposa(680, 96, .9) + _mariposa(70, 108, .9, "#6fb6d8", "#ffffff")
                    + _suelo(h - 36, h - 1, W, 41) + _henequen(70, h - 18, .55, 5) + _roca(250, h - 14, .6, 9) + _ceiba(1040, h - 14, .5)
                    + _henequen(640, h - 18, .5, 7)))
    _poner(fig, g, "casa_palma", 262, suelo, 150)
    _poner(fig, g, "casa_moderna", 950, suelo, 112)
    _poner(fig, g, "alux_foco", g["l"] + 0.5 * (W - g["l"] - g["r"]), suelo, 112)    # sobre la línea del cero


def decorar_pobreza(fig) -> None:
    """Alux regando retoños en la esquina vacía (poco rezago, mucha pobreza), arriba a la izquierda."""
    g = GEOM["pobreza_rezago"]
    ph = g["h"] - g["t"] - g["b"]
    base = g["t"] + ph      # línea de base de los palitos
    _fondo(fig, g, (_sol(118, 78, 20) + _nube(330, 62, 120) + _nube(590, 78, 100) + _pajaros(470, 128, .9) + _pajaros(250, 36, .7)
                    + _mariposa(340, 205, 1.0) + _mariposa(120, 250, .9, "#d96c8a", "#f4d35e") + _mariposa(520, 260, .8, "#6fb6d8", "#ffffff")
                    + _pasto(g["l"] + (W - g["l"] - g["r"]) / 2, base + 1, W - g["l"] - g["r"], 70, 71, True, .6)))
    _poner(fig, g, "alux_riega", g["l"] + 0.15 * (W - g["l"] - g["r"]), g["t"] + 0.30 * ph, 160)


DECORAR = {"lo_que_se_invirtio": decorar_inversion, "la_casa_cambio": decorar_casa, "pobreza_rezago": decorar_pobreza}
