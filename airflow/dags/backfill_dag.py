"""
Airflow DAG for backfilling historical data.

This DAG is manually triggered to backfill historical data for a date range.
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
    "execution_timeout": timedelta(hours=6),
}

dag = DAG(
    "backfill_cross_asset_data",
    default_args=DEFAULT_ARGS,
    description="Backfill historical cross-asset market data",
    schedule_interval=None,  # Manual trigger only
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["data-platform", "backfill", "cross-asset"],
)


def run_backfill(**context) -> dict:
    """
    Run backfill task.
    
    Uses DAG run configuration for date range:
    {
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "chunk_size_days": 365,
        "tickers": ["^GSPC", "BTC-USD"]  # optional
    }
    
    Args:
        **context: Airflow context
        
    Returns:
        Dictionary with execution stats
    """
    # Get parameters from DAG run config
    dag_run = context["dag_run"]
    conf = dag_run.conf or {}
    
    start_date_str = conf.get("start_date")
    end_date_str = conf.get("end_date")
    chunk_size = conf.get("chunk_size_days", 365)
    tickers = conf.get("tickers")
    
    if not start_date_str or not end_date_str:
        raise ValueError(
            "Must provide 'start_date' and 'end_date' in DAG run config"
        )
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    runner = PipelineRunner()
    results = runner.run_backfill(
        start_date=start_date,
        end_date=end_date,
        chunk_size_days=chunk_size,
        tickers=tickers,
    )
    
    total_loaded = sum(r.records_loaded for r in results)
    failed_chunks = sum(1 for r in results if not r.success)
    
    if failed_chunks > 0:
        print(f"Warning: {failed_chunks} chunks failed")
    
    return {
        "total_chunks": len(results),
        "failed_chunks": failed_chunks,
        "total_records_loaded": total_loaded,
    }


# Task: Run backfill
backfill_task = PythonOperator(
    task_id="run_backfill",
    python_callable=run_backfill,
    dag=dag,
)
