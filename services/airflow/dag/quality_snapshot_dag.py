from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, "/opt/airflow")

default_args = {"retries": 2, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="quality_snapshot_dag",
    default_args=default_args,
    schedule_interval="*/15 * * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["quality", "snapshot"],
) as dag:

    def write_snapshot():
        from dashboards.snapshot_writer import SnapshotWriter
        SnapshotWriter().write()

    PythonOperator(task_id="write_quality_snapshot", python_callable=write_snapshot)