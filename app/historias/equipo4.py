"""Equipo 4 · Inversión extranjera en Yucatán: una historia en siete partes, cada una en su página.

Cada parte se muestra en la ficha de su subtema, /v/4/{subtema}, la misma que enlaza el menú de la portada.

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

from dash import Input, Output, callback, dcc, html

try:
    from app.recorrido import ficha
except ImportError:
    from recorrido import ficha

RAIZ = Path(__file__).resolve().parents[2]


def _modulo(ruta: Path, nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


oro = _modulo(RAIZ / "pipelines" / "4" / "oro.py", "equipo4_oro")
FIG = {s: _modulo(RAIZ / "figures" / "4" / s / "figura.py", f"equipo4_{s}")
       for s in ("ied_por_pais", "ied_ranking_origen", "turismo_derrama", "censos_economicos", "pulso_ied",
                 "promesa_resultado", "remesas_ied")}


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


def cifras_yazira() -> dict:
    """Cifras que citan las secciones del pulso, la promesa y las remesas (salen del oro)."""
    pu = datos("pulso_ied").sort_values(["anio", "trimestre"]).reset_index(drop=True)
    alto, bajo = pu.loc[pu.ied_mdd.idxmax()], pu.loc[pu.ied_mdd.idxmin()]
    p20 = pu[pu.anio == 2020]
    a24 = pu[pu.anio == 2024]
    pr = datos("promesa_resultado").set_index("concepto")
    re = datos("remesas_ied").sort_values("anio").reset_index(drop=True)
    gana_ied = re[re.ied_mdd > re.remesas_mdd]
    return dict(
        pu=pu, alto=alto, bajo=bajo, p20_min=p20.loc[p20.ied_mdd.idxmin()], p20_max=p20.loc[p20.ied_mdd.idxmax()],
        a24_max=a24.loc[a24.ied_mdd.idxmax()] if len(a24) else pu.loc[pu.ied_mdd.idxmax()], ultimo=pu.iloc[-1],
        anual=pu.groupby("anio").ied_mdd.sum(), prom=pr.loc["prometido"], reg=pr.loc["registrado_imss"],
        re=re, gana_ied=gana_ied, veces=re.remesas_mdd.sum() / re.ied_mdd.sum(),
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


def _num(subtema: str) -> int:
    """Número del subtema en la lista de la portada (app/recorrido.py)."""
    return ficha("4", subtema)[1]


def _seccion(num, kicker, titulo, entradilla, *cuerpo, id_=None):
    return html.Section(id=id_, className="seccion", children=[
        html.Div(className="seccion-cabeza revelar", children=[
            html.Div(f"{num} · {kicker}", className="kicker"), html.H2(titulo), html.P(entradilla, className="dek")]),
        *cuerpo])


def _secciones(c) -> dict:
    """Las partes de la historia, cada una con su figura, por subtema."""
    a, part, der, gas = c["anual"], c["part"], c["derrama"], c["gasto"]
    pico = a.idxmax()
    salidas = ", ".join(f"{p} ({_n(v, 1)} mdd)" for p, v in c["salidas"].items())
    ult = c["nac"].index[-1]
    nac_pct = c["nac"][ult] / (c["nac"][ult] + c["intl"][ult])
    tot = c["tot"]
    cambio = lambda k: tot[f"{k}_2023"] / tot[f"{k}_2018"] - 1  # noqa: E731
    q = c["cuadrantes"]

    return {
        # ---------------------------------------------------------------- 1 · quién apuesta
        "ied_por_pais": _seccion(
            _num("ied_por_pais"), "Quién apuesta por el estado", "Un mapa de billetes que cruzan el océano",
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
        "ied_ranking_origen": _seccion(
            _num("ied_ranking_origen"), "Flujos volátiles, participación baja", "Un gran año no hace una tendencia",
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
        "turismo_derrama": _seccion(
            _num("turismo_derrama"), "Turismo y derrama económica", "Mientras tanto, el turismo no se detuvo",
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
        "censos_economicos": _seccion(
            _num("censos_economicos"), "Qué cambió en las empresas", "Cinco años en los negocios de 106 municipios",
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
        **_secciones_yazira(),
    }


def _secciones_yazira() -> dict:
    """Las partes de Yazira (pulso, promesa y remesas). Si sus tablas de oro todavía no existen, se omiten y
    las demás partes del capítulo siguen funcionando."""
    try:
        y = cifras_yazira()
    except Exception:
        return {}
    return {
        # ---------------------------------------------------------------- 3 · pulso (Yazira)
        "pulso_ied": _seccion(
            _num("pulso_ied"), "Con qué ritmo llega", "El pulso de la inversión extranjera",
            "Cada latido del monitor es un trimestre: entre más alto el pico, más dinero de fuera llegó a Yucatán. "
            "Un latido hacia abajo es un trimestre en que salió más de lo que entró.",
            _scrolly("pulso_ied", [
                (1, [html.H3("2020: el pulso casi se apaga"),
                     html.P(f"El año abrió con {_n(y['p20_max'].ied_mdd)} mdd en el primer trimestre. Con la pandemia, "
                            f"el {y['p20_min'].periodo} llegaron apenas {_n(y['p20_min'].ied_mdd, 1)} millones de "
                            "dólares.")]),
                (2, [html.H3(f"{y['alto'].periodo}: taquicardia"),
                     html.P(f"El trimestre más alto del periodo: {_n(y['alto'].ied_mdd, 1)} mdd en tres meses. "
                            f"Ese año sumó {_n(y['anual'][int(y['alto'].anio)])} mdd"
                            + (", más que 2020 y 2021 juntos." if y['anual'][int(y['alto'].anio)] >
                               y['anual'].get(2020, 0) + y['anual'].get(2021, 0) else "."))]),
                (3, [html.H3(f"{int(y['bajo'].anio)}: arritmia"),
                     html.P(f"El {y['a24_max'].periodo} entraron {_n(y['a24_max'].ied_mdd)} mdd y el "
                            f"{y['bajo'].periodo} salieron {_n(-y['bajo'].ied_mdd)}: reembolsos y ventas de empresas "
                            "superaron a la inversión nueva. Un año normal en el total puede esconder sobresaltos.")]),
                (0, [html.H3("El trazo completo"),
                     html.P(f"En promedio llegaron {_n(y['pu'].ied_mdd.mean())} mdd por trimestre, pero casi nunca "
                            "el promedio: el capital extranjero llega en latidos sueltos, no en un ritmo constante."),
                     html.Div(className="nota-metodo", children=[
                         html.B("Fuente en streaming. "),
                         f"Esta serie se consulta en cada corrida a la API de Data México; hoy llega hasta el "
                         f"{y['ultimo'].periodo}. Cuando la Secretaría de Economía publique un trimestre nuevo, "
                         "aparecerá aquí."])]),
            ]),
            _fuente("pulso_ied"),
            id_="pulso"),

        # ---------------------------------------------------------------- 6 · promesa (Yazira)
        "promesa_resultado": _seccion(
            _num("promesa_resultado"), "Promesa contra resultado", "Se prometieron empleos; ¿cuántos llegaron?",
            f"En junio de 2022 el Gobierno de Yucatán anunció {int(y['prom'].proyectos)} proyectos de inversión "
            f"privada que generarían {_n(y['prom'].empleos)} empleos. Cada figura vale mil empleos.",
            _scrolly("promesa_resultado", [
                (1, [html.H3(f"{_n(y['prom'].empleos / 1000)} mil empleos prometidos"),
                     html.P(f"La cartera sumaba más de {_n(y['prom'].inversion_mdp)} millones de pesos. La cifra "
                            "incluía empleos directos e indirectos.")]),
                (2, [html.H3(f"{_n(y['reg'].empleos / 1000)} mil con casco"),
                     html.P(f"En el periodo {y['reg'].periodo}, el IMSS registró {_n(y['reg'].empleos)} trabajadores "
                            f"nuevos asegurados en Yucatán: {y['reg'].pct_de_lo_prometido:.0f} % de lo anunciado.")]),
                (0, [html.H3(f"1 de cada {round(100 / y['reg'].pct_de_lo_prometido)}"),
                     html.P("La brecha es la pregunta, no la conclusión: la promesa sumaba empleos indirectos y "
                            "plazos de varios años; el IMSS solo cuenta el empleo formal.")]),
            ]),
            _fuente("promesa_resultado"),
            id_="promesa"),

        # ---------------------------------------------------------------- 7 · remesas (Yazira)
        "remesas_ied": _seccion(
            _num("remesas_ied"), "El otro dinero que llega de fuera", "Sobres contra maletines",
            "Las empresas extranjeras no son las únicas que mandan dinero a Yucatán. Cada sobre son 50 millones de "
            "dólares que los migrantes enviaron a sus familias; cada maletín, 50 millones de inversión extranjera.",
            _scrolly("remesas_ied", [
                (1, [html.H3("Los sobres ganan desde el principio"),
                     html.P(f"En {y['re'].anio.iloc[0]} llegaron {_n(y['re'].remesas_mdd.iloc[0])} mdd en remesas "
                            f"contra {_n(y['re'].ied_mdd.iloc[0])} de inversión extranjera.")]),
                (2, [html.H3(f"{', '.join(map(str, y['gana_ied'].anio)) or 'Ningún año'}: los maletines, una vez"),
                     html.P("Solo entonces la inversión extranjera superó a las remesas"
                            + (": fue el año de la taquicardia del monitor." if int(y['alto'].anio) in
                               set(y['gana_ied'].anio) else "."))]),
                (3, [html.H3("La brecha se abre"),
                     html.P(f"En {y['re'].anio.iloc[-1]} las remesas llegaron a {_n(y['re'].remesas_mdd.iloc[-1])} "
                            f"mdd, {y['re'].veces.iloc[-1]:.1f} veces la inversión extranjera de ese año.")]),
                (0, [html.H3(f"{y['veces']:.1f} veces más en sobres"),
                     html.P(f"Entre {y['re'].anio.iloc[0]} y {y['re'].anio.iloc[-1]} llegaron "
                            f"{_n(y['re'].remesas_mdd.sum())} mdd en remesas y {_n(y['re'].ied_mdd.sum())} en "
                            "inversión extranjera. El dinero de las familias fue más constante que el de las "
                            "empresas.")]),
            ]),
            _fuente("remesas_ied"),
            id_="remesas"),
    }


# ------------------------------------------------------------------ las cuatro partes, cada una en su página
# (subtema, número, título). Cada parte se muestra en la ficha de su subtema, /v/4/{subtema}.
PARTES = [
    ("ied_por_pais", 1, "Un mapa de billetes que cruzan el océano"),
    ("ied_ranking_origen", 2, "Un gran año no hace una tendencia"),
    ("turismo_derrama", 3, "Mientras tanto, el turismo no se detuvo"),
    ("censos_economicos", 4, "Cinco años en los negocios de 106 municipios"),
    ("pulso_ied", 5, "El pulso de la inversión extranjera"),
    ("promesa_resultado", 6, "Se prometieron empleos; ¿cuántos llegaron?"),
    ("remesas_ied", 7, "Sobres contra maletines"),
]


def ruta_parte(subtema: str) -> str:
    return f"/v/4/{subtema}"


def _cierre():
    return html.Footer(className="cierre revelar", children=[
        html.H2("Lo que dice la historia"),
        html.P("El capital extranjero llega a Yucatán en oleadas, sobre todo desde Estados Unidos, y pesa poco "
               "frente al resto del país. El turismo, en cambio, creció año con año, y los negocios del estado "
               "se multiplicaron fuera de Mérida más rápido que dentro."),
        html.P("Los empleos que se anunciaron con esa inversión aparecen solo en parte en el empleo formal, y el "
               "dinero que más llega de fuera no viene de empresas: viene en las remesas de los migrantes."),
        html.P(className="pie", children=(
            "Cifras de IED en millones de dólares; turismo y producción en pesos corrientes. Los datos se leen "
            "de las tablas de oro del equipo 4; la misma función de cada figura genera la imagen del ebook.")),
    ])


def layout_parte(subtema: str):
    """Una sola parte de la historia, con su figura. La última cierra la historia."""
    sincronizar_oro()
    return html.Div(className="historia historia-parte", children=[
        html.Nav(className="migas", children=[html.A("Volver al recorrido", href="/")]),
        _secciones(cifras())[subtema],
        *([_cierre()] if subtema == PARTES[-1][0] else []),
    ])


@callback(Output("fig-mapa", "figure"), Input("mapa-periodo", "value"), Input("mapa-modo", "value"))
def _mapa(periodo, modo):
    sincronizar_oro()
    return fig_mapa(int(periodo[0]), int(periodo[1]), modo)


def _vincular_paso(subtema):
    @callback(Output(f"fig-{subtema}", "figure"), Input(f"paso-{subtema}", "data"))
    def actualizar(paso, subtema=subtema):
        sincronizar_oro()
        return fig_paso(subtema, int(paso or 0))


for _subtema in ("ied_ranking_origen", "pulso_ied", "turismo_derrama", "censos_economicos", "promesa_resultado",
                 "remesas_ied"):
    _vincular_paso(_subtema)
