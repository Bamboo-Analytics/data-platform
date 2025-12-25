# Data Platform - Cross-Asset & Alternative Data Ingestion Pipeline

A production-ready, extensible pipeline for ingesting cross-asset market data, sentiment indicators, on-chain metrics, and macro economic data into ClickHouse with Airflow orchestration.

## Overview

This pipeline transforms ad-hoc data fetching scripts into a maintainable, testable, and scalable data platform with:

- **Plugin-based architecture** - Easy to add new data sources (market data, sentiment, macro)
- **Comprehensive feature coverage** - Prices, returns, volatility, sentiment, on-chain, macro indicators
- **Separation of concerns** - Extract, Transform, Validate, Load
- **Idempotent loads** - Safe to re-run without duplicates
- **Data quality validation** - Automated checks and outlier detection
- **ClickHouse storage** - Optimized for time-series analytics with `(date, ticker)` primary key
- **Airflow orchestration** - Scheduled daily/quarterly refreshes
- **CLI interface** - Run locally or in pipelines
- **Comprehensive testing** - Unit tests with fixtures

### Key Features

✅ **Primary Key**: `(date, ticker)` uniquely identifies each record  
✅ **Extended Features**: 50+ feature types (price, sentiment, volatility, on-chain, macro)  
✅ **Alternative Data**: Sentiment scores, social volume, fear/greed indices  
✅ **Deduplication**: ReplacingMergeTree with version column  
✅ **Partitioning**: By `YYYYMM(date)` for efficient queries  
✅ **Backfill support**: Process historical data in chunks  
✅ **Retry logic**: Automatic retries with exponential backoff  
✅ **Type safety**: Pydantic models with validation  
✅ **Structured logging**: JSON logs for production monitoring  

## Quick Start

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your ClickHouse credentials

# Initialize database
data-platform init-db

# Run daily ingestion
data-platform daily --start-date 2024-01-01 --end-date 2024-01-31

# Backfill historical data
data-platform backfill --start-date 2020-01-01 --end-date 2024-12-31
```

## Installation

See full installation instructions in [INSTALLATION.md](docs/INSTALLATION.md)

## Usage

### CLI Commands

```bash
# List sources
data-platform list-sources

# Daily ingestion
data-platform daily --start-date 2024-12-20

# Backfill
data-platform backfill --start-date 2020-01-01 --end-date 2024-12-31 --chunk-size 365

# Specific tickers only
data-platform daily --start-date 2024-01-01 --tickers "^GSPC,BTC-USD"
```

### Python API

```python
from datetime import date
from data_platform import PipelineRunner

runner = PipelineRunner()
result = runner.run_daily(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)
```

## Adding New Data Sources

### Add a new ticker (existing vendor)

Edit `config/sources.yaml`:

```yaml
daily_sources:
  - name: "audusd"
    vendor: "yahoo_finance"
    asset_class: "fx"
    ticker: "AUDUSD=X"
    symbol: "AUD/USD"
    features:
      - close_price
      - daily_return
    enabled: true
```

### Add a new vendor

1. Create connector in `src/data_platform/connectors/my_vendor.py`
2. Register with `ConnectorFactory`
3. Add configuration to `sources.yaml`

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## Architecture

```
Data Sources → Connectors → Transform → Validate → ClickHouse → Airflow
```

### Feature Categories Supported

| Category | Examples | Status |
|----------|----------|--------|
| **Prices & Returns** | Close, Open, Daily Return, Log Return | ✅ Implemented |
| **Volume** | Trading Volume, Dollar Volume | ✅ Implemented |
| **Volatility** | VIX, Realized Vol, Implied Vol | ✅ VIX Ready |
| **Fixed Income** | Yields, Spreads, Duration | ✅ Implemented |
| **Correlations** | 30d/90d Correlation, Beta | ✅ Implemented |
| **Sentiment** | Sentiment Score, Fear & Greed | 🚧 Stubs Created |
| **Social Metrics** | Twitter Volume, News Count | 🚧 Stubs Created |
| **On-Chain** | Active Addresses, Hash Rate | 🚧 Stubs Created |
| **Macro Indicators** | CPI, Unemployment, Fed Funds | 🚧 Stubs Created |
| **Technical Indicators** | RSI, MACD, Moving Averages | 📋 TODO |

### Data Vendors

| Vendor | Coverage | API Key Required | Status |
|--------|----------|------------------|--------|
| **Yahoo Finance** | Equities, FX, Commodities, Crypto | No | ✅ Implemented |
| **FRED** | Macro Economic Data | Free Key | 🚧 Stub |
| **Alternative.me** | Crypto Fear & Greed | No | 🚧 Stub |
| **Glassnode** | On-Chain Crypto Metrics | Paid | 🚧 Stub |
| **Twitter API** | Social Sentiment | Yes (v2) | 🚧 Stub |
| **Google Trends** | Search Interest | No (pytrends) | 🚧 Stub |

See [EXTENDED_FEATURES.md](docs/EXTENDED_FEATURES.md) for complete feature documentation.

Full architecture documentation in [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=data_platform --cov-report=html

# Specific tests
pytest tests/test_models.py
```

## Deployment

### Airflow

```bash
export AIRFLOW_HOME=/path/to/data-platform/airflow
airflow db init
cp -r airflow/dags $AIRFLOW_HOME/dags
airflow webserver &
airflow scheduler &
```

DAGs:
- `daily_ingestion_dag` - Runs daily at 2 AM
- `backfill_dag` - Manual trigger for historical data
- `quarterly_refresh_dag` - Quarterly at 3 AM

## Project Structure

```
data-platform/
├── src/data_platform/      # Main package
│   ├── models.py          # Pydantic models
│   ├── pipeline.py        # Pipeline orchestrator
│   ├── connectors/        # Data source connectors
│   └── storage/           # ClickHouse client
├── config/                # Configuration
│   └── sources.yaml      # Data sources
├── airflow/dags/          # Airflow DAGs
├── schema/                # ClickHouse DDL
├── tests/                 # Unit tests
└── README.md
```

## Migration from Old Code

Old code in `dev/cross_asset_and_sentiment/cross_asset.py` is deprecated.

Migration steps:
1. Backfill historical data: `data-platform backfill --start-date 2019-01-01 --end-date 2024-12-31`
2. Enable Airflow DAG for daily updates
3. Query from ClickHouse instead of running old functions

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Adding Data Sources](docs/ADDING_SOURCES.md)
- [Airflow Setup](docs/AIRFLOW.md)
- [ClickHouse Schema](schema/clickhouse_ddl.sql)
- [API Reference](docs/API.md)

## Troubleshooting

Common issues:

**ClickHouse connection failed**
```bash
# Test connection
clickhouse-client --host localhost
```

**API rate limits**
- Reduce `chunk_size` in backfills
- Add delays in connector config

**Duplicate records**
```sql
-- Check for duplicates
SELECT date, ticker, count(*) 
FROM daily_features 
GROUP BY date, ticker 
HAVING count(*) > 1;
```

## Support

- GitHub Issues: [data-platform/issues](https://github.com/Bamboo-Analytics/data-platform/issues)
- Email: data-platform-team@example.com

## License

MIT License

## Roadmap

- [ ] Async/parallel fetching
- [ ] Additional vendors (Polygon, FRED)
- [ ] Real-time CDC updates
- [ ] REST API layer
- [ ] Grafana dashboards
- [ ] ML feature store integration
