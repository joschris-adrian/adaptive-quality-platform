from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/opt/airflow")

default_args = {"retries": 1, "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="report_dag",
    default_args=default_args,
    schedule_interval="@weekly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["reporting"],
) as dag:

    def generate_report():
        from dashboards.report_generator import ReportGenerator
        ReportGenerator().generate()

    PythonOperator(task_id="generate_weekly_report", python_callable=generate_report)