"""Proceso del equipo 4: medallion completo.

ingesta  fuentes (datos/4/ y descargas de INEGI) -> MinIO bronze/4/
plata    MinIO bronze/4/ -> PostgreSQL plata.*
oro      plata.* -> PostgreSQL oro.*  (lo que leen la web y el PDF)

Cada capa corre su script de pipelines/4/ en un entorno virtual propio (PythonVirtualenvOperator), porque
Airflow 2.x fija SQLAlchemy 1.4 y los pipelines usan SQLAlchemy 2. El entorno se crea en la primera corrida y
se reutiliza. `validacion` y `catalogo` quedan pendientes.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonVirtualenvOperator

PIPELINES = "/opt/airflow/pipelines/4"
REQUISITOS = ["pandas>=2.2", "sqlalchemy>=2.0", "psycopg2-binary>=2.9", "openpyxl>=3.1", "minio>=7.2"]


def correr_capa(script: str, funcion: str):
    """Carga pipelines/4/<script> y ejecuta su función principal; imprime lo que dejó la capa."""
    import importlib.util
    import sys

    sys.dont_write_bytecode = True  # pipelines/ está montado en solo lectura
    spec = importlib.util.spec_from_file_location(f"equipo4_{script[:-3]}", f"/opt/airflow/pipelines/4/{script}")
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
        venv_cache_path="/tmp/venv-equipo4",
    )


with DAG(
    dag_id="equipo_4",
    start_date=datetime(2026, 11, 19),
    schedule=None,
    catchup=False,
    tags=["equipo-4"],
) as dag:
    ingesta = capa("ingesta", "ingesta.py", "ingerir")
    plata = capa("plata", "plata.py", "construir")
    oro = capa("oro", "oro.py", "construir")
    validacion = EmptyOperator(task_id="validacion")
    catalogo = EmptyOperator(task_id="catalogo")
    ingesta >> plata >> oro >> validacion >> catalogo
