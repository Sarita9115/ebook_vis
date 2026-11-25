"""Proceso del equipo 6 (Dinámica empresarial).

ingesta >> plata >> oro >> validacion >> catalogo

Cada tarea corre los cinco subtemas con pipelines conectados, en este orden
(huella_construida reutiliza la malla de relieve_5m, por eso va después):

    gasto_publico, cambio_suelo, corredor_industrial, relieve_5m, huella_construida

- ingesta:    fuentes -> MinIO bronze/6/<subtema>/fecha=<ds>/
- plata:      bronce -> PostgreSQL plata.* (EPSG:32616) y COG en MinIO raster/6/relieve_5m/
- oro:        plata -> PostgreSQL oro."6.<subtema>" (EPSG:4326 cuando es mapa)
- validacion: cifra de oro contra valor_referencia ± tolerancia de catalog/catalog.csv,
              CRS, recorte a la península, metadatos y reglas de fuentes
- catalogo:   publica las filas del equipo 6 en oro.catalogo con su estado

Como el DAG de referencia del equipo 4, cada etapa corre en un entorno virtual
propio (PythonVirtualenvOperator, subclase de PythonOperator): Airflow 2.x fija
SQLAlchemy 1.4 y la imagen no trae geopandas. El entorno se crea en la primera
corrida y se reutiliza (/tmp/venv-equipo6). Hereda las variables de entorno
del scheduler: MINIO_*, ORO_DB_URL / DATABASE_URL / POSTGRES_* y, si se usan,
E6_GDRIVE_<SUBTEMA>.

Una etapa intenta todos los subtemas y falla al final si alguno falló, con el
detalle de cada uno en el log. Las cargas a plata y oro son transaccionales e
idempotentes (pipelines/6/_almacen.py). `validacion` guarda sus resultados por
corrida en plata."6.validacion" antes de fallar, para que `catalogo` (que corre
aunque la validación falle) registre también los rechazos y luego falle.

Parámetro `crudos_locales` (solo pruebas, vacío por omisión): carpeta con una
subcarpeta por subtema, que la ingesta sube a bronce en vez de descargar; por
ejemplo /opt/airflow/datos/6.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonVirtualenvOperator
from airflow.utils.trigger_rule import TriggerRule

SUBTEMAS = ["gasto_publico", "cambio_suelo", "corredor_industrial", "relieve_5m", "huella_construida"]
REQUISITOS = [
    "pandas>=2.2", "numpy>=1.26", "pyarrow>=15", "shapely>=2.0", "geopandas>=1.0", "pyogrio>=0.9",
    "sqlalchemy>=2.0", "psycopg2-binary>=2.9", "geoalchemy2>=0.15", "minio>=7.2", "openpyxl>=3.1",
    "requests>=2.31", "gdown>=5.1", "rasterio>=1.3",
]


def correr_etapa(etapa: str, subtemas: list, fecha: str = "", crudos_locales: str = "",
                 prefijos=None, run_id: str = ""):
    """Corre una etapa para cada subtema dentro del entorno virtual.

    Se ejecuta aislada (PythonVirtualenvOperator): todo lo que usa se importa aquí.
    """
    import importlib.util
    import logging
    import os
    import sys
    from pathlib import Path

    sys.dont_write_bytecode = True  # pipelines/ está montado en solo lectura
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("equipo6")
    carpeta = Path(os.environ.get("E6_PIPELINES_DIR", "/opt/airflow/pipelines/6"))

    def pipeline(subtema):
        nombre = f"e6_{subtema}"
        if nombre not in sys.modules:
            spec = importlib.util.spec_from_file_location(nombre, carpeta / f"{subtema}.py")
            modulo = importlib.util.module_from_spec(spec)
            sys.modules[nombre] = modulo
            spec.loader.exec_module(modulo)
        return sys.modules[nombre]

    prefijos = prefijos if isinstance(prefijos, dict) else {}
    alm = pipeline(subtemas[0]).alm

    if etapa == "catalogo":
        resultados = alm.leer_validacion(run_id)
        if not resultados:
            raise RuntimeError(f"No hay resultados de validación de la corrida {run_id}; no se publica el catálogo")
        bronce = {}
        for subtema in subtemas:
            for conjunto in (subtema, "relieve_5m"):  # huella_construida puede usar los crudos de relieve_5m
                resumen = alm.resumen_bronce(conjunto)
                if resumen:
                    bronce[f"{alm.EQUIPO}.{subtema}"] = resumen
                    break
        n = alm.publicar_catalogo(resultados, bronce)
        rechazados = sorted(v for v, r in resultados.items() if r["estado"] != "validado")
        if rechazados:
            raise RuntimeError(f"Catálogo publicado ({n} filas) con tablas rechazadas: {rechazados}")
        return n

    if etapa == "validacion":
        resultados = {}
        for subtema in subtemas:
            viz_id = f"{alm.EQUIPO}.{subtema}"
            try:
                resultados[viz_id] = alm.validar_oro(viz_id, pipeline(subtema).valor_referencia)
            except Exception as error:
                log.exception("[validacion] %s falló", viz_id)
                resultados[viz_id] = {"viz_id": viz_id, "estado": "rechazado", "valor_publicado": None,
                                      "motivos": [f"{type(error).__name__}: {error}"]}
            r = resultados[viz_id]
            log.info("[validacion] %s: %s (publicado %s, referencia %s ± %s) %s", viz_id, r["estado"],
                     r.get("valor_publicado"), r.get("valor_referencia"), r.get("tolerancia"),
                     "; ".join(r["motivos"]))
        alm.guardar_validacion(resultados, run_id)
        rechazados = sorted(v for v, r in resultados.items() if r["estado"] != "validado")
        if rechazados:
            raise RuntimeError(f"Tablas de oro rechazadas: {rechazados}")
        return {v: r["estado"] for v, r in resultados.items()}

    hechos, errores = {}, {}
    for subtema in subtemas:
        try:
            m = pipeline(subtema)
            if etapa == "ingesta":
                local = str(Path(crudos_locales) / subtema) if crudos_locales else None
                hechos[subtema] = m.ingesta(fecha=fecha or None, carpeta_local=local)
            elif etapa == "plata":
                hechos[subtema] = m.plata(prefijo=prefijos.get(subtema))
            elif etapa == "oro":
                hechos[subtema] = m.oro()
            else:
                raise ValueError(f"Etapa desconocida: {etapa}")
            log.info("[%s] %s.%s: %s", etapa, alm.EQUIPO, subtema, hechos[subtema])
        except Exception as error:  # se reportan todos juntos
            log.exception("[%s] %s.%s falló", etapa, alm.EQUIPO, subtema)
            errores[subtema] = f"{type(error).__name__}: {error}"
    if errores:
        raise RuntimeError(f"{etapa}: fallaron {len(errores)} subtemas: {errores}")
    return hechos


def etapa(task_id: str, horas: float, retries: int = 1,
          trigger_rule: str = TriggerRule.ALL_SUCCESS, **kwargs) -> PythonVirtualenvOperator:
    return PythonVirtualenvOperator(
        task_id=task_id,
        python_callable=correr_etapa,
        op_kwargs={"etapa": task_id, "subtemas": SUBTEMAS, **kwargs},
        requirements=REQUISITOS,
        system_site_packages=False,
        venv_cache_path="/tmp/venv-equipo6",
        execution_timeout=timedelta(hours=horas),
        retries=retries,
        trigger_rule=trigger_rule,
    )


with DAG(
    dag_id="equipo_6",
    description="Dinámica empresarial: bronce (MinIO) -> plata -> oro (PostGIS) -> validación -> catálogo",
    start_date=datetime(2026, 11, 19),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    render_template_as_native_obj=True,
    tags=["equipo-6"],
    default_args={"owner": "equipo-6", "retry_delay": timedelta(minutes=5)},
    params={"crudos_locales": Param("", type="string",
                                    description="Solo pruebas: carpeta con una subcarpeta por subtema "
                                                "(p. ej. /opt/airflow/datos/6). Vacío = descargar.")},
) as dag:
    ingesta = etapa("ingesta", 2, fecha="{{ ds }}", crudos_locales="{{ params.crudos_locales }}")
    plata = etapa("plata", 3, prefijos="{{ ti.xcom_pull(task_ids='ingesta') }}")
    oro = etapa("oro", 1)
    validacion = etapa("validacion", 0.5, retries=0, run_id="{{ run_id }}")
    # Corre aunque la validación falle, para registrar los rechazos; luego falla también.
    catalogo = etapa("catalogo", 0.5, retries=0, trigger_rule=TriggerRule.ALL_DONE, run_id="{{ run_id }}")
    ingesta >> plata >> oro >> validacion >> catalogo
