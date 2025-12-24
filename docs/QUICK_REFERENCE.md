# Quick Reference Guide

## Common Commands

### Setup
```bash
# Install
uv sync

# Configure
cp .env.example .env
nano .env

# Initialize database
data-platform init-db
```

### Daily Operations
```bash
# Today's data
data-platform daily --start-date $(date +%Y-%m-%d)

# Specific date range
data-platform daily --start-date 2024-01-01 --end-date 2024-01-31

# Specific tickers
data-platform daily --start-date 2024-01-01 --tickers "^GSPC,BTC-USD"
```

### Backfill
```bash
# Last 5 years
data-platform backfill --start-date 2019-12-21 --end-date 2024-12-21

# With custom chunk size
data-platform backfill --start-date 2020-01-01 --end-date 2024-12-31 --chunk-size 90
```

### Debugging
```bash
# Verbose logging
data-platform daily --start-date 2024-01-01 --log-level DEBUG

# List sources
data-platform list-sources

# List connectors
data-platform list-connectors
```

## Common SQL Queries

### Basic Queries
```sql
-- Latest data for a ticker
SELECT * FROM daily_features_latest
WHERE ticker = '^GSPC'
ORDER BY date DESC
LIMIT 10;

-- All tickers for a date
SELECT ticker, close_price, daily_return
FROM daily_features_latest
WHERE date = '2024-01-15'
ORDER BY ticker;

-- Date range for multiple tickers
SELECT date, ticker, close_price, daily_return
FROM daily_features_latest
WHERE ticker IN ('^GSPC', 'BTC-USD', 'GC=F')
  AND date >= '2024-01-01'
ORDER BY date, ticker;
```

### Analytics
```sql
-- Monthly average returns by asset class
SELECT
    toStartOfMonth(date) AS month,
    asset_class,
    avg(daily_return) * 100 AS avg_return_pct,
    count() AS trading_days
FROM daily_features_latest
WHERE date >= today() - INTERVAL 12 MONTH
GROUP BY month, asset_class
ORDER BY month DESC;

-- Correlation matrix
SELECT
    a.ticker AS ticker1,
    b.ticker AS ticker2,
    corr(a.daily_return, b.daily_return) AS correlation
FROM daily_features_latest a
JOIN daily_features_latest b ON a.date = b.date
WHERE a.date >= today() - INTERVAL 90 DAY
  AND a.ticker IN ('^GSPC', 'BTC-USD', 'GC=F')
  AND b.ticker IN ('^GSPC', 'BTC-USD', 'GC=F')
GROUP BY ticker1, ticker2;

-- Best/worst performers (last 30 days)
SELECT
    ticker,
    symbol,
    asset_class,
    (last_value(close_price) - first_value(close_price)) / first_value(close_price) * 100 AS return_pct
FROM daily_features_latest
WHERE date >= today() - INTERVAL 30 DAY
GROUP BY ticker, symbol, asset_class
ORDER BY return_pct DESC;
```

### Monitoring
```sql
-- Data freshness check
SELECT
    ticker,
    max(date) AS latest_date,
    dateDiff('day', max(date), today()) AS days_stale
FROM daily_features_latest
GROUP BY ticker
HAVING days_stale > 3
ORDER BY days_stale DESC;

-- Missing data gaps
SELECT
    ticker,
    groupArray(date) AS dates,
    arrayEnumerate(dates) AS positions
FROM daily_features_latest
WHERE ticker = '^GSPC'
  AND date >= today() - INTERVAL 30 DAY
ORDER BY date;

-- Record count by month
SELECT
    toYYYYMM(date) AS month,
    count(DISTINCT ticker) AS tickers,
    count(*) AS records
FROM daily_features
GROUP BY month
ORDER BY month DESC;
```

### Maintenance
```sql
-- Table size
SELECT
    table,
    formatReadableSize(sum(bytes)) AS size,
    sum(rows) AS rows
FROM system.parts
WHERE database = 'data_platform'
  AND table = 'daily_features'
  AND active
GROUP BY table;

-- Check for duplicates (should be none)
SELECT date, ticker, count(*) AS cnt
FROM daily_features
GROUP BY date, ticker
HAVING cnt > 1;

-- Optimize table
OPTIMIZE TABLE daily_features FINAL;
```

## Python API Examples

### Basic Usage
```python
from datetime import date, timedelta
from data_platform import PipelineRunner

runner = PipelineRunner()

# Daily ingestion
result = runner.run_daily(
    start_date=date.today() - timedelta(days=30),
    end_date=date.today(),
)

print(f"Loaded: {result.records_loaded}")
```

### Query Data
```python
from data_platform.storage import ClickHouseClient

with ClickHouseClient() as client:
    records = client.query_daily_facts(
        ticker="^GSPC",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )
    
    for record in records:
        print(f"{record['date']}: {record['close_price']}")
```

### Custom Connector
```python
from data_platform.connectors.base import BaseConnector, ConnectorFactory
from data_platform.models import AssetDataPoint, AssetClass, Vendor

class MyConnector(BaseConnector):
    def fetch(self, ticker, start_date, end_date, **kwargs):
        # Your implementation
        return [AssetDataPoint(...)]
    
    def validate_ticker(self, ticker):
        return True
    
    @property
    def supported_features(self):
        return ["close_price", "daily_return"]

# Register
ConnectorFactory.register(
    Vendor.POLYGON,  # or your vendor
    AssetClass.EQUITY_INDEX,
    MyConnector,
)
```

## Configuration Files

### config/sources.yaml
```yaml
daily_sources:
  - name: "my_ticker"
    vendor: "yahoo_finance"
    asset_class: "equity_index"
    ticker: "AAPL"
    symbol: "Apple Inc."
    currency: "USD"
    features:
      - close_price
      - daily_return
    enabled: true
```

### .env
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=your_password
CLICKHOUSE_DATABASE=data_platform
LOG_LEVEL=INFO
```

## Airflow Trigger Examples

### Daily DAG (Automatic)
Runs at 2 AM daily automatically.

### Backfill DAG (Manual)
```json
{
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "chunk_size_days": 90,
  "tickers": ["^GSPC", "BTC-USD"]
}
```

## Troubleshooting

### Connection Error
```bash
# Test ClickHouse
clickhouse-client --host localhost

# Check credentials in .env
cat .env | grep CLICKHOUSE
```

### Validation Error
```python
# Adjust thresholds in config/sources.yaml
pipeline:
  max_null_rate: 0.5
  check_outliers: false
```

### Slow Performance
```bash
# Reduce chunk size
data-platform backfill --chunk-size 30

# Run specific tickers
data-platform daily --tickers "^GSPC"
```

## File Locations

```
data-platform/
├── src/data_platform/       # Source code
├── config/sources.yaml      # Data sources config
├── .env                     # Environment config
├── airflow/dags/            # Airflow DAGs
├── schema/clickhouse_ddl.sql # Database schema
├── tests/                   # Unit tests
└── docs/                    # Documentation
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLICKHOUSE_HOST` | localhost | ClickHouse host |
| `CLICKHOUSE_PORT` | 8123 | HTTP port |
| `CLICKHOUSE_DATABASE` | data_platform | Database name |
| `LOG_LEVEL` | INFO | Log verbosity |
| `LOG_FORMAT` | json | Log format |

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=data_platform

# Specific test
pytest tests/test_models.py::TestAssetDataPoint::test_create_valid_data_point

# Watch mode
pytest-watch
```

## Useful Links

- [Full Documentation](README.md)
- [Migration Guide](docs/MIGRATION.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)
- [ClickHouse DDL](schema/clickhouse_ddl.sql)
