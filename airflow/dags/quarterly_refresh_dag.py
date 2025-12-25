"""
Airflow DAG for quarterly data refresh.

This DAG runs quarterly to ingest fundamentals and reference data.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_platform.pipeline import PipelineRunner

# DAG configuration
DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "email": ["alerts@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=4),
}

dag = DAG(
    "quarterly_cross_asset_refresh",
    default_args=DEFAULT_ARGS,
    description="Quarterly refresh of fundamentals and reference data",
    schedule_interval="0 3 1 1,4,7,10 *",  # 3 AM on first day of Q1,Q2,Q3,Q4
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["data-platform", "quarterly", "cross-asset"],
)


def run_quarterly_refresh(**context) -> dict:
    """
    Run quarterly refresh task.
    
    Args:
        **context: Airflow context
        
    Returns:
        Dictionary with execution stats
    """
    runner = PipelineRunner()
    result = runner.run_quarterly()
    
    if not result.success:
        raise Exception(f"Quarterly refresh failed: {result.errors}")
    
    return {
        "records_loaded": result.records_loaded,
        "warnings": result.warnings,
    }


# Task: Run quarterly refresh
quarterly_task = PythonOperator(
    task_id="run_quarterly_refresh",
    python_callable=run_quarterly_refresh,
    dag=dag,
)
