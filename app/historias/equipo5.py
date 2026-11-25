"""Equipo 5 · Más años en el aula, ¿mejor vida en casa?: una historia con aluxes, en una sola página.

La página no redibuja ninguna figura: importa `figura` de figures/5/{subtema}/figura.py y le pasa la tabla de
oro. Todas las cifras del texto se calculan de esas tablas (oro."5.<subtema>"); si cambian, el texto cambia.
Orden: treinta_anos → pobreza_rezago → la_casa_cambio → lo_que_se_invirtio.
"""
from __future__ import annotations

import importlib.util
import threading
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dash import dcc, html

RAIZ = Path(__file__).resolve().parents[2]
SUBTEMAS = ("treinta_anos", "pobreza_rezago", "la_casa_cambio", "lo_que_se_invirtio")


def _modulo(ruta: Path, nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


oro = _modulo(RAIZ / "pipelines" / "5" / "oro.py", "equipo5_oro")
try:
    DIBUJO = _modulo(RAIZ / "app" / "historias" / "dibujo5.py", "equipo5_dibujo")
except Exception:
    DIBUJO = None
FIG = {s: _modulo(RAIZ / "figures" / "5" / s / "figura.py", f"equipo5_{s}") for s in SUBTEMAS}

NOTAS = {"treinta_anos": "El alux cuida el camino", "pobreza_rezago": "El alux vigila el monte y las brechas",
         "la_casa_cambio": "El alux revisa que llegue la luz", "lo_que_se_invirtio": "El alux sigue el dinero"}

FUENTES = {
    "educacion_05": "INEGI · Grado promedio de escolaridad por entidad federativa y sexo (tabulado Educacion_05)",
    "censo_1990": "INEGI · Censo de Población y Vivienda 1990, características educativas",
    "irs_coneval": "CONEVAL · Índice de Rezago Social por entidad y municipio, 2000 a 2020",
    "pobreza_municipal": "CONEVAL · Medición de la pobreza municipal 2010, 2015 y 2020 (datos.gob.mx)",
    "iter_2020_yuc": "INEGI · Principales resultados por localidad (ITER), Censo 2020, Yucatán",
    "iter_2010_nal": "INEGI · Principales resultados por localidad (ITER), Censo 2010, nacional",
    "cuenta_publica_tomo2": "Gobierno de Yucatán · Cuenta Pública 2025, Tomo II (Poder Ejecutivo)",
    "cuenta_publica_tomo6": "Gobierno de Yucatán · Cuenta Pública 2025, Tomo VI (entidades paraestatales)",
}


@lru_cache(maxsize=None)
def _tabla(viz_id: str) -> pd.DataFrame:
    return oro.leer(viz_id)


def datos(subtema: str) -> pd.DataFrame:
    return _tabla(f"5.{subtema}")


# Las tablas y figuras se guardan en memoria mientras oro no cambie. Cada carga de página consulta la huella de
# oro (una consulta ligera): si Airflow republicó, se vacían los cachés y lo nuevo aparece al refrescar.
_candado = threading.Lock()
_version_oro = None


def sincronizar_oro() -> None:
    global _version_oro
    with _candado:
        v = oro.version()
        if v != _version_oro:
            for f in (_tabla, fig_pagina):
                f.cache_clear()
            _version_oro = v


@lru_cache(maxsize=None)
def fig_pagina(subtema: str):
    """La misma figura del ebook; en la página el título lo pone la sección. En "treinta_anos" se le agrega el dibujo
    (capa de imagen de Plotly) calculado con los mismos puntos de la línea; si falla, la figura sale sin dibujo."""
    fig = FIG[subtema].figura(datos(subtema))
    if subtema == "treinta_anos":
        fig.update_layout(title=None, autosize=False, width=1100, height=640, margin=dict(l=80, r=150, t=30, b=70),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        try:
            DIBUJO.decorar_treinta(fig)
        except Exception:
            pass
    elif DIBUJO is not None and subtema in DIBUJO.GEOM:        # mismo método: dibujo pegado a los elementos de la gráfica
        g = DIBUJO.GEOM[subtema]
        fig.update_layout(title=None, autosize=False, width=1100, height=g["h"],
                          margin=dict(l=g["l"], r=g["r"], t=g["t"], b=g["b"]),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        try:
            DIBUJO.DECORAR[subtema](fig)
        except Exception:
            pass
    else:
        fig.update_layout(title=None, autosize=False, width=1100, height=640, margin=dict(t=30))
    return fig


# ------------------------------------------------------------------ cifras que cita el texto (salen del oro)
def _n(v, d=1):
    return f"{v:,.{d}f}".replace("-", "−")


def c_treinta() -> dict:
    d = datos("treinta_anos")
    y = d[(d.entidad == "Yucatán") & (d.sexo == "Total")].sort_values("anio")
    p25 = d[(d.sexo == "Total") & (d.anio == y.anio.max())].set_index("entidad").grado_promedio
    mh = d[(d.entidad == "Yucatán") & (d.anio == y.anio.max())].set_index("sexo").grado_promedio
    return dict(a0=int(y.anio.iloc[0]), v0=y.grado_promedio.iloc[0], a1=int(y.anio.iloc[-1]),
                v1=y.grado_promedio.iloc[-1], n=len(y), pen=p25, mh=mh)


def c_pobreza() -> dict:
    d = datos("pobreza_rezago")
    a, b = d[d.anio == 2010], d[d.anio == 2020]
    alto = lambda x: int(x.grado_rezago.isin(["Alto", "Muy alto"]).sum())  # noqa: E731
    bajo = lambda x: int(x.grado_rezago.isin(["Bajo", "Muy bajo"]).sum())  # noqa: E731
    m = a.merge(b, on="municipio", suffixes=("_a", "_b"))
    return dict(n=a.municipio.nunique(), med_a=a.pobreza_pct.median(), med_b=b.pobreza_pct.median(),
                alto_a=alto(a), alto_b=alto(b), bajo_a=bajo(a), bajo_b=bajo(b),
                bajaron=int((m.pobreza_pct_b < m.pobreza_pct_a).sum()), de=len(m),
                r=d.irs.corr(d.pobreza_pct))


def c_casa() -> dict:
    d = datos("la_casa_cambio")

    def v(ind, anio, amb):
        return float(d[(d.indicador == ind) & (d.anio == anio) & (d.ambito == amb)].porcentaje.iloc[0])
    out = {}
    for ind in d.indicador.unique():
        out[ind] = dict(r10=v(ind, 2010, "Rural"), r20=v(ind, 2020, "Rural"),
                        u10=v(ind, 2010, "Urbano"), u20=v(ind, 2020, "Urbano"))
    return out


def c_inversion() -> dict:
    d = datos("lo_que_se_invirtio")
    top = d[d.origen == "Sector educativo"].set_index("destino").monto_millones
    total = top.sum()
    seg = top[top.index.str.contains("SEGEY")].sum()
    resto = d[d.origen.isin(top.index) & ~d.origen.str.contains("SEGEY")]
    mayor = resto.sort_values("monto_millones", ascending=False).iloc[0]
    return dict(total=total, seg=seg, ms=total - seg, pct_seg=seg / total, n_org=len(resto),
                mayor=mayor.destino, mayor_m=mayor.monto_millones)


# ------------------------------------------------------------------ piezas de la página
def _cifra(valor, texto):
    return html.Div(className="h5-cifra", children=[html.Div(valor, className="h5-cifra-valor"),
                                                    html.Div(texto, className="h5-cifra-texto")])


def _fuente(subtema):
    d = datos(subtema).iloc[0]
    sec = [FUENTES.get(k.strip(), k.strip()) for k in str(d.fuente_secundaria).split(",")]
    return html.Div(className="h5-fuente", children=[
        html.Span("Fuente primaria: ", className="h5-et"), FUENTES.get(d.fuente_primaria, d.fuente_primaria),
        html.Br(), html.Span("Fuente secundaria: ", className="h5-et"), " · ".join(sec), html.Br(),
        html.Span("Obtención: ", className="h5-et"), str(d.fecha_obtencion), " · ",
        html.Span("Procesamiento: ", className="h5-et"), str(d.responsable), " · ",
        html.Span("viz_id ", className="h5-et"), html.Code(d.viz_id)])


def _sin_datos(subtema):
    return html.Div(className="h5-sin-datos", children=[
        html.B("Esta sección todavía no tiene datos en oro. "),
        f"Corre el DAG equipo_5 en Airflow para publicar oro.\"5.{subtema}\"."])


def _seccion(num, kicker, titulo, entradilla, subtema, lectura):
    """Cabeza + escena con alux + figura + lectura. Si la tabla de oro no existe, muestra un aviso."""
    cabeza = html.Div(className="h5-cabeza revelar", children=[
        html.Div(f"{num} · {kicker}", className="h5-kicker"), html.H2(titulo), html.P(entradilla, className="h5-dek")])
    try:
        grafica = dcc.Graph(figure=fig_pagina(subtema), config=dict(displayModeBar=False, responsive=False),
                            style={"width": "1100px", "maxWidth": "none"})
        lienzo = html.Div(className="h5-lienzo revelar", children=[      # misma estructura en las cuatro
            html.Span(NOTAS[subtema], className="h5-nota"),
            html.Img(src="/assets/5/asoma.svg", className="h5-asoma", alt=""),
            html.Div(className="h5-marco", children=html.Div(className="h5-figura h5-figura-fija", children=grafica))])
        cuerpo = [lienzo, *lectura(), _fuente(subtema)]
    except Exception:  # tabla ausente o con otra forma: la página sigue viva
        cuerpo = [_sin_datos(subtema)]
    return html.Section(id=subtema, className="h5-seccion", children=[cabeza, *cuerpo])


def _cierre() -> str:
    """Resumen final: cada frase se incluye solo si los datos la sostienen."""
    frases = []
    try:
        t = c_treinta()
        if t["v1"] > t["v0"]:
            frases.append(f"entre {t['a0']} y {t['a1']}, los años de escuela promedio en Yucatán subieron de "
                          f"{_n(t['v0'])} a {_n(t['v1'])}")
    except Exception:
        pass
    try:
        p = c_pobreza()
        if p["med_b"] < p["med_a"]:
            frases.append(f"entre 2010 y 2020, la pobreza en el municipio mediano bajó de {_n(p['med_a'], 0)} % a "
                          f"{_n(p['med_b'], 0)} %")
    except Exception:
        pass
    try:
        k = c_casa().get("Acceso a Internet")
        if k and k["r20"] > k["r10"]:
            frases.append(f"entre 2010 y 2020, las viviendas rurales con internet pasaron de {_n(k['r10'])} % a "
                          f"{_n(k['r20'])} %")
    except Exception:
        pass
    base = ("Las figuras muestran lo que ocurrió al mismo tiempo, no qué provocó qué. "
            "Con datos de INEGI, CONEVAL y la Cuenta Pública")
    if frases:
        return (f"{base}: " + "; ".join(frases) + ". Aun así, la distancia entre lo rural y lo urbano, y los municipios "
                "con rezago alto, no desaparecen.")
    return base + ", cada figura cuenta una parte; falta que el oro tenga datos para resumirlas."


def layout():
    sincronizar_oro()

    def lec_treinta():
        c = c_treinta()
        pen = c["pen"].drop("Yucatán", errors="ignore")
        cambio = c["v1"] - c["v0"]
        verbo = "ganó" if cambio >= 0 else "perdió"
        texto = (f"En {c['a0']} la persona promedio de 15 años o más en Yucatán había cursado {_n(c['v0'])} años de "
                 f"escuela. En {c['a1']} son {_n(c['v1'])}: {verbo} {_n(abs(cambio))} años en {c['a1'] - c['a0']}. "
                 f"La licenciatura completa equivale a 16 años; falta {_n(max(16 - c['v1'], 0))} para llegar ahí.")
        return [html.Div(className="h5-cifras revelar", children=[
                    _cifra(f"{_n(c['v0'])} → {_n(c['v1'])}", f"años de escuela promedio, {c['a0']} a {c['a1']}."),
                    _cifra(f"{c['v1'] - c['v0']:+.1f}".replace("-", "−"), "años de escuela en promedio entre la primera y la última medición."),
                    _cifra(" · ".join(f"{k} {_n(v)}" for k, v in pen.items()),
                           f"las otras dos entidades de la península en {c['a1']}.")]),
                html.P(texto, className="h5-texto revelar")]

    def lec_pobreza():
        c = c_pobreza()
        texto = (f"Cada punto es un municipio. Los de arriba a la derecha son los que tienen más rezago social y "
                 f"más población en pobreza; los de abajo a la izquierda, lo contrario. En los {c['n']} municipios, "
                 f"los dos indicadores se mueven juntos (correlación de {_n(c['r'], 2)}), "
                 "pero eso describe cómo se acompañan, no qué causa qué.")
        return [html.Div(className="h5-cifras revelar", children=[
                    _cifra(f"{_n(c['med_a'], 0)} % → {_n(c['med_b'], 0)} %",
                           "pobreza en el municipio mediano, 2010 a 2020."),
                    _cifra(f"{c['alto_a']} → {c['alto_b']}", "municipios con rezago social alto o muy alto."),
                    _cifra(f"{c['bajaron']} de {c['de']}", "municipios con menos población en pobreza en 2020 que en 2010.")]),
                html.P(texto, className="h5-texto revelar")]

    def lec_casa():
        c = c_casa()
        net = c.get("Acceso a Internet")
        agua = c.get("Agua entubada")
        cel = c.get("Celular")
        cif = []
        if net:
            cif.append(_cifra(f"{_n(net['r10'])} % → {_n(net['r20'])} %",
                              f"viviendas rurales con internet, 2010 a 2020 (urbanas: {_n(net['u10'], 0)} % → "
                              f"{_n(net['u20'], 0)} %)."))
        if cel:
            cif.append(_cifra(f"{_n(cel['r10'], 0)} % → {_n(cel['r20'], 0)} %",
                              "viviendas rurales con celular, 2010 a 2020."))
        if agua:
            cif.append(_cifra(f"{_n(agua['r20'], 0)} %", "de las viviendas rurales ya tiene agua entubada en 2020."))
        basicos = [c[k][a] for k in ("Agua entubada", "Energía eléctrica", "Piso firme") if k in c for a in ("r20", "u20")]
        brechas = {k: c[k]["u20"] - c[k]["r20"] for k in ("Acceso a Internet", "Celular", "Computadora") if k in c}
        partes = []
        if basicos:
            partes.append(f"En 2020, agua, luz y piso firme llegan al menos a {int(min(basicos))} de cada 100 viviendas, "
                          "rurales o urbanas.")
        if brechas:
            partes.append("La distancia entre urbano y rural en 2020 se nota en lo que se suma después: " +
                          ", ".join(f"{_n(b, 0)} puntos en {k.lower()}" for k, b in brechas.items()) + ".")
        partes.append("Las barras con rayas son 2020; las lisas, 2010. Rural y urbano se separan por tamaño de "
                      "localidad (menos de 2,500 habitantes es rural).")
        texto = " ".join(partes)
        return [html.Div(className="h5-cifras revelar", children=cif), html.P(texto, className="h5-texto revelar")]

    def lec_inversion():
        c = c_inversion()
        texto = (f"La Cuenta Pública 2025 registra {_n(c['total'], 0)} millones de pesos devengados en el sector "
                 f"educativo del estado, sumando la Secretaría de Educación y los organismos de educación media "
                 f"superior y superior que aparecen en el diagrama. La Secretaría concentra {c['pct_seg']:.0%}; "
                 f"entre los organismos, el mayor es {c['mayor']} con {_n(c['mayor_m'], 0)} millones. "
                 "Los dos tomos son entes distintos: si parte de lo que reciben los organismos viene de transferencias "
                 "de la propia Secretaría, el diagrama no lo descuenta.")
        return [html.Div(className="h5-cifras revelar", children=[
                    _cifra(f"{_n(c['total'], 0)} mdp", "devengados en 2025 en el sector educativo del diagrama."),
                    _cifra(f"{c['pct_seg']:.0%}", f"corresponde a la Secretaría de Educación ({_n(c['seg'], 0)} mdp)."),
                    _cifra(f"{_n(c['ms'], 0)} mdp", f"van a {c['n_org']} grupos de organismos de media superior y superior.")]),
                html.P(texto, className="h5-texto revelar")]

    return html.Div(className="h5", children=[
        html.Header(className="h5-portada", children=[
            html.Div(className="h5-portada-texto", children=[
                html.Div("La vida en casa · Yucatán, 2000–2025", className="h5-kicker"),
                html.H1("Más años en el aula, ¿mejor vida en casa?"),
                html.P(className="h5-dek", children=(
                    "Cuenta la tradición maya que los aluxes cuidan la milpa y las casas del monte. Esta historia los "
                    "sigue hasta la escuela: cuántos años de aula ganó Yucatán, dónde la pobreza y el rezago siguen "
                    "pesando, qué cambió dentro de las casas y cuánto dinero público se destinó a enseñar.")),
                html.Div("Equipo 5 · Mauricio Ramírez, Diego De Gante y Yeimy · Visual Modelling, UPY",
                         className="h5-firma"),
                html.Div("Desliza para empezar ↓", className="h5-desliza")]),
            html.Img(src="/assets/indice/cap3.jpg", className="h5-portada-img",
                     alt="Casa maya de palma con hamaca y dos niños con mochila rumbo a la escuela.")]),
        _seccion(1, "Treinta años aprendiendo", "Un escalón de libros a la vez",
                 "El alux sube una escalera donde cada peldaño es un año de escuela. La línea muestra el promedio de "
                 "Yucatán; las líneas punteadas, los niveles que se van completando.", "treinta_anos", lec_treinta),
        _seccion(2, "Pobreza y rezago", "Semillas con raíces",
                 "Cada municipio es una semilla; su raíz llega hasta el suelo, el 0 % de pobreza. Mueve el control de "
                 "año para ver cómo se mueven las semillas entre 2010 y 2020.", "pobreza_rezago", lec_pobreza),
        _seccion(3, "La casa cambió", "De la casa de palma a la casa con luz, agua e internet",
                 "El alux sostiene un foco entre las dos casas. Rural a la izquierda, urbano a la derecha: cuántas "
                 "viviendas tienen cada servicio.", "la_casa_cambio", lec_casa),
        _seccion(4, "Lo que se invirtió", "La bolsa que se reparte",
                 "Del dinero público devengado en educación, esto es lo que llegó a cada institución según la Cuenta "
                 "Pública 2025. El ancho de cada cinta es proporcional al monto.", "lo_que_se_invirtio", lec_inversion),
        html.Footer(className="h5-cierre revelar", children=[
            html.H2("Lo que dice la historia"),
            html.P(_cierre()),
            html.P(className="h5-pie", children=(
                "Los datos se leen de las tablas de oro del equipo 5; la misma función de cada figura genera la "
                "imagen del ebook. Los aluxes de las escenas son ilustraciones originales del equipo."))]),
    ])
