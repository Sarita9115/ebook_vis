"""Equipo 4 · Inversión extranjera en Yucatán: una sola historia, en una sola página.

La página no redibuja ninguna figura: importa `figura` de figures/4/{subtema}/figura.py y le pasa la tabla de
oro. El texto avanza con el scroll; cada bloque de texto (paso) le indica a la figura qué resaltar.
Orden de la historia: quién apuesta (4.ied_por_pais) → cuánto pesa (4.ied_ranking_origen) →
mientras tanto, el turismo (4.turismo_derrama) → qué cambió en las empresas (4.censos_economicos).
"""
from __future__ import annotations

import importlib.util
import threading
from functools import lru_cache
from pathlib import Path

from dash import Input, Output, dcc, html

RAIZ = Path(__file__).resolve().parents[3]


def _modulo(ruta: Path, nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


oro = _modulo(RAIZ / "pipelines" / "4" / "oro.py", "equipo4_oro")
FIG = {s: _modulo(RAIZ / "figures" / "4" / s / "figura.py", f"equipo4_{s}")
       for s in ("ied_por_pais", "ied_ranking_origen", "turismo_derrama", "censos_economicos")}


@lru_cache(maxsize=None)
def _tabla(viz_id: str):
    return oro.leer(viz_id)


def datos(subtema: str):
    return _tabla(f"4.{subtema}")


# Las tablas y figuras se guardan en memoria mientras oro no cambie. Cada carga de página y cada callback
# consultan la huella de oro (oro.version, una consulta ligera): si Airflow republicó o una fuente en
# streaming modificó filas, se vacían los cachés y lo nuevo aparece al refrescar, sin reiniciar la app.
_candado = threading.Lock()
_version_oro = None


def sincronizar_oro() -> None:
    global _version_oro
    with _candado:
        v = oro.version()
        if v != _version_oro:
            for f in (_tabla, fig_paso, fig_mapa):
                f.cache_clear()
            _version_oro = v


def _para_pagina(fig, alto=None):
    """En la página el título lo pone la sección; la figura conserva todo lo demás."""
    fig.update_layout(title=None, margin=dict(t=40 if fig.layout.sliders or fig.layout.updatemenus else 50))
    if alto:
        fig.update_layout(height=alto)
    return fig


@lru_cache(maxsize=None)
def fig_paso(subtema: str, paso: int):
    return _para_pagina(FIG[subtema].figura(datos(subtema), paso=paso or None), alto=620)


@lru_cache(maxsize=None)
def fig_mapa(desde: int, hasta: int, modo: str):
    fig = _para_pagina(FIG["ied_por_pais"].figura(datos("ied_por_pais"), anios=list(range(desde, hasta + 1)),
                                                  modo=modo))
    # En la página la leyenda va en la barra de controles de abajo; se quita la del lienzo (la usa el PDF).
    fig.layout.annotations = fig.layout.annotations[:1]
    for g in fig.layout.meta["billetes"]["grupos"]:
        g["anotaciones"] = g["anotaciones"][:1]
    return fig


# ------------------------------------------------------------------ cifras que cita el texto (salen del oro)
def cifras() -> dict:
    p = datos("ied_por_pais")
    p = p[p.anio.between(2020, 2025)]
    por_pais = p.groupby("pais_corto").ied_mdd.sum().sort_values(ascending=False)
    entro = p[p.ied_mdd > 0].ied_mdd.sum()
    china22 = p[(p.pais_corto == "China") & (p.anio == 2022)].ied_mdd.sum()
    revisado = datos("ied_por_pais").groupby("anio").ied_mdd.sum()

    r = datos("ied_ranking_origen")
    anual = r[r.serie == "anual"].set_index("categoria").valor
    anual.index = anual.index.astype(str)
    part = r[r.serie == "participacion"].set_index("categoria").valor
    part.index = part.index.astype(str)
    rk = r[r.serie == "ranking_2025"].set_index("categoria")

    t = datos("turismo_derrama")
    s = {k: g.set_index("periodo").valor for k, g in t.groupby("serie")}
    for v in s.values():
        v.index = v.index.astype(str)
    ctx = _tabla(oro.CONTEXTO)
    ctx = ctx[(ctx.tabla == "llegada_centros") & (ctx.periodo == "ene-nov")]
    ext = {c: g.set_index("indicador").valor for c, g in ctx.groupby("dimension")}

    c = datos("censos_economicos")
    tot = c[["ue_2018", "ue_2023", "personal_2018", "personal_2023", "produccion_mdp_2018",
             "produccion_mdp_2023"]].sum()
    merida = c[c.municipio == "Mérida"].iloc[0]
    kanasin = c[c.municipio == "Kanasín"].iloc[0]
    return dict(
        paises=p[p.ied_mdd.abs() >= 0.05].pais.nunique(), entro=entro, revisado=revisado,
        eu=por_pais["Estados Unidos"], eu_pct=por_pais["Estados Unidos"] / entro, china22=china22,
        salidas=por_pais[por_pais < 0], anual=anual, part=part, lugar25=int(rk.loc["Yucatán", "lugar"]),
        cdmx_veces=rk.loc["Ciudad de México", "valor"] / rk.loc["Yucatán", "valor"],
        derrama=s["derrama_1t"], gasto=s["gasto_1t"], nac=s["derrama_nacional"], intl=s["derrama_internacional"],
        pct_intl=s["pct_internacional"],
        ext_chichen=ext["Chichén Itzá"]["turistas_extranjeros"] / ext["Chichén Itzá"]["turistas_total"],
        ext_uxmal=ext["Uxmal"]["turistas_extranjeros"] / ext["Uxmal"]["turistas_total"],
        ext_merida=ext["Mérida"]["turistas_extranjeros"] / ext["Mérida"]["turistas_total"],
        tot=tot, merida=merida, merida_pct=merida.personal_2023 / tot.personal_2023, kanasin=kanasin,
        cuadrantes=c.cuadrante.value_counts(), n_mun=len(c),
    )


def _n(v, d=0):
    return f"{v:,.{d}f}".replace("-", "−")


# ------------------------------------------------------------------ piezas de la página
def _cifra(valor, texto):
    return html.Div(className="cifra", children=[html.Div(valor, className="cifra-valor"),
                                                 html.Div(texto, className="cifra-texto")])


def _fuente(subtema):
    d = datos(subtema).iloc[0]
    return html.Div(className="fuente", children=[
        html.Span("Fuente primaria: ", className="fuente-et"), d.fuente_primaria, html.Br(),
        html.Span("Fuente secundaria: ", className="fuente-et"), d.fuente_secundaria, html.Br(),
        html.Span("Obtención: ", className="fuente-et"), d.fecha_obtencion, " · ",
        html.Span("Procesamiento: ", className="fuente-et"), d.responsable, " · ",
        html.Span("viz_id ", className="fuente-et"), html.Code(d.viz_id)])


def _scrolly(subtema, pasos):
    """Texto a la izquierda, figura fija a la derecha. Cada paso lleva data-paso; scrolly.js lo publica en el Store."""
    return html.Div(className="scrolly", children=[
        dcc.Store(id=f"paso-{subtema}", data=0),
        html.Div(className="pasos", children=[
            html.Div(className="paso", **{"data-paso": str(i), "data-store": f"paso-{subtema}"},
                     children=[html.Div(className="paso-num", children=f"{i} / {len(pasos)}" if i else "Completo"),
                               *contenido])
            for i, contenido in pasos]),
        html.Div(className="grafica", children=dcc.Graph(
            id=f"fig-{subtema}", figure=fig_paso(subtema, 0), config=dict(displayModeBar=False, responsive=True))),
    ])


def _seccion(num, kicker, titulo, entradilla, *cuerpo, id_=None):
    return html.Section(id=id_, className="seccion", children=[
        html.Div(className="seccion-cabeza revelar", children=[
            html.Div(f"{num} · {kicker}", className="kicker"), html.H2(titulo), html.P(entradilla, className="dek")]),
        *cuerpo])


def layout():
    sincronizar_oro()
    c = cifras()
    a, part, der, gas = c["anual"], c["part"], c["derrama"], c["gasto"]
    pico = a.idxmax()
    salidas = ", ".join(f"{p} ({_n(v, 1)} mdd)" for p, v in c["salidas"].items())
    ult = c["nac"].index[-1]
    nac_pct = c["nac"][ult] / (c["nac"][ult] + c["intl"][ult])
    tot = c["tot"]
    cambio = lambda k: tot[f"{k}_2023"] / tot[f"{k}_2018"] - 1  # noqa: E731
    q = c["cuadrantes"]

    return html.Div(className="historia", children=[
        # ---------------------------------------------------------------- portada
        html.Header(className="portada", children=[
            html.Div("Inversión extranjera en Yucatán · 2018–2025", className="kicker"),
            html.H1("El dinero que llega de fuera"),
            html.P(className="dek", children=(
                f"Entre 2020 y 2025, empresas de {c['paises']} países movieron dinero hacia Yucatán. "
                "Esta es la historia de quién apuesta por el estado, cuánto pesa esa apuesta frente al resto del país, "
                "qué hizo el turismo mientras tanto y qué cambió en los negocios yucatecos.")),
            html.Div("Equipo 4 · Jorge, Yazira Hernández Rives y Dalila Ku · Visual Modelling, UPY", className="firma"),
            html.Div("Desliza para empezar ↓", className="desliza"),
        ]),

        # ---------------------------------------------------------------- 1 · quién apuesta
        _seccion(
            1, "Quién apuesta por el estado", "Un mapa de billetes que cruzan el océano",
            "Cada billete viaja por la ruta entre el país inversionista y Yucatán. El verde es inversión que llega; "
            "el rojo, sobre una ruta punteada, es dinero que se va: años en que los reembolsos o las ventas de "
            "empresas superaron a la inversión nueva. Elige el periodo y cómo quieres verlo.",
            html.Div(className="controles revelar", children=[
                html.Div(className="control", children=[
                    html.Label("Periodo"),
                    dcc.RangeSlider(id="mapa-periodo", min=2018, max=2025, step=1, value=[2020, 2025],
                                    marks={y: str(y) for y in range(2018, 2026)}, allowCross=False)]),
                html.Div(className="control", children=[
                    html.Label("Animación"),
                    dcc.RadioItems(id="mapa-modo", value="acumulado", inline=True, className="radio",
                                   options=[{"label": "Año por año", "value": "anual"},
                                            {"label": "Periodo acumulado", "value": "acumulado"}])]),
            ]),
            html.Div(className="figura-ancha", children=[
                dcc.Graph(id="fig-mapa", figure=fig_mapa(2020, 2025, "acumulado"),
                          config=dict(displayModeBar=False, responsive=True)),
                html.Div(className="mapa-barra", children=[
                    html.Button("⏸ Pausa", id="mapa-pausa", className="mapa-boton", n_clicks=0),
                    html.Select(id="mapa-velocidad", className="mapa-select", children=[
                        html.Option("0.5×", value="0.5"), html.Option("1×", value="1", selected=True),
                        html.Option("2×", value="2")]),
                    html.Span(className="mapa-ley", children=[html.I(className="ley-entra"), "Entra a Yucatán"]),
                    html.Span(className="mapa-ley", children=[html.I(className="ley-sale"), "Sale de Yucatán"]),
                    html.Div(id="mapa-chips", className="mapa-chips"),
                ])]),
            _fuente("ied_por_pais"),
            html.Div(className="cifras revelar", children=[
                _cifra(f"{c['eu_pct']:.0%}", f"de la inversión que llegó entre 2020 y 2025 vino de Estados Unidos "
                                            f"({_n(c['eu'])} mdd)."),
                _cifra(f"{_n(c['china22'])} mdd", "llegaron de China en un solo año, 2022: el mayor flujo de un país "
                                                   "en todo el periodo."),
                _cifra(f"{len(c['salidas'])}", f"países sacaron más de lo que metieron en el periodo: {salidas}."),
            ]),
            id_="quien"),

        # ---------------------------------------------------------------- 2 · cuánto pesa
        _seccion(
            2, "Flujos volátiles, participación baja", "Un gran año no hace una tendencia",
            "Vista desde el resto del país, la inversión extranjera en Yucatán es pequeña y nerviosa: "
            "sube y baja con unas cuantas operaciones grandes.",
            _scrolly("ied_ranking_origen", [
                (1, [html.H3(f"{pico}, el año del salto"),
                     html.P(f"Yucatán recibió {_n(a[pico], 1)} millones de dólares en {pico}, "
                            f"{a[pico] / a.drop(pico).mean():.1f} veces el promedio del resto de los años. "
                            f"No se sostuvo: en 2025 fueron {_n(a['2025'], 1)} mdd.")]),
                (2, [html.H3(f"Nunca más de {part.max():.2f} %"),
                     html.P(f"Ni en su mejor año pasó de {part.max():.2f} % de la inversión extranjera que llegó "
                            f"a México. En 2025 fue {part['2025']:.2f} %: de cada {100 / part['2025']:,.0f} dólares, "
                            f"uno llegó a Yucatán.")]),
                (3, [html.H3(f"Lugar {c['lugar25']} de 32"),
                     html.P(f"En 2025 la Ciudad de México recibió {c['cdmx_veces']:,.0f} veces lo que Yucatán. "
                            "La inversión se concentra en el centro y el norte industrial.")]),
                (4, [html.H3("Tres países explican casi todo"),
                     html.P("Según la ficha estatal de la Secretaría de Economía, Estados Unidos, China y España "
                            "concentran la inversión acumulada desde 2018.")]),
                (0, [html.H3("Los cuatro paneles juntos"),
                     html.P("Picos aislados, una participación que no despega y pocos países de origen."),
                     html.Div(className="nota-metodo", children=[
                         html.B("¿Por qué no coincide con el mapa? "),
                         "Estas cifras son las originales, publicadas al cierre de cada año. El mapa usa la base "
                         "por país, que la Secretaría de Economía revisa trimestre con trimestre: las revisiones "
                         f"posteriores cambian los montos (por ejemplo, {pico} pasa de {_n(a[pico])} a "
                         f"{_n(c['revisado'][int(pico)])} mdd en la base revisada)."])]),
            ]),
            _fuente("ied_ranking_origen"),
            id_="pesa"),

        # ---------------------------------------------------------------- 3 · turismo
        _seccion(
            3, "Turismo y derrama económica", "Mientras tanto, el turismo no se detuvo",
            "La inversión extranjera va y viene. El gasto de quienes visitan el estado, en cambio, creció casi sin "
            "pausa desde la pandemia.",
            _scrolly("turismo_derrama", [
                (1, [html.H3(f"{der.iloc[-1] / der.iloc[0]:.1f} veces más derrama"),
                     html.P(f"En el primer trimestre de 2026 los visitantes dejaron {_n(der.iloc[-1])} millones de "
                            f"pesos, contra {_n(der.iloc[0])} en el de 2020. El piso fue 2021, con "
                            f"{_n(der.min())} millones, en plena pandemia.")]),
                (2, [html.H3(f"${_n(gas.iloc[-1])} al día"),
                     html.P(f"Cada turista gasta más: el gasto diario promedio pasó de ${_n(gas.iloc[0])} a "
                            f"${_n(gas.iloc[-1])} pesos entre el primer trimestre de 2020 y el de 2026.")]),
                (3, [html.H3("El turismo nacional sostiene la derrama"),
                     html.P(f"En {ult}, {nac_pct:.0%} de la derrama vino de turistas nacionales.")]),
                (4, [html.H3("Uno de cada cuatro es extranjero"),
                     html.P(f"Alrededor de una cuarta parte de los turistas-noche son internacionales. En los sitios "
                            f"arqueológicos la proporción se dispara: de enero a noviembre de 2025, "
                            f"{c['ext_chichen']:.0%} de quienes llegaron a Chichén Itzá y {c['ext_uxmal']:.0%} de "
                            f"los de Uxmal venían de fuera del país; en Mérida, {c['ext_merida']:.0%}.")]),
                (0, [html.H3("Crecimiento ininterrumpido"),
                     html.P("Más derrama, más gasto por persona y un turismo internacional estable: "
                            "el contraste con la inversión extranjera, que cayó después de 2022.")]),
            ]),
            _fuente("turismo_derrama"),
            id_="turismo"),

        # ---------------------------------------------------------------- 4 · censos
        _seccion(
            4, "Qué cambió en las empresas", "Cinco años en los negocios de 106 municipios",
            "Los Censos Económicos fotografían a todos los negocios del estado. Comparar el de 2019 (año de "
            "referencia 2018) con el de 2024 (2023) muestra dónde hubo más negocios, más empleo, o ninguno de los dos.",
            html.Div(className="cifras revelar", children=[
                _cifra(f"{cambio('ue'):+.0%}", f"unidades económicas: de {_n(tot.ue_2018)} a {_n(tot.ue_2023)}."),
                _cifra(f"{cambio('personal'):+.0%}", f"personal ocupado: de {_n(tot.personal_2018)} a "
                                                     f"{_n(tot.personal_2023)} personas."),
                _cifra(f"{cambio('produccion_mdp'):+.0%}", "producción bruta total, en pesos corrientes "
                                                            "(sin descontar la inflación)."),
            ]),
            _scrolly("censos_economicos", [
                (1, [html.H3("Mérida pesa, pero apenas se movió"),
                     html.P(f"La capital concentra {c['merida_pct']:.0%} del empleo de los negocios del estado. "
                            f"Entre censos sumó {c['merida'].cambio_ue_pct:.0f} % más negocios, pero su personal "
                            f"ocupado creció solo {c['merida'].cambio_personal_pct:.1f} %.")]),
                (2, [html.H3("La periferia metropolitana"),
                     html.P(f"Kanasín, pegado a Mérida, pasó de {_n(c['kanasin'].personal_2018)} a "
                            f"{_n(c['kanasin'].personal_2023)} personas ocupadas "
                            f"({c['kanasin'].cambio_personal_pct:+.0f} %). Umán y Progreso crecieron más despacio.")]),
                (3, [html.H3("Porcentajes enormes, números pequeños"),
                     html.P("Abalá, Yaxcabá o Mocochá duplicaron su empleo, pero partían de unos cientos de "
                            "personas: el tamaño de la burbuja recuerda cuánto pesan.")]),
                (4, [html.H3(f"{c['n_mun'] - q.get('Expansión', 0)} municipios fuera de la expansión"),
                     html.P(f"{q.get('Fragmentación', 0)} tienen más negocios pero menos empleo, "
                            f"{q.get('Concentración', 0)} menos negocios pero más empleo, y "
                            f"{q.get('Retroceso', 0)} perdieron en ambos.")]),
                (0, [html.H3("El mapa completo"),
                     html.P(f"{q.get('Expansión', 0)} de {c['n_mun']} municipios ganaron negocios y empleo. "
                            "Pasa el cursor sobre cada burbuja para ver sus cifras.")]),
            ]),
            _fuente("censos_economicos"),
            id_="censos"),

        # ---------------------------------------------------------------- cierre
        html.Footer(className="cierre revelar", children=[
            html.H2("Lo que dice la historia"),
            html.P("El capital extranjero llega a Yucatán en oleadas, sobre todo desde Estados Unidos, y pesa poco "
                   "frente al resto del país. El turismo, en cambio, creció año con año, y los negocios del estado "
                   "se multiplicaron fuera de Mérida más rápido que dentro."),
            html.P(className="pie", children=(
                "Cifras de IED en millones de dólares; turismo y producción en pesos corrientes. Los datos se leen "
                "de las tablas de oro del equipo 4; la misma función de cada figura genera la imagen del ebook.")),
        ]),
    ])


def registrar(app) -> None:
    """Callbacks: periodo y modo del mapa; paso activo de cada sección guiada."""
    @app.callback(Output("fig-mapa", "figure"), Input("mapa-periodo", "value"), Input("mapa-modo", "value"))
    def _mapa(periodo, modo):
        sincronizar_oro()
        return fig_mapa(int(periodo[0]), int(periodo[1]), modo)

    def _paso(subtema):
        def actualizar(paso):
            sincronizar_oro()
            return fig_paso(subtema, int(paso or 0))
        return actualizar

    for subtema in ("ied_ranking_origen", "turismo_derrama", "censos_economicos"):
        app.callback(Output(f"fig-{subtema}", "figure"), Input(f"paso-{subtema}", "data"))(_paso(subtema))
