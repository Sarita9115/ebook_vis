"""Datos de las figuras del equipo 2 que procesa Ingrid.

    2.ecosistemas   Los ecosistemas que protege la península
    2.fauna_nom059  La fauna de la península, en tu espacio (jaguar y manatí)

Cada subtema tiene dos funciones:

    ingesta_<subtema>(ruta)   sube el archivo crudo al bronce (MinIO, bucket `bronze`,
                              prefijo `2/<dataset>/fecha=AAAA-MM-DD/`), sin transformarlo.
    oro_<subtema>(origen)     deja la tabla de oro lista para `figura(datos)`.

Uso para revisar en local (con `docker compose up -d minio minio-init` si quieres subir):

    python pipelines/2/oro_ingrid.py ruta/a/listado_anp.csv            # ecosistemas: arma el oro
    python pipelines/2/oro_ingrid.py ruta/a/listado_anp.csv --bronce   # además sube a MinIO
    python pipelines/2/oro_ingrid.py fauna jaguar.glb manati.glb       # fauna: arma el oro
    python pipelines/2/oro_ingrid.py fauna jaguar.glb manati.glb --bronce

Los CSV y los GLB no se versionan en Git.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import sys
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RESPONSABLE = "Ingrid Castillo"
EQUIPO = "2"

# ----------------------------------------------------------------------- conexión a MinIO


def _env() -> dict:
    """Variables de entorno; si faltan, las del `.env` de la raíz (el de docker compose)."""
    valores = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip("'\"")
    return {**valores, **os.environ}


def _minio():
    from minio import Minio  # se importa aquí para poder armar el oro sin MinIO

    e = _env()
    return Minio(e.get("MINIO_ENDPOINT", "localhost:9000"), access_key=e.get("MINIO_ROOT_USER"),
                 secret_key=e.get("MINIO_ROOT_PASSWORD"), secure=False)


def _subir(dataset: str, ruta: Path, origen: str, nombre: str | None = None,
           bucket: str = "bronze") -> str:
    """Sube el archivo tal cual a `bronze/2/<dataset>/fecha=AAAA-MM-DD/<archivo>`.

    Es idempotente: si ya hay un objeto con el mismo contenido (sha256) no lo vuelve a subir.
    """
    contenido = Path(ruta).read_bytes()
    nombre = nombre or Path(ruta).name
    sha = hashlib.sha256(contenido).hexdigest()
    cliente = _minio()
    if not cliente.bucket_exists(bucket):
        raise RuntimeError(f"No existe el bucket {bucket}; levanta minio y minio-init del compose.")
    prefijo = f"{EQUIPO}/{dataset}/"
    for obj in cliente.list_objects(bucket, prefix=prefijo, recursive=True):
        if obj.object_name.endswith("/" + nombre):
            meta = cliente.stat_object(bucket, obj.object_name).metadata or {}
            if meta.get("x-amz-meta-sha256") == sha:
                return f"{bucket}/{obj.object_name} (sin cambios)"
    objeto = f"{prefijo}fecha={date.today().isoformat()}/{nombre}"
    cliente.put_object(bucket, objeto, io.BytesIO(contenido), len(contenido),
                       metadata={"fecha-obtencion": date.today().isoformat(),
                                 "origen": origen, "sha256": sha})
    return f"{bucket}/{objeto} (subido)"


# ----------------------------------------------------------------------- utilidades


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def _procedencia(df: pd.DataFrame, viz_id: str, primaria: str, secundaria: str,
                 institucion: str) -> pd.DataFrame:
    df = df.copy()
    df["viz_id"] = viz_id
    df["fuente_primaria"] = primaria
    df["fuente_secundaria"] = secundaria
    df["institucion"] = institucion
    df["fecha_obtencion"] = date.today().isoformat()
    df["responsable"] = RESPONSABLE
    return df


# ----------------------------------------------------------------------- 2.ecosistemas

ANP_PRIMARIA = ("https://www.datos.gob.mx/dataset/informacion_monitoreo_evaluacion_para_conservacion"
                "/resource/fd923799-1d5b-4a34-91f7-f66d7440a118")
ANP_SECUNDARIA = ("https://historico.datos.gob.mx/busca/dataset/simec/resource/"
                  "489f051b-8d8a-4d86-8c00-7f03949e70dd")

ESTADOS_PENINSULA = ("campeche", "yucatan", "quintana roo")
REGION_PENINSULA = "peninsula de yucatan"

# Códigos de categoría de manejo de la CONANP, para que el hover diga algo legible.
CAT_MANEJO = {
    "RB": "Reserva de la Biosfera",
    "PN": "Parque Nacional",
    "APFF": "Área de Protección de Flora y Fauna",
    "APRN": "Área de Protección de Recursos Naturales",
    "MN": "Monumento Natural",
    "SANT": "Santuario",
}


def ingesta_ecosistemas(ruta: str | Path) -> str:
    """Sube el CSV nacional de ANP al bronce: bronze/2/anp_listado/fecha=.../"""
    return _subir("anp_listado", Path(ruta), ANP_PRIMARIA)


def oro_ecosistemas(origen: str | Path | io.BytesIO) -> pd.DataFrame:
    """Tabla de oro de 2.ecosistemas: una fila por ANP de la península.

    El CSV de CONANP es nacional (232 ANP). Aquí se recorta a Campeche, Yucatán y
    Quintana Roo: una ANP entra si su `estado` nombra alguno de los tres o si su
    `region` es la Península de Yucatán. Las ANP marinas gigantes se quedan en la tabla;
    la figura es la que excluye las tres más extensas y toma las 10 mayores.

    Columnas: nombre, cat_manejo, estado, sup_ha, sterr_ha, smar_ha, más la procedencia.
    """
    df = pd.read_csv(origen, encoding="utf-8")
    for c in ("sup_ha", "sterr_ha", "smar_ha"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["sup_ha"])

    estado = df["estado"].fillna("").map(_norm)
    region = df["region"].fillna("").map(_norm)
    en_estados = estado.map(lambda e: any(x in e for x in ESTADOS_PENINSULA))
    en_region = region.str.contains(REGION_PENINSULA, regex=False)
    df = df[en_estados | en_region].copy()

    df["cat_manejo"] = df["cat_manejo"].map(lambda c: CAT_MANEJO.get(str(c).strip(), c))
    df["sterr_ha"] = df["sterr_ha"].fillna(0)
    df["smar_ha"] = df["smar_ha"].fillna(0)

    df = df[["nombre", "cat_manejo", "estado", "sup_ha", "sterr_ha", "smar_ha"]]
    df = df.sort_values("sup_ha", ascending=False).reset_index(drop=True)
    return _procedencia(df, "2.ecosistemas", ANP_PRIMARIA, ANP_SECUNDARIA, "CONANP")



# ----------------------------------------------------------------------- 2.fauna_nom059

GLB_JAGUAR = "https://static.poly.pizza/4866ebc9-2633-4356-b1e7-b74627e5cbd4.glb"
GLB_MANATI = "https://static.poly.pizza/6a03a835-2d9e-4694-8ab0-f308a22724c0.glb"
NOM059_PDF = "https://www.profepa.gob.mx/innovaportal/file/435/1/NOM_059_SEMARNAT_2010.pdf"

# Categoría de riesgo en la NOM-059-SEMARNAT-2010 (P = en peligro de extinción).
FAUNA = [
    ("Jaguar", "Panthera onca", "P", GLB_JAGUAR),
    ("Manatí", "Trichechus manatus", "P", GLB_MANATI),
]

_TIPOS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_COMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _leer_glb(ruta):
    b = Path(ruta).read_bytes() if not isinstance(ruta, (bytes, bytearray)) else bytes(ruta)
    magic, _, _ = struct.unpack("<4sII", b[:12])
    if magic != b"glTF":
        raise ValueError(f"{ruta} no es un GLB")
    off, js, binario = 12, None, b""
    while off < len(b):
        n, tipo = struct.unpack("<II", b[off:off + 8])
        trozo = b[off + 8:off + 8 + n]
        if tipo == 0x4E4F534A:
            js = json.loads(trozo)
        elif tipo == 0x004E4942:
            binario = trozo
        off += 8 + n
    return js, binario


def _accesor(js, binario, i):
    a = js["accessors"][i]
    vista = js["bufferViews"][a["bufferView"]]
    dtype = np.dtype(_TIPOS[a["componentType"]])
    k = _COMP[a["type"]]
    ini = vista.get("byteOffset", 0) + a.get("byteOffset", 0)
    paso = vista.get("byteStride") or dtype.itemsize * k
    bruto = np.frombuffer(binario, dtype=np.uint8, count=a["count"] * paso, offset=ini) if paso != dtype.itemsize * k \
        else None
    if bruto is None:
        datos = np.frombuffer(binario, dtype=dtype, count=a["count"] * k, offset=ini)
    else:
        filas = bruto.reshape(a["count"], paso)[:, :dtype.itemsize * k].copy()
        datos = filas.view(dtype).reshape(-1)
    return datos.reshape(a["count"], k) if k > 1 else datos


def _matriz_nodo(n):
    if "matrix" in n:
        return np.array(n["matrix"], float).reshape(4, 4).T
    m = np.eye(4)
    if "scale" in n:
        m = np.diag([*n["scale"], 1.0]) @ m
    if "rotation" in n:
        x, y, z, w = n["rotation"]
        r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        t = np.eye(4); t[:3, :3] = r
        m = t @ m
    if "translation" in n:
        t = np.eye(4); t[:3, 3] = n["translation"]
        m = t @ m
    return m


def malla_glb(ruta):
    """Lee un GLB y devuelve x, y, z (Z arriba), triángulos y el color de cada cara.

    Solo necesita numpy y Pillow. El color de cada cara sale de la textura del modelo,
    muestreada en el centro de cada triángulo (Plotly no dibuja texturas de imagen).
    """
    from PIL import Image

    js, binario = _leer_glb(ruta)
    escena = js["scenes"][js.get("scene", 0)]
    pila = [(i, np.eye(4)) for i in escena["nodes"]]
    vs, fs, cs, base = [], [], [], 0
    while pila:
        i, padre = pila.pop()
        nodo = js["nodes"][i]
        m = padre @ _matriz_nodo(nodo)
        pila += [(c, m) for c in nodo.get("children", [])]
        if "mesh" not in nodo:
            continue
        for p in js["meshes"][nodo["mesh"]]["primitives"]:
            if p.get("mode", 4) != 4:
                continue
            pos = _accesor(js, binario, p["attributes"]["POSITION"]).astype(float)
            pos = (np.c_[pos, np.ones(len(pos))] @ m.T)[:, :3]
            tri = (_accesor(js, binario, p["indices"]).astype(np.int64) if "indices" in p
                   else np.arange(len(pos))).reshape(-1, 3)
            mat = js["materials"][p["material"]] if "material" in p else {}
            pbr = mat.get("pbrMetallicRoughness", {})
            factor = np.array(pbr.get("baseColorFactor", [1, 1, 1, 1])[:3])
            if "baseColorTexture" in pbr and "TEXCOORD_0" in p["attributes"]:
                tex = js["textures"][pbr["baseColorTexture"]["index"]]
                img = js["images"][tex["source"]]
                vista = js["bufferViews"][img["bufferView"]]
                ini = vista.get("byteOffset", 0)
                im = Image.open(io.BytesIO(binario[ini:ini + vista["byteLength"]])).convert("RGB")
                px = np.asarray(im, dtype=float) / 255.0
                uv = _accesor(js, binario, p["attributes"]["TEXCOORD_0"]).astype(float)
                c = uv[tri].mean(axis=1)                       # centro de cada triángulo
                u = np.clip((c[:, 0] % 1.0) * (px.shape[1] - 1), 0, px.shape[1] - 1).round().astype(int)
                v = np.clip((c[:, 1] % 1.0) * (px.shape[0] - 1), 0, px.shape[0] - 1).round().astype(int)
                color = px[v, u] * factor
            else:
                color = np.tile(factor, (len(tri), 1))
            vs.append(pos); fs.append(tri + base); cs.append(color)
            base += len(pos)
    v = np.vstack(vs); f = np.vstack(fs); c = np.vstack(cs)
    x, y, z = v[:, 0], -v[:, 2], v[:, 1]                       # glTF es Y arriba; Plotly, Z arriba
    return dict(x=x, y=y, z=z, i=f[:, 0], j=f[:, 1], k=f[:, 2],
                colores_cara=(c * 255).round().astype(int))


def ingesta_fauna(glb_jaguar: str | Path, glb_manati: str | Path) -> list[str]:
    """Sube los dos GLB al bronce: bronze/2/modelos_fauna/fecha=.../{jaguar,manati}.glb"""
    return [_subir("modelos_fauna", Path(glb_jaguar), GLB_JAGUAR, nombre="jaguar.glb"),
            _subir("modelos_fauna", Path(glb_manati), GLB_MANATI, nombre="manati.glb")]


def oro_fauna_nom059(glb_jaguar: str | Path, glb_manati: str | Path) -> pd.DataFrame:
    """Tabla de oro de 2.fauna_nom059: una fila por especie, con su malla 3D.

    Columnas: nombre, cientifico, categoria, x, y, z (vértices, Z arriba), i, j, k
    (índices de cada triángulo), colores_cara ([r, g, b] por triángulo), más la procedencia.
    """
    archivos = {"Jaguar": glb_jaguar, "Manatí": glb_manati}
    filas = []
    for nombre, cientifico, categoria, _ in FAUNA:
        malla = malla_glb(archivos[nombre])
        fila = {"nombre": nombre, "cientifico": cientifico, "categoria": categoria}
        fila.update({k: v.tolist() for k, v in malla.items()})
        filas.append(fila)
    return _procedencia(pd.DataFrame(filas), "2.fauna_nom059", f"{GLB_JAGUAR}; {GLB_MANATI}",
                        NOM059_PDF, "poly.pizza / SEMARNAT")


# ----------------------------------------------------------------------- uso local

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "fauna":
        if len(sys.argv) < 4:
            raise SystemExit("Uso: python pipelines/2/oro_ingrid.py fauna jaguar.glb manati.glb [--bronce]")
        datos = oro_fauna_nom059(sys.argv[2], sys.argv[3])
        print(f"oro_fauna_nom059: {len(datos)} especies")
        for _, f in datos.iterrows():
            print(f"  {f['nombre']:8s} {f['cientifico']:20s} categoria={f['categoria']}  "
                  f"vertices={len(f['x'])}  triangulos={len(f['i'])}")
        if "--bronce" in sys.argv:
            print(*ingesta_fauna(sys.argv[2], sys.argv[3]), sep="\n")
    else:
        ruta = Path(sys.argv[1])
        datos = oro_ecosistemas(ruta)
        print(f"oro_ecosistemas: {len(datos)} ANP en la península")
        print(datos[["nombre", "sup_ha", "sterr_ha", "smar_ha"]].head(14).to_string(index=False))
        if "--bronce" in sys.argv:
            print(ingesta_ecosistemas(ruta))