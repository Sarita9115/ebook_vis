"""Abre las figuras del equipo 3 a partir de archivos preparados locales."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import sys
from tempfile import mkdtemp
import webbrowser

DATOS = Path(__file__).resolve().parent / "datos_locales"


SELECCION_MAPA = """
const grafica = document.getElementById('{plot_id}');
const menus = grafica.layout.updatemenus || [];
const indiceMenu = menus.findIndex(menu => menu.name === 'municipios');
if (indiceMenu !== -1) {
    grafica.on('plotly_click', ({points}) => {
        const punto = points[0];
        if (!punto || !['choropleth', 'scattergeo'].includes(punto.data.type)) return;
        const botones = menus[indiceMenu].buttons;
        const indice = botones.findIndex(boton => boton.label === punto.text);
        if (indice === -1) return;
        const boton = botones[indice];
        Plotly.restyle(grafica, ...boton.args);
        Plotly.relayout(grafica, {[`updatemenus[${indiceMenu}].active`]: indice});
    });
}
"""


def leer_tabla(archivo):
    import pandas as pd

    datos = pd.read_csv(archivo, dtype={"clave_municipio": str})
    return incluir_mapa(datos)


def _orientar_anillos(poligono):
    """Adapta los anillos GeoJSON a la convención del mapa esférico de Plotly."""
    for indice, anillo in enumerate(poligono):
        area = sum(
            a[0] * b[1] - b[0] * a[1]
            for a, b in zip(anillo, anillo[1:])
        )
        if (indice == 0 and area > 0) or (indice > 0 and area < 0):
            anillo.reverse()


def incluir_mapa(datos):
    limites = DATOS / "yucatan.geojson"
    if limites.is_file():
        geojson = json.loads(limites.read_text(encoding="utf-8"))
        for elemento in geojson["features"]:
            geometria = elemento["geometry"]
            if geometria["type"] == "Polygon":
                _orientar_anillos(geometria["coordinates"])
            elif geometria["type"] == "MultiPolygon":
                for poligono in geometria["coordinates"]:
                    _orientar_anillos(poligono)
        datos.attrs["geojson"] = geojson
    return datos


def abrir(figuras, nombre, sin_abrir=False):
    fragmentos = []
    for indice, figura in enumerate(figuras):
        fragmentos.append(figura.to_html(
            full_html=False, include_plotlyjs=indice == 0, auto_play=False,
            config={"displaylogo": False, "responsive": True, "locale": "es"},
            post_script=SELECCION_MAPA,
        ))
    topologia = DATOS / "world_110m.json"
    mapa_local = ""
    if topologia.is_file():
        contenido = topologia.read_text(encoding="utf-8")
        mapa_local = (
            "<script>window.PlotlyGeoAssets={topojson:{world_110m:"
            + contenido + "}};</script>"
        )
    salida = Path(mkdtemp(prefix="mayab-equipo-3-")) / f"{nombre}.html"
    salida.write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Los aluxes del Mayab | Equipo 3</title>'
        '<style>body{margin:0;background:#f7f2e8}main{max-width:1200px;margin:auto}</style>'
        + mapa_local + "<main>" + "\n".join(fragmentos) + "</main></html>",
        encoding="utf-8",
    )
    print(salida.as_uri())
    if not sin_abrir and not webbrowser.open(salida.as_uri()):
        print("Abre la dirección anterior en el navegador.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("natalidad", nargs="?", type=Path, default=DATOS / "natalidad.csv")
    parser.add_argument("--alfabetizacion", type=Path, default=DATOS / "alfabetizacion.csv")
    parser.add_argument("--sin-abrir", action="store_true")
    args = parser.parse_args()
    if not args.natalidad.is_file():
        parser.error(f"No se encontró el CSV: {args.natalidad}")

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    natalidad = import_module("figures.3.natalidad.figura")
    alfabetizacion = import_module("figures.3.alfabetizacion.figura")
    nacimientos = leer_tabla(args.natalidad)
    adultos = alfabetizacion.datos_locales(args.alfabetizacion)
    abrir(
        [natalidad.figura(nacimientos), alfabetizacion.figura(adultos)],
        "equipo-3", args.sin_abrir,
    )


if __name__ == "__main__":
    main()
