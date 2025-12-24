# Migration Guide: From Dev Scripts to Production Pipeline

This guide explains how to migrate from the old ad-hoc data fetching functions in `dev/cross_asset_and_sentiment/cross_asset.py` to the new production pipeline.

## Overview

### Before (Old Approach)
- Functions scattered in development folder
- Manual execution via Jupyter notebooks
- No data persistence or validation
- Hard-coded parameters
- No error handling or retries
- No deduplication or versioning

### After (New Approach)
- Structured pipeline with ETL separation
- Automated Airflow orchestration
- ClickHouse storage with `(date, ticker)` primary key
- YAML configuration
- Comprehensive error handling and retries
- Automatic deduplication with versioning

## Migration Steps

### Step 1: Install New Dependencies

```bash
cd /Users/buinhatquang/Desktop/data-platform

# Sync dependencies
uv sync

# Install additional required packages
uv add clickhouse-connect pydantic pydantic-settings pyyaml pandera tenacity typer rich python-json-logger python-dotenv
```

### Step 2: Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit with your ClickHouse credentials
nano .env
```

Add to `.env`:
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=your_password
CLICKHOUSE_DATABASE=data_platform
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Step 3: Initialize ClickHouse Database

```bash
# Option 1: Using CLI (recommended)
data-platform init-db

# Option 2: Manual DDL execution
clickhouse-client --multiquery < schema/clickhouse_ddl.sql
```

Verify tables created:
```sql
SHOW TABLES FROM data_platform;
-- Should show: daily_features, quarterly_features
```

### Step 4: Configure Data Sources

The old functions are already mapped to the new configuration in `config/sources.yaml`:

**Old → New Mapping:**

| Old Function | New Config Entry | Notes |
|-------------|------------------|-------|
| `get_sp500_return()` | `sp500` source | ticker: `^GSPC` |
| `get_sector_etf_returns()` | `xlk_tech`, `xlf_financials`, `xle_energy` | 3 separate sources |
| `get_oil_price()` | `wti_oil` source | ticker: `CL=F` |
| `get_gold_price()` | `gold` source | ticker: `GC=F` |
| `get_usd_index()` | `dxy` source | ticker: `DX-Y.NYB` |
| `get_btc_correlation()` | `bitcoin` source | includes correlation feature |
| `get_treasury_yields()` | `treasury_3m`, `treasury_10y` | multiple tickers |
| `get_credit_spreads()` | `hyg_high_yield`, `lqd_investment_grade` | separate sources |
| `get_fx_pairs()` | Individual FX sources | `eurusd`, `usdjpy`, etc. |

All sources are already configured in `config/sources.yaml`. Review and enable/disable as needed:

```yaml
daily_sources:
  - name: "sp500"
    enabled: true  # Set to false to disable
    # ... rest of config
```

### Step 5: Backfill Historical Data

Run a backfill to populate ClickHouse with historical data:

```bash
# Start with a test (1 month)
data-platform backfill \
  --start-date 2024-11-01 \
  --end-date 2024-11-30 \
  --chunk-size 30

# If successful, backfill full history (5 years as in old code)
data-platform backfill \
  --start-date 2019-12-21 \
  --end-date 2024-12-21 \
  --chunk-size 365
```

Monitor progress:
```sql
-- Check ingestion progress
SELECT
    toYYYYMM(date) AS month,
    count(DISTINCT ticker) AS tickers,
    count(*) AS records
FROM data_platform.daily_features
GROUP BY month
ORDER BY month DESC;
```

### Step 6: Validate Data Quality

Compare old function outputs with new pipeline data:

```python
# Create validation script: validate_migration.py
from datetime import date, datetime, timedelta
from dev.cross_asset_and_sentiment.cross_asset import get_sp500_return
from data_platform.storage import ClickHouseClient

# Fetch from old function
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
old_data = get_sp500_return(start_date, end_date)

# Fetch from ClickHouse
with ClickHouseClient() as client:
    new_data = client.query_daily_facts(
        ticker="^GSPC",
        start_date=start_date.date(),
        end_date=end_date.date(),
    )

# Compare values
# ... comparison logic
```

Expected differences:
- ✅ **Timestamps**: Old data has no ingestion metadata; new data tracks lineage
- ✅ **Structure**: Old data is DataFrame; new data is structured records
- ⚠️ **Values**: Should match within floating-point precision
- ⚠️ **Dates**: Should cover same range (may differ for weekends/holidays)

### Step 7: Set Up Airflow (Optional but Recommended)

```bash
# Install Airflow
uv add --optional airflow apache-airflow

# Set Airflow home
export AIRFLOW_HOME=/Users/buinhatquang/Desktop/data-platform/airflow

# Initialize Airflow DB
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com

# Copy DAGs (already in place)
# airflow/dags/ contains: daily_ingestion_dag.py, backfill_dag.py, quarterly_refresh_dag.py

# Start Airflow services
airflow webserver --port 8080 &
airflow scheduler &
```

Access UI: http://localhost:8080

Enable `daily_cross_asset_ingestion` DAG for automatic daily updates.

### Step 8: Update Downstream Code

Replace old function calls with ClickHouse queries:

**Before:**
```python
from dev.cross_asset_and_sentiment.cross_asset import get_sp500_return
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=30)
df = get_sp500_return(start_date, end_date)
```

**After:**
```python
from data_platform.storage import ClickHouseClient
from datetime import date, timedelta

end_date = date.today()
start_date = end_date - timedelta(days=30)

with ClickHouseClient() as client:
    records = client.query_daily_facts(
        ticker="^GSPC",
        start_date=start_date,
        end_date=end_date,
    )
```

Or use raw SQL:
```python
import clickhouse_connect

client = clickhouse_connect.get_client(host='localhost', database='data_platform')

result = client.query("""
    SELECT date, close_price, daily_return
    FROM daily_features_latest
    WHERE ticker = '^GSPC'
      AND date >= today() - INTERVAL 30 DAY
    ORDER BY date
""")

df = result.result_as_dataframe()
```

### Step 9: Deprecate Old Code

Once validated:

1. **Add deprecation notice** to old functions:
```python
# dev/cross_asset_and_sentiment/cross_asset.py

import warnings

def get_sp500_return(start_date, end_date):
    """
    DEPRECATED: This function is deprecated.
    Use the production pipeline instead:
    
    data-platform daily --start-date YYYY-MM-DD --tickers "^GSPC"
    
    Or query from ClickHouse:
    SELECT * FROM daily_features_latest WHERE ticker = '^GSPC'
    """
    warnings.warn(
        "get_sp500_return() is deprecated. Use production pipeline.",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... existing code
```

2. **Archive notebooks** that use old functions:
```bash
mkdir -p dev/archive
mv dev/cross_asset_and_sentiment/main.ipynb dev/archive/
```

3. **Update documentation** to point to new pipeline

### Step 10: Monitor and Maintain

**Daily Monitoring:**
```bash
# Check today's ingestion
data-platform daily --start-date $(date +%Y-%m-%d)
```

**Weekly Maintenance:**
```sql
-- Check data freshness
SELECT
    ticker,
    max(date) AS latest_date,
    dateDiff('day', max(date), today()) AS days_stale
FROM daily_features_latest
GROUP BY ticker
HAVING days_stale > 3;

-- Check for gaps in data
SELECT
    ticker,
    date,
    neighbor(date, 1) AS next_date,
    dateDiff('day', date, next_date) AS gap_days
FROM daily_features_latest
WHERE ticker = '^GSPC'
  AND gap_days > 3
ORDER BY date DESC;
```

**Monthly Optimization:**
```sql
-- Optimize tables (merge parts)
OPTIMIZE TABLE daily_features FINAL;

-- Check table size
SELECT
    formatReadableSize(sum(bytes)) AS size,
    sum(rows) AS rows
FROM system.parts
WHERE database = 'data_platform'
  AND table = 'daily_features'
  AND active;
```

## Rollback Plan

If issues arise, you can temporarily revert:

1. **Keep old code** in `dev/` folder (don't delete yet)
2. **Use old functions** for critical processes
3. **Investigate issues** in new pipeline
4. **Fix and re-run** backfill if needed

```bash
# Re-run backfill for specific date range
data-platform backfill \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --chunk-size 30
```

## Common Migration Issues

### Issue 1: Missing Data for Certain Tickers

**Symptom**: Some tickers have no data in ClickHouse

**Solution**:
```bash
# Check logs for errors
data-platform daily --start-date 2024-01-01 --tickers "PROBLEMATIC_TICKER" --log-level DEBUG

# Verify ticker in sources.yaml
grep -A 10 "PROBLEMATIC_TICKER" config/sources.yaml

# Check if connector supports ticker
data-platform list-connectors
```

### Issue 2: Data Quality Validation Failures

**Symptom**: Pipeline fails with validation errors

**Solution**:
```python
# Adjust validation thresholds in config/sources.yaml
pipeline:
  max_null_rate: 0.5  # Increase from 0.3 if expecting more nulls
  check_outliers: false  # Temporarily disable for debugging
```

### Issue 3: ClickHouse Connection Errors

**Symptom**: Cannot connect to ClickHouse

**Solution**:
```bash
# Test connection directly
clickhouse-client --host localhost --port 9000

# Check .env credentials
cat .env | grep CLICKHOUSE

# Verify ClickHouse is running
ps aux | grep clickhouse
```

### Issue 4: Slow Backfill Performance

**Symptom**: Backfill takes too long

**Solution**:
```bash
# Reduce chunk size
data-platform backfill --chunk-size 90  # Instead of 365

# Or run specific tickers in parallel (in separate terminals)
data-platform backfill --tickers "^GSPC" --chunk-size 365 &
data-platform backfill --tickers "BTC-USD" --chunk-size 365 &
```

## Testing Checklist

Before fully migrating:

- [ ] ClickHouse tables created successfully
- [ ] Test ingestion for 1 month completes without errors
- [ ] Data values match old functions (within precision)
- [ ] All configured tickers have data
- [ ] No duplicate `(date, ticker)` records
- [ ] Airflow DAG runs successfully (if using)
- [ ] Downstream code updated and tested
- [ ] Monitoring queries return expected results
- [ ] Backfill completes for full historical range

## Support

If you encounter issues during migration:

1. Check logs: `data-platform daily --log-level DEBUG`
2. Review [Troubleshooting](../README.md#troubleshooting) section
3. Open GitHub issue with:
   - Error message
   - Command run
   - Log output
   - Expected vs actual behavior

## Next Steps

After successful migration:

1. **Set up monitoring dashboards** (Grafana)
2. **Configure alerting** (email/Slack on failures)
3. **Add new data sources** as needed
4. **Optimize queries** for your use cases
5. **Contribute improvements** back to the project

Congratulations on migrating to the production pipeline! 🎉
