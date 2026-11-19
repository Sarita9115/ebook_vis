"""Proceso del equipo 5. Las tareas quedan pendientes hasta conectar los datos."""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="equipo_5",
    start_date=datetime(2026, 11, 19),
    schedule=None,
    catchup=False,
    tags=["equipo-5"],
) as dag:
    ingesta = EmptyOperator(task_id="ingesta")
    plata = EmptyOperator(task_id="plata")
    oro = EmptyOperator(task_id="oro")
    validacion = EmptyOperator(task_id="validacion")
    catalogo = EmptyOperator(task_id="catalogo")
    ingesta >> plata >> oro >> validacion >> catalogo
