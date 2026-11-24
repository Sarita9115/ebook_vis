"""Tablas de oro de cuatro subtemas del equipo 2 (los que procesa Esaú).

    2.herbario_cicy         Herbario CICY, plantas vasculares
    2.cria_de_cerdo         Impacto por municipio ocasionado por la cría de cerdo en la península
    2.negocios_en_reservas  Cada tipo de negocio situado en cada reserva natural
    2.unidades_en_reservas  Unidades económicas de impacto ambiental o relación con la biodiversidad

Mientras los DAG no carguen plata y oro, estas funciones arman la tabla de oro directamente
desde los archivos de la carpeta de fuentes del equipo (la de Drive). Cada función devuelve
un DataFrame (o GeoDataFrame en EPSG:4326) que se pasa tal cual a `figura(datos)`.

Uso para revisar las figuras en local:

    python pipelines/2/oro_esau.py "ruta/a/Fuentes" salida/

`Fuentes` es la carpeta con las subcarpetas DENUE, Granjas_porcicolas_transformación y
Herbario CICY plantas vasculares. En `salida/` quedan los HTML y PNG de prueba (no se versionan).
"""

from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

CRS_M = "EPSG:32616"      # UTM 16N, distancias en metros
CRS_WEB = "EPSG:4326"
ENTIDADES = {"04": "Campeche", "23": "Quintana Roo", "31": "Yucatán"}
RESPONSABLE = "Esaú Palomo"
SIMPLIFICA_M = 400        # tolerancia para simplificar polígonos antes de publicarlos

# ---------------------------------------------------------------------------- rutas


def _rutas(fuentes: Path) -> dict[str, Path]:
    g = fuentes / "Granjas_porcicolas_transformación" / "data"
    return {
        "anp": g / "anp_shapefile" / "232-ANP_ITRF08_19162026.shp",
        "municipios": g / "municipios_peninsula.geojson",
        "basemap": g / "basemap_peninsula.geojson",
        "cerdos": g / "censo" / "ca2022_gan25.xlsx",       # existencias de porcinos
        "unidades": g / "censo" / "ca2022_gan24.xlsx",     # unidades de producción con porcinos
        "denue": fuentes / "DENUE" / "denue_peninsula_impacto_biodiversidad.csv",
        "cicy": fuentes / "Herbario CICY plantas vasculares" / "cicy_flora_peninsula_yucatan.csv",
    }


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def _procedencia(df: pd.DataFrame, viz_id: str, primaria: str, secundaria: str, institucion: str) -> pd.DataFrame:
    df = df.copy()
    df["viz_id"] = viz_id
    df["fuente_primaria"] = primaria
    df["fuente_secundaria"] = secundaria
    df["institucion"] = institucion
    df["fecha_obtencion"] = date.today().isoformat()
    df["responsable"] = RESPONSABLE
    return df


def _simplifica_web(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.to_crs(CRS_M).copy()
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFICA_M, preserve_topology=True)
    return gdf.to_crs(CRS_WEB)


# ---------------------------------------------------------------------- capas comunes


def _municipios(r) -> gpd.GeoDataFrame:
    mun = gpd.read_file(r["municipios"]).to_crs(CRS_M)
    mun["key"] = mun["CVE_ENT"] + "|" + mun["NOMGEO"].map(_norm)
    return mun


def _reservas(r, mun: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """ANP federales principalmente terrestres (al menos 20 %) que tocan la península."""
    anp = gpd.read_file(r["anp"]).to_crs(CRS_M)
    anp = anp[anp.intersects(mun.union_all().buffer(15_000))]
    anp = anp[anp["S_TERRES"] / (anp["S_TERRES"] + anp["S_MARINA"]) >= 0.2].copy()
    anp["NOMBRE"] = anp["NOMBRE"].str.replace("Dzibilchantún", "Dzibilchaltún")
    return anp.reset_index(drop=True)


def _contexto(r, mun: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Países vecinos y contorno de los tres estados, como capa de fondo."""
    base = gpd.read_file(r["basemap"]).to_crs(CRS_M)
    vecinos = base[base["grupo"] == "vecino"][["geometry"]].assign(tipo="vecino", nombre="")
    estados = mun.dissolve("CVE_ENT").reset_index()
    estados["geometry"] = estados.buffer(300).buffer(-300)
    estados = estados[["CVE_ENT", "geometry"]].assign(tipo="estado", nombre=estados["CVE_ENT"].map(ENTIDADES))
    return gpd.GeoDataFrame(pd.concat([vecinos, estados[["tipo", "nombre", "geometry"]]]), crs=CRS_M)


def _leer_cuadro(ruta: Path, col_valor: int, nombre: str) -> pd.DataFrame:
    """Cuadros del Censo Agropecuario 2022: solo filas municipales de 04, 23 y 31."""
    t = pd.read_excel(ruta, header=None)
    filas = t[t[0].astype(str).str.match(r"^(04|23|31) ") & t[1].notna()]
    return pd.DataFrame({
        "CVE_ENT": filas[0].str[:2].values,
        "municipio": filas[1].values,
        nombre: pd.to_numeric(filas[col_valor], errors="coerce").fillna(0).astype(int).values,
    })


def _censo_porcino(r) -> pd.DataFrame:
    censo = _leer_cuadro(r["cerdos"], 3, "cerdos").merge(
        _leer_cuadro(r["unidades"], 5, "unidades"), on=["CVE_ENT", "municipio"])
    censo["key"] = censo["CVE_ENT"] + "|" + censo["municipio"].map(_norm)
    return censo


# Temas de negocio (mismos patrones que mapa_burbujas_reservas.ipynb)
TEMAS = [
    ("Gasolina, gas y químicos", r"peligros|gasolina|diesel|gas l\. p|gas natural|combustible|petróleo|petrol|"
                                 r"petroquímic|químic|pesticida|gases industriales|fabricación de fertilizantes"),
    ("Basura y reciclaje", r"desecho|remediación de residuos"),
    ("Campo y ganado", r"agropecuari|agricultura|alimentos para animales|agrícola|ganado|ganadería|"
                       r"plaguicida|matanza|carne de|embutidos|aserr|aprovechamiento forestal|fumigación|riego|harina"),
    ("Construcción y materiales", r"construcción|edificación|cemento|concreto|tabique|cantera|yeso|fabricación de cal|"
                                  r"minería|minerales no metálicos|urbanización|terrenos"),
    ("Pesca y mariscos", r"pesca|pescados|mariscos|camaron|acuicultura|sardina|túnidos"),
    ("Hoteles y turismo", r"hotel|casas amueblados|marinas turísticas"),
]
CERCA_KM = 5
# Posición de la burbuja (lon, lat) cuando conviene separarla de su reserva
MOVER = {
    "Manglares de Nichupté": (-86.15, 21.02), "San Buenaventura": (-86.50, 21.62), "Yum Balam": (-87.15, 22.00),
    "Manglares de Puerto Morelos": (-86.00, 20.40), "Cenote Aerolito": (-86.05, 19.95), "Tulum": (-86.75, 19.62),
    "Jaguar": (-87.95, 20.20), "Ría Lagartos": (-88.20, 22.00), "Dzibilchaltún": (-89.60, 21.75),
    "Ría Celestún": (-90.75, 21.05), "Los Petenes": (-91.15, 20.15), "Laguna de Términos": (-91.75, 18.95),
    "Sian Ka'an": (-87.40, 19.02),
}
CONTRASTE = ["Calakmul", "Balam Kú", "Balam Kin", "Bala'an K'aax"]   # grandes selvas casi sin negocios
MIN_VECINOS = 40


def _tema(clase) -> str | None:
    c = str(clase).lower()
    for tema, patron in TEMAS:
        if re.search(patron, c):
            return tema
    return None


def _negocios_cerca(r, anp: gpd.GeoDataFrame, max_km: float | None = CERCA_KM) -> gpd.GeoDataFrame:
    """Cada negocio del DENUE con tema se asigna a su reserva más cercana; se quedan los de menos de `max_km`."""
    denue = pd.read_csv(r["denue"], encoding="utf-8-sig", low_memory=False)
    denue["tema"] = denue["Clase_actividad"].map(_tema)
    denue = denue.dropna(subset=["tema", "Latitud", "Longitud"])
    neg = gpd.GeoDataFrame(denue, geometry=gpd.points_from_xy(denue["Longitud"], denue["Latitud"]),
                           crs=CRS_WEB).to_crs(CRS_M)
    cruce = gpd.sjoin_nearest(neg, anp[["NOMBRE", "geometry"]], distance_col="dist_m")
    cruce = cruce[~cruce.index.duplicated()]
    return cruce if max_km is None else cruce[cruce["dist_m"] <= max_km * 1000]


def _punto_web(x: float, y: float) -> tuple[float, float]:
    p = gpd.GeoSeries.from_xy([x], [y], crs=CRS_M).to_crs(CRS_WEB).iloc[0]
    return p.x, p.y


def _burbujas(anp: gpd.GeoDataFrame, conteo: pd.Series) -> pd.DataFrame:
    sel = [n for n in conteo.index if conteo[n] >= MIN_VECINOS]
    sel += [n for n in CONTRASTE if n in set(anp["NOMBRE"]) and n not in sel]
    filas = []
    for nombre in sel:
        geom = anp.loc[anp["NOMBRE"] == nombre, "geometry"].union_all()
        px, py = _punto_web(*geom.representative_point().coords[0])
        bx, by = MOVER.get(nombre, (px, py))
        filas.append(dict(reserva=nombre, ancla_lon=px, ancla_lat=py, lon=bx, lat=by))
    return pd.DataFrame(filas)


# ------------------------------------------------------------------- 2.cria_de_cerdo

FRANJA_KM = 10
GRANJA_GRANDE = 1_000     # cerdos por unidad de producción, en promedio
MIN_CERDOS = 10_000


def oro_cria_de_cerdo(fuentes: Path) -> gpd.GeoDataFrame:
    """Tabla de oro de 2.cria_de_cerdo. Una fila por geometría, separada por `tipo`:

    municipio  cve_ent, nombre, cerdos, unidades, cerdos_por_unidad, granja_grande, geometry
    reserva    nombre, cerdos_entorno, municipios_entorno, municipio_top, cerdos_municipio_top, geometry
    franja     geometry (unión de las franjas de 10 km alrededor de las reservas)
    vecino / estado   capas de contexto
    """
    r = _rutas(Path(fuentes))
    mun = _municipios(r).merge(_censo_porcino(r)[["key", "cerdos", "unidades"]], on="key", how="left")
    mun[["cerdos", "unidades"]] = mun[["cerdos", "unidades"]].fillna(0).astype(int)
    mun["cerdos_por_unidad"] = (mun["cerdos"] / mun["unidades"].where(mun["unidades"] > 0)).fillna(0)
    mun["granja_grande"] = (mun["cerdos_por_unidad"] >= GRANJA_GRANDE) & (mun["cerdos"] >= MIN_CERDOS)
    anp = _reservas(r, mun)

    reservas = []
    for _, a in anp.iterrows():
        vecinos = mun[mun.intersects(a.geometry.buffer(FRANJA_KM * 1000))]
        if vecinos.empty:          # reservas fuera de la península (p. ej. Tabasco)
            continue
        top = vecinos.sort_values("cerdos", ascending=False).iloc[0]
        reservas.append(dict(tipo="reserva", nombre=a["NOMBRE"], cerdos_entorno=int(vecinos["cerdos"].sum()),
                             municipios_entorno=len(vecinos), municipio_top=top["NOMGEO"],
                             cerdos_municipio_top=int(top["cerdos"]), geometry=a.geometry))
    reservas = gpd.GeoDataFrame(reservas, crs=CRS_M)

    municipios = mun.rename(columns={"CVE_ENT": "cve_ent", "NOMGEO": "nombre"})[
        ["cve_ent", "nombre", "cerdos", "unidades", "cerdos_por_unidad", "granja_grande", "geometry"]
    ].assign(tipo="municipio")
    franja = gpd.GeoDataFrame([dict(tipo="franja", nombre=f"Franja de {FRANJA_KM} km",
                                    geometry=anp.buffer(FRANJA_KM * 1000).union_all().boundary)], crs=CRS_M)
    oro = gpd.GeoDataFrame(pd.concat([municipios, reservas, franja, _contexto(r, mun)], ignore_index=True), crs=CRS_M)
    oro = _simplifica_web(oro)
    return _procedencia(oro, "2.cria_de_cerdo", "INEGI, Censo Agropecuario 2022 (cuadros ca2022_gan24 y ca2022_gan25)",
                        "CONANP, Áreas Naturales Protegidas federales", "INEGI")


# ------------------------------------------------- 2.negocios_en_reservas y unidades


def _oro_burbujas(fuentes: Path, por_tema: bool) -> gpd.GeoDataFrame:
    r = _rutas(Path(fuentes))
    mun = _municipios(r)
    anp = _reservas(r, mun)
    cerca = _negocios_cerca(r, anp)
    conteo = cerca["NOMBRE"].value_counts()
    burbujas = _burbujas(anp, conteo)
    if por_tema:
        t = cerca.groupby(["NOMBRE", "tema"]).size().rename("negocios").reset_index()
        rejilla = pd.MultiIndex.from_product([burbujas["reserva"], [x for x, _ in TEMAS]], names=["reserva", "tema"])
        t = (t.rename(columns={"NOMBRE": "reserva"}).set_index(["reserva", "tema"])
             .reindex(rejilla, fill_value=0).reset_index())
        burbujas = burbujas.merge(t, on="reserva")
    else:
        burbujas["negocios"] = burbujas["reserva"].map(conteo).fillna(0).astype(int)
        principal = cerca.groupby("NOMBRE")["tema"].agg(lambda s: s.value_counts().idxmax())
        burbujas["tema_principal"] = burbujas["reserva"].map(principal).fillna("")
    burbujas["tipo"] = "burbuja"
    capas = anp[["NOMBRE", "geometry"]].rename(columns={"NOMBRE": "nombre"}).assign(tipo="reserva")
    capas = gpd.GeoDataFrame(pd.concat([capas, _contexto(r, mun)], ignore_index=True), crs=CRS_M)
    capas = _simplifica_web(capas)
    oro = pd.concat([burbujas, capas], ignore_index=True)
    return gpd.GeoDataFrame(oro, geometry="geometry", crs=CRS_WEB)


def oro_negocios_en_reservas(fuentes: Path) -> gpd.GeoDataFrame:
    """Tabla de oro de 2.negocios_en_reservas.

    burbuja    reserva, tema, negocios (a menos de 5 km), lon, lat (burbuja), ancla_lon, ancla_lat (reserva)
    reserva / vecino / estado   polígonos de fondo (geometry)
    """
    oro = _oro_burbujas(fuentes, por_tema=True)
    return _procedencia(oro, "2.negocios_en_reservas", "INEGI, DENUE (corte vigente, península)",
                        "CONANP, Áreas Naturales Protegidas federales", "INEGI")


def oro_unidades_en_reservas(fuentes: Path) -> gpd.GeoDataFrame:
    """Tabla de oro de 2.unidades_en_reservas.

    burbuja    reserva, negocios (a menos de 5 km), tema_principal, lon, lat, ancla_lon, ancla_lat
    reserva / vecino / estado   polígonos de fondo (geometry)
    """
    oro = _oro_burbujas(fuentes, por_tema=False)
    return _procedencia(oro, "2.unidades_en_reservas", "CONANP, Áreas Naturales Protegidas federales",
                        "INEGI, DENUE (corte vigente, península)", "CONANP")


# ------------------------------------------------------------------- 2.herbario_cicy

UMBRAL_CERDOS = 50_000       # municipio con muchas granjas
UMBRAL_NEGOCIOS = 300        # municipio con muchos negocios que pueden dañar la naturaleza
ESPECIES_POR_ESTADO = 12
MIN_REGISTROS = 3

# especie: nombre común
POPULARES = {
    "Agave fourcroydes": "Henequén", "Bursera simaruba": "Chacá", "Manilkara zapota": "Chicozapote",
    "Haematoxylum campechianum": "Palo de tinte", "Piscidia piscipula": "Jabín",
    "Gymnopodium floribundum": "Ts'iits'ilche'", "Bixa orellana": "Achiote", "Byrsonima crassifolia": "Nance",
    "Pouteria campechiana": "Kanisté", "Chrysophyllum mexicanum": "Caimito", "Psidium guajava": "Guayaba",
    "Annona squamosa": "Saramuyo", "Coccoloba uvifera": "Uva de mar", "Bauhinia divaricata": "Pata de vaca",
    "Tabebuia rosea": "Maculís", "Plumeria rubra": "Flor de mayo", "Cordia sebestena": "Siricote de playa",
    "Guazuma ulmifolia": "Pixoy", "Havardia albicans": "Chukum", "Lonchocarpus rugosus": "Kanasín",
    "Vitex gaumeri": "Ya'axnik", "Leucaena leucocephala": "Uaxim", "Mimosa bahamensis": "Sak katsim",
    "Acacia gaumeri": "Box katsim", "Jatropha gaumeri": "Pomolché", "Hampea trilobata": "Majahua",
    "Neomillspaughia emarginata": "Sak iitsa'", "Ceiba pentandra": "Ceiba", "Brosimum alicastrum": "Ramón",
    "Lysiloma latisiliquum": "Tzalam", "Metopium brownei": "Chechem", "Swietenia macrophylla": "Caoba",
    "Enterolobium cyclocarpum": "Pich", "Cordia dodecandra": "Ciricote", "Sabal yapa": "Huano",
    "Coccothrinax readii": "Palma nakax", "Thrinax radiata": "Palma chit", "Pseudophoenix sargentii": "Palma kuká",
    "Rhizophora mangle": "Mangle rojo", "Avicennia germinans": "Mangle negro", "Laguncularia racemosa": "Mangle blanco",
    "Conocarpus erectus": "Mangle botoncillo", "Beaucarnea pliabilis": "Pata de elefante",
    "Guaiacum sanctum": "Guayacán", "Cedrela odorata": "Cedro rojo",
}
# NOM-059-SEMARNAT-2010: A = amenazada, Pr = sujeta a protección especial
NOM059 = {"Rhizophora mangle": "A", "Avicennia germinans": "A", "Laguncularia racemosa": "A",
          "Conocarpus erectus": "A", "Beaucarnea pliabilis": "A", "Thrinax radiata": "A",
          "Pseudophoenix sargentii": "A", "Guaiacum sanctum": "Pr", "Cedrela odorata": "Pr"}
ESTADO_CVE = {"YUCATÁN": "31", "CAMPECHE": "04", "QUINTANA ROO": "23"}


def oro_herbario_cicy(fuentes: Path) -> pd.DataFrame:
    """Tabla de oro de 2.herbario_cicy. Una fila por estado y planta conocida:

    estado, nombre_comun, especie, registros, frac_presion, nom059, nivel,
    especies_estado, frac_presion_estado, municipios_presion
    """
    r = _rutas(Path(fuentes))
    # municipios con mucha presión: muchos cerdos o muchos negocios que pueden dañar la naturaleza
    cerdos = _censo_porcino(r).set_index("key")["cerdos"]
    mun = _municipios(r)
    todos = _negocios_cerca(r, _reservas(r, mun), max_km=None).drop(columns="index_right")
    todos = todos.sjoin(mun[["key", "geometry"]], predicate="within")
    negocios = todos["key"].value_counts()
    presion = set(cerdos[cerdos >= UMBRAL_CERDOS].index) | set(negocios[negocios >= UMBRAL_NEGOCIOS].index)

    flora = pd.read_csv(r["cicy"], low_memory=False)
    flora["especie"] = flora["Genero"].str.strip() + " " + flora["Especie"].str.strip()
    flora["key"] = flora["Estado_Normalizado"].map(ESTADO_CVE) + "|" + flora["Municipio"].map(_norm)
    flora["presion"] = flora["key"].isin(presion)

    tabla = (flora[flora["especie"].isin(POPULARES)]
             .groupby(["Estado_Normalizado", "especie"])
             .agg(registros=("especie", "size"), frac_presion=("presion", "mean")).reset_index())
    tabla["nombre_comun"] = tabla["especie"].map(POPULARES)
    tabla["nom059"] = tabla["especie"].map(NOM059).fillna("")
    n = (tabla["nom059"] != "").astype(int) + (tabla["frac_presion"] > 0.5).astype(int)
    tabla["nivel"] = n.map({2: "Peligro", 1: "Alerta", 0: "Sin alerta"})

    sel = []
    for _, g in tabla[tabla["registros"] >= MIN_REGISTROS].groupby("Estado_Normalizado"):
        g = g.sort_values("registros", ascending=False)
        sel.append(pd.concat([g[g["nom059"] != ""], g]).drop_duplicates("especie").head(ESPECIES_POR_ESTADO))
    sel = pd.concat(sel)

    resumen = flora.groupby("Estado_Normalizado").agg(especies_estado=("especie", "nunique"),
                                                      frac_presion_estado=("presion", "mean"))
    sel = sel.join(resumen, on="Estado_Normalizado")
    sel["estado"] = sel["Estado_Normalizado"].map({"YUCATÁN": "Yucatán", "CAMPECHE": "Campeche",
                                                   "QUINTANA ROO": "Quintana Roo"})
    sel["municipios_presion"] = len(presion)
    sel = sel[["estado", "nombre_comun", "especie", "registros", "frac_presion", "nom059", "nivel",
               "especies_estado", "frac_presion_estado", "municipios_presion"]].reset_index(drop=True)
    return _procedencia(sel, "2.herbario_cicy", "Herbario CICY, colectas de plantas vasculares",
                        "SEMARNAT, NOM-059-SEMARNAT-2010; INEGI, Censo Agropecuario 2022 y DENUE", "CICY")


# --------------------------------------------------------------------------- prueba

ORO = {
    "herbario_cicy": oro_herbario_cicy,
    "cria_de_cerdo": oro_cria_de_cerdo,
    "negocios_en_reservas": oro_negocios_en_reservas,
    "unidades_en_reservas": oro_unidades_en_reservas,
}

if __name__ == "__main__":
    import importlib.util

    fuentes, salida = Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else "salida_equipo2")
    salida.mkdir(parents=True, exist_ok=True)
    raiz = Path(__file__).resolve().parents[2]
    for subtema, construir in ORO.items():
        spec = importlib.util.spec_from_file_location(subtema, raiz / "figures" / "2" / subtema / "figura.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        datos = construir(fuentes)
        fig = modulo.figura(datos)
        fig.write_html(salida / f"{subtema}.html", include_plotlyjs="cdn")
        try:
            fig.write_image(salida / f"{subtema}.png", scale=2)
        except Exception as e:  # Kaleido necesita Chrome; el HTML basta para revisar
            print(f"{subtema}: sin PNG ({e})")
        print(f"{subtema}: {len(datos)} filas")
