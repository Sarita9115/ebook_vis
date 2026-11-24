"""Proceso del equipo 4. La tarea `oro` publica las tablas en PostgreSQL; las demás quedan pendientes.

`oro` corre pipelines/4/oro.py en un entorno virtual propio (PythonVirtualenvOperator), porque Airflow 2.x fija
SQLAlchemy 1.4 y el pipeline usa SQLAlchemy 2. El entorno se crea en la primera corrida y se reutiliza.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonVirtualenvOperator


def publicar_oro():
    """Reconstruye las tablas de oro del equipo 4 y las publica en el esquema oro (una sola transacción)."""
    import importlib.util
    import sys

    sys.dont_write_bytecode = True  # pipelines/ está montado en solo lectura
    spec = importlib.util.spec_from_file_location("equipo4_oro", "/opt/airflow/pipelines/4/oro.py")
    oro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oro)
    for viz_id, df in oro.construir().items():
        print(f"oro.\"{viz_id}\": {len(df)} filas")


with DAG(
    dag_id="equipo_4",
    start_date=datetime(2026, 11, 19),
    schedule=None,
    catchup=False,
    tags=["equipo-4"],
) as dag:
    ingesta = EmptyOperator(task_id="ingesta")
    plata = EmptyOperator(task_id="plata")
    oro = PythonVirtualenvOperator(
        task_id="oro",
        python_callable=publicar_oro,
        requirements=["pandas>=2.2", "sqlalchemy>=2.0", "psycopg2-binary>=2.9", "openpyxl>=3.1"],
        system_site_packages=False,
        venv_cache_path="/tmp/venv-equipo4",
    )
    validacion = EmptyOperator(task_id="validacion")
    catalogo = EmptyOperator(task_id="catalogo")
    ingesta >> plata >> oro >> validacion >> catalogo
