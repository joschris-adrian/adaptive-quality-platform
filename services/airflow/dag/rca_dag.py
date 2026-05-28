from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/opt/airflow")

default_args = {"retries": 1, "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="rca_dag",
    default_args=default_args,
    schedule_interval="@hourly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["rca", "drift"],
) as dag:

    def run_rca():
        from services.rca.root_cause import RCAEngine
        from services.mlflow.tracking import log_drift_snapshot
        engine = RCAEngine()
        report = engine.report()
        log_drift_snapshot(report["trend"])
        if report["trend"].get("status") == "drift_detected":
            print(f"ALERT: drift detected — {report['trend']}")

    PythonOperator(task_id="run_rca_engine", python_callable=run_rca)