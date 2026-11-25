"""Proceso del equipo 5: medallion completo.

ingesta     fuentes (INEGI, CONEVAL, Cuenta Pública) -> MinIO bronze/5/
plata       MinIO bronze/5/ -> PostgreSQL plata."5.*"
oro         plata -> PostgreSQL oro."5.*"  (lo que leen las figuras)
validacion  revisa rangos y cobertura de oro
catalogo    deja oro."5.catalogo" con la procedencia de cada figura

Cada capa corre su script de pipelines/5/ en un entorno virtual propio (PythonVirtualenvOperator), porque
Airflow 2.x fija SQLAlchemy 1.4 y los pipelines usan SQLAlchemy

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator

REQUISITOS = ["pandas>=2.2", "sqlalchemy>=2.0", "psycopg2-binary>=2.9", "openpyxl>=3.1", "minio>=7.2"]


def correr_capa(script: str, funcion: str):
    """Carga pipelines/5/<script> y ejecuta su función principal; imprime lo que dejó la capa."""
    import importlib.util
    import sys

    sys.dont_write_bytecode = True  # pipelines/ está montado en solo lectura
    spec = importlib.util.spec_from_file_location(f"equipo5_{script[:-3]}", f"/opt/airflow/pipelines/5/{script}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    resultado = getattr(modulo, funcion)()
    for nombre, valor in resultado.items():
        print(nombre, "->", valor if isinstance(valor, str) else f"{len(valor)} filas")


def capa(task_id: str, script: str, funcion: str) -> PythonVirtualenvOperator:
    return PythonVirtualenvOperator(
        task_id=task_id,
        python_callable=correr_capa,
        op_args=[script, funcion],
        requirements=REQUISITOS,
        system_site_packages=False,
        venv_cache_path="/tmp/venv-equipo5",
    )


with DAG(
    dag_id="equipo_5",
    start_date=datetime(2026, 11, 19),
    schedule=None,
    catchup=False,
    tags=["equipo-5"],
) as dag:
    ingesta = capa("ingesta", "ingesta.py", "ingerir")
    plata = capa("plata", "plata.py", "construir")
    oro = capa("oro", "oro.py", "construir")
    validacion = capa("validacion", "validacion.py", "validar")
    catalogo = capa("catalogo", "catalogo.py", "publicar")
    ingesta >> plata >> oro >> validacion >> catalogo
