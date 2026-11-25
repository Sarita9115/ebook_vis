"""Equipo 2 · Oro: de plata (PostgreSQL, esquema `plata`) a la tabla que dibuja cada figura (esquema `oro`).

Oro lee solo de plata, nunca del bronce ni de una carpeta. Una tabla por visualización, con el `viz_id` como
nombre. Las de Esaú:

    oro."2.herbario_cicy"          Herbario CICY, plantas vasculares
    oro."2.cria_de_cerdo"          Impacto por municipio ocasionado por la cría de cerdo en la península
    oro."2.negocios_en_reservas"   Cada tipo de negocio situado en cada reserva natural
    oro."2.unidades_en_reservas"   Unidades económicas de impacto ambiental o relación con la biodiversidad

Los mapas guardan su geometría en EPSG:4326 (PostGIS) y `leer()` los devuelve como GeoDataFrame. Cada tabla lleva
las columnas de procedencia (viz_id, fuentes, institución, fecha de obtención del bronce y responsable).
Para sumar los subtemas de Ingrid basta con agregar su función a `CONSTRUCTORES`.

Flujo completo:  python pipelines/2/ingesta.py   # revisa / refresca bronze/2/
                 python pipelines/2/plata.py     # bronce -> plata."2.*"
                 python pipelines/2/oro.py       # plata."2.*" -> oro."2.*"
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd


def _cargar(nombre: str):
    clave = f"equipo2_{nombre}"
    if clave not in sys.modules:
        spec = importlib.util.spec_from_file_location(clave, Path(__file__).with_name(f"{nombre}.py"))
        sys.modules[clave] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules[clave]


comun = _cargar("comun")
plata = _cargar("plata")
ESQUEMA = "oro"
CRS_M = "EPSG:32616"
CRS_WEB = "EPSG:4326"
ENTIDADES = {"04": "Campeche", "23": "Quintana Roo", "31": "Yucatán"}
RESPONSABLE = "Esaú Palomo"
SIMPLIFICA_M = 400        # tolerancia para simplificar polígonos antes de publicarlos
TEMAS = plata.TEMAS
_norm = plata.norm

# fuentes de cada visualización y datasets de bronce de los que sale su fecha de obtención
META = {
    "2.herbario_cicy": dict(
        fuente_primaria="Herbario CICY, colectas de plantas vasculares",
        fuente_secundaria="SEMARNAT, NOM-059-SEMARNAT-2010; INEGI, Censo Agropecuario 2022 y DENUE",
        institucion="CICY", datasets=["cicy_flora", "censo_agropecuario", "denue"]),
    "2.cria_de_cerdo": dict(
        fuente_primaria="INEGI, Censo Agropecuario 2022 (cuadros ca2022_gan24 y ca2022_gan25)",
        fuente_secundaria="CONANP, Áreas Naturales Protegidas federales",
        institucion="INEGI", datasets=["censo_agropecuario", "anp_conanp", "marco_geo"]),
    "2.negocios_en_reservas": dict(
        fuente_primaria="INEGI, DENUE (corte vigente, península)",
        fuente_secundaria="CONANP, Áreas Naturales Protegidas federales",
        institucion="INEGI", datasets=["denue", "anp_conanp", "marco_geo"]),
    "2.unidades_en_reservas": dict(
        fuente_primaria="CONANP, Áreas Naturales Protegidas federales",
        fuente_secundaria="INEGI, DENUE (corte vigente, península)",
        institucion="CONANP", datasets=["anp_conanp", "denue", "marco_geo"]),
}


def _plata(nombre: str):
    return comun.leer_tabla("plata", nombre)


def _procedencia(df: pd.DataFrame, viz_id: str) -> pd.DataFrame:
    m = META[viz_id]
    bronce = _plata("2.bronce_archivos")
    fechas = bronce.loc[bronce["dataset"].isin(m["datasets"]), "fecha_obtencion"]
    df = df.copy()
    df["viz_id"] = viz_id
    df["fuente_primaria"] = m["fuente_primaria"]
    df["fuente_secundaria"] = m["fuente_secundaria"]
    df["institucion"] = m["institucion"]
    df["fecha_obtencion"] = fechas.max() if len(fechas) else date.today().isoformat()
    df["responsable"] = RESPONSABLE
    return df


def _simplifica_web(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.to_crs(CRS_M).copy()
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFICA_M, preserve_topology=True)
    return gdf.to_crs(CRS_WEB)


# ---------------------------------------------------------------------- capas comunes (desde plata)


def _municipios() -> gpd.GeoDataFrame:
    return _plata("2.municipios").to_crs(CRS_M)


def _reservas() -> gpd.GeoDataFrame:
    return _plata("2.anp").to_crs(CRS_M)


def _contexto(mun: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Países vecinos y contorno de los tres estados, como capa de fondo."""
    vecinos = _plata("2.vecinos").to_crs(CRS_M)[["geometry"]].assign(tipo="vecino", nombre="")
    estados = mun.dissolve("CVE_ENT").reset_index()
    estados["geometry"] = estados.buffer(300).buffer(-300)
    estados = estados[["CVE_ENT", "geometry"]].assign(tipo="estado", nombre=estados["CVE_ENT"].map(ENTIDADES))
    return gpd.GeoDataFrame(pd.concat([vecinos, estados[["tipo", "nombre", "geometry"]]]), crs=CRS_M)


def _censo_porcino() -> pd.DataFrame:
    return _plata("2.censo_porcino")


def _negocios(anp: gpd.GeoDataFrame, max_km: float | None) -> gpd.GeoDataFrame:
    """Cada negocio del DENUE con tema se asigna a su reserva más cercana; se quedan los de menos de `max_km`."""
    neg = _plata("2.denue_impacto").to_crs(CRS_M)
    cruce = gpd.sjoin_nearest(neg, anp[["NOMBRE", "geometry"]], distance_col="dist_m")
    cruce = cruce[~cruce.index.duplicated()]
    return cruce if max_km is None else cruce[cruce["dist_m"] <= max_km * 1000]


# ------------------------------------------------------------- burbujas

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


def oro_cria_de_cerdo() -> gpd.GeoDataFrame:
    """Una fila por geometría, separada por `tipo`:

    municipio  cve_ent, nombre, cerdos, unidades, cerdos_por_unidad, granja_grande, geometry
    reserva    nombre, cerdos_entorno, municipios_entorno, municipio_top, cerdos_municipio_top, geometry
    franja     geometry (contorno de las franjas de 10 km alrededor de las reservas)
    vecino / estado   capas de contexto
    """
    mun = _municipios().merge(_censo_porcino()[["key", "cerdos", "unidades"]], on="key", how="left")
    mun[["cerdos", "unidades"]] = mun[["cerdos", "unidades"]].fillna(0).astype(int)
    mun["cerdos_por_unidad"] = (mun["cerdos"] / mun["unidades"].where(mun["unidades"] > 0)).fillna(0)
    mun["granja_grande"] = (mun["cerdos_por_unidad"] >= GRANJA_GRANDE) & (mun["cerdos"] >= MIN_CERDOS)
    anp = _reservas()

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
    oro = gpd.GeoDataFrame(pd.concat([municipios, reservas, franja, _contexto(mun)], ignore_index=True), crs=CRS_M)
    oro["granja_grande"] = oro["granja_grande"].fillna(False).astype(bool)   # sin nulos al pasar a PostgreSQL
    return _procedencia(_simplifica_web(oro), "2.cria_de_cerdo")


# ------------------------------------------------- 2.negocios_en_reservas y unidades


def _oro_burbujas(por_tema: bool) -> gpd.GeoDataFrame:
    mun = _municipios()
    anp = _reservas()
    cerca = _negocios(anp, CERCA_KM)
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
    capas = gpd.GeoDataFrame(pd.concat([capas, _contexto(mun)], ignore_index=True), crs=CRS_M)
    capas = _simplifica_web(capas)
    oro = pd.concat([burbujas, capas], ignore_index=True)
    return gpd.GeoDataFrame(oro, geometry="geometry", crs=CRS_WEB)


def oro_negocios_en_reservas() -> gpd.GeoDataFrame:
    """burbuja: reserva, tema, negocios (a menos de 5 km), lon, lat, ancla_lon, ancla_lat; resto: polígonos de fondo."""
    return _procedencia(_oro_burbujas(por_tema=True), "2.negocios_en_reservas")


def oro_unidades_en_reservas() -> gpd.GeoDataFrame:
    """burbuja: reserva, negocios (a menos de 5 km), tema_principal, lon, lat, ancla_lon, ancla_lat; resto: fondo."""
    return _procedencia(_oro_burbujas(por_tema=False), "2.unidades_en_reservas")


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


def oro_herbario_cicy() -> pd.DataFrame:
    """Una fila por estado y planta conocida: estado, nombre_comun, especie, registros, frac_presion, nom059,
    nivel, especies_estado, frac_presion_estado, municipios_presion."""
    # municipios con mucha presión: muchos cerdos o muchos negocios que pueden dañar la naturaleza
    cerdos = _censo_porcino().set_index("key")["cerdos"]
    mun = _municipios()
    todos = _plata("2.denue_impacto").to_crs(CRS_M).sjoin(mun[["key", "geometry"]], predicate="within")
    negocios = todos["key"].value_counts()
    presion = set(cerdos[cerdos >= UMBRAL_CERDOS].index) | set(negocios[negocios >= UMBRAL_NEGOCIOS].index)

    flora = _plata("2.cicy_flora")
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
    return _procedencia(sel, "2.herbario_cicy")


# --------------------------------------------------------------------------- publicación

CONSTRUCTORES = {
    "2.herbario_cicy": oro_herbario_cicy,
    "2.cria_de_cerdo": oro_cria_de_cerdo,
    "2.negocios_en_reservas": oro_negocios_en_reservas,
    "2.unidades_en_reservas": oro_unidades_en_reservas,
}


def construir(*viz_ids: str) -> dict[str, pd.DataFrame]:
    """Reconstruye las tablas de oro pedidas (todas si no se indica ninguna) y las publica en el esquema oro.

    Primero se calculan en memoria; después se escriben en una sola transacción: o se confirman todas o
    PostgreSQL no queda con cambios parciales. Es idempotente: cada ejecución reemplaza las tablas.
    """
    tablas = {v: CONSTRUCTORES[v]() for v in (viz_ids or CONSTRUCTORES)}
    comun.escribir(ESQUEMA, tablas)
    return tablas


def leer(viz_id: str) -> pd.DataFrame:
    """Lee la tabla de oro vigente desde PostgreSQL; si no existe todavía, la construye desde plata."""
    try:
        return comun.leer_tabla(ESQUEMA, viz_id)
    except LookupError:
        return construir(viz_id)[viz_id]


if __name__ == "__main__":
    for v, df in construir().items():
        print(f'{ESQUEMA}."{v}"{"":{26 - len(v)}} {len(df):5} filas  ({date.today()})')
