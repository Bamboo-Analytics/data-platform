"""
Airflow DAG for daily cross-asset data ingestion.

This DAG runs daily to ingest the latest data for all configured sources.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.dates import days_ago

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_platform.pipeline import PipelineRunner
from data_platform.config import get_config

# DAG configuration
DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "email": ["alerts@example.com"],  # Configure your email
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=2),
}

dag = DAG(
    "daily_cross_asset_ingestion",
    default_args=DEFAULT_ARGS,
    description="Daily ingestion of cross-asset market data",
    schedule_interval="0 2 * * *",  # 2 AM daily (after markets close)
    start_date=days_ago(1),
    catchup=False,  # Don't backfill automatically
    max_active_runs=1,
    tags=["data-platform", "daily", "cross-asset"],
)


def run_daily_ingestion(**context) -> dict:
    """
    Run daily ingestion task.
    
    Args:
        **context: Airflow context
        
    Returns:
        Dictionary with execution stats
    """
    execution_date = context["execution_date"]
    
    # Ingest data for the execution date
    start_date = execution_date.date()
    end_date = start_date
    
    runner = PipelineRunner()
    result = runner.run_daily(start_date=start_date, end_date=end_date)
    
    if not result.success:
        raise Exception(f"Daily ingestion failed: {result.errors}")
    
    return {
        "records_extracted": result.records_extracted,
        "records_loaded": result.records_loaded,
        "warnings": result.warnings,
    }


def check_data_quality(**context) -> None:
    """
    Check data quality after ingestion.
    
    Args:
        **context: Airflow context
    """
    # Pull stats from previous task
    ti = context["ti"]
    stats = ti.xcom_pull(task_ids="ingest_daily_data")
    
    if stats["records_loaded"] == 0:
        raise Exception("No records loaded")
    
    if stats["warnings"]:
        print(f"Warnings: {stats['warnings']}")


def send_success_notification(**context) -> None:
    """
    Send success notification.
    
    Args:
        **context: Airflow context
    """
    ti = context["ti"]
    stats = ti.xcom_pull(task_ids="ingest_daily_data")
    
    print(f"Daily ingestion completed successfully!")
    print(f"Records loaded: {stats['records_loaded']}")
    
    # TODO: Send to Slack, email, or monitoring system


# Task 1: Ingest daily data
ingest_task = PythonOperator(
    task_id="ingest_daily_data",
    python_callable=run_daily_ingestion,
    dag=dag,
)

# Task 2: Check data quality
quality_check_task = PythonOperator(
    task_id="check_data_quality",
    python_callable=check_data_quality,
    dag=dag,
)

# Task 3: Send success notification
notification_task = PythonOperator(
    task_id="send_success_notification",
    python_callable=send_success_notification,
    dag=dag,
)

# Define task dependencies
ingest_task >> quality_check_task >> notification_task
