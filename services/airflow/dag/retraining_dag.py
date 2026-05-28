from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/opt/airflow")

default_args = {"retries": 1, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="retraining_dag",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["retraining", "classifier"],
) as dag:

    def check_and_retrain():
        from services.rca.root_cause import RCAEngine
        engine = RCAEngine()
        emerging = engine.emerging_categories(window_size=50)
        if len(emerging) > 0:
            print(f"Emerging categories detected: {emerging} — triggering retraining")
            import subprocess
            subprocess.run(["python", "scripts/train_classifier.py"], check=True)
        else:
            print("No emerging categories — skipping retraining")

    PythonOperator(task_id="check_and_retrain", python_callable=check_and_retrain)