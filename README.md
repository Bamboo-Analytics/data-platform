# Data Platform

Financial Data Platform for ingesting and processing market data from multiple APIs.

## Architecture

This platform uses a **per-API Lambda architecture** with clean separation of concerns:

```
API Response → Connector (validate) → Mapper (transform) → Standard Models → S3 (Parquet)
```

### Components

- **Standard Models**: Canonical data schemas (`OHLCV`, `AssetInfo`) that all APIs map to
- **API-Specific Models**: Pydantic models matching each API's response format
- **Connectors**: Fetch and validate data from external APIs
- **Mappers**: Transform API-specific models to standard platform models
- **S3 Writer**: Store data as parquet files with partitioning and incremental load support
- **Lambda Handlers**: One per API for isolated deployment and scaling

## Features

- ✅ **Incremental Loads**: Automatically fetches only new data based on S3 timestamps
- ✅ **Type Safety**: Full Pydantic validation for both API and platform models
- ✅ **Partitioned Storage**: Data organized by source, ticker, and date
- ✅ **Multiple Data Types**: OHLCV, asset info, and extensible for more
- ✅ **Per-API Isolation**: Independent Lambda deployments for each data source

## Project Structure

```
data_platform/
├── ingestion/
│   ├── models/
│   │   └── standard.py          # Platform standard models
│   ├── storage/
│   │   └── s3_writer.py         # S3 parquet writer
│   ├── connectors/
│   │   └── yfinance/
│   │       ├── models.py        # YFinance-specific models
│   │       ├── connector.py     # YFinance API client
│   │       ├── mapper.py        # Transform to standard models
│   │       └── handler.py       # Lambda handler
│   └── examples/
│       └── eventbridge_payloads.json
```

## Getting Started

### Installation

```bash
# Install dependencies using uv
uv sync

# Or with pip
pip install -e .
```

### Environment Variables

Lambda functions require:
- `S3_BUCKET`: Target S3 bucket for parquet files
- `AWS_REGION`: AWS region (auto-provided by Lambda)

### Example Usage

#### Deploy YFinance Lambda

```bash
# Package the Lambda (example using AWS CLI)
zip -r yfinance-lambda.zip data_platform/

aws lambda create-function \
  --function-name yfinance-ingestion \
  --runtime python3.13 \
  --handler data_platform.ingestion.connectors.yfinance.handler.lambda_handler \
  --zip-file fileb://yfinance-lambda.zip \
  --environment Variables="{S3_BUCKET=my-data-bucket}" \
  --timeout 300 \
  --memory-size 512
```

#### Invoke Lambda

```bash
# Incremental OHLCV load
aws lambda invoke \
  --function-name yfinance-ingestion \
  --payload '{"data_type":"ohlcv","ticker":"AAPL","incremental":true}' \
  response.json

# Fetch asset info
aws lambda invoke \
  --function-name yfinance-ingestion \
  --payload '{"data_type":"asset_info","ticker":"AAPL"}' \
  response.json
```

#### Configure EventBridge Schedule

```bash
# Daily OHLCV ingestion after market close (9 PM ET)
aws events put-rule \
  --name daily-ohlcv-aapl \
  --schedule-expression "cron(0 21 ? * MON-FRI *)"

aws events put-targets \
  --rule daily-ohlcv-aapl \
  --targets "Id"="1","Arn"="arn:aws:lambda:...:function:yfinance-ingestion","Input"='{"data_type":"ohlcv","ticker":"AAPL","incremental":true}'
```

## Data Storage Format

### S3 Structure

```
s3://my-bucket/
├── ohlcv/
│   └── source=yfinance/
│       └── ticker=aapl/
│           └── year=2024/
│               └── month=12/
│                   └── day=27/
│                       └── data_20241227_160000.parquet
└── asset_info/
    └── source=yfinance/
        └── ticker=aapl/
            └── info_20241227_120000.parquet
```

### Parquet Schema

**OHLCV:**
```
ticker: string
timestamp: timestamp
open: double
high: double
low: double
close: double
volume: double
source: string
```

**AssetInfo:**
```
ticker: string
name: string
asset_type: string
exchange: string
currency: string
sector: string
industry: string
market_cap: double
description: string
last_dividend: double
last_split: string
source: string
```

## Adding New APIs

To add a new data source (e.g., Polygon.io):

1. Create `connectors/polygon/models.py` with API-specific models
2. Create `connectors/polygon/connector.py` to fetch and validate
3. Create `connectors/polygon/mapper.py` to transform to standard models
4. Create `connectors/polygon/handler.py` with Lambda entry point
5. Deploy as a separate Lambda function

No changes needed to existing connectors or shared infrastructure!

## Development

### Run Tests

```bash
# TODO: Add test suite
pytest tests/
```

### Linting

```bash
ruff check .
ruff format .
```

## Supported APIs

- ✅ **YFinance**: Yahoo Finance (OHLCV, asset info)
- 🚧 **Polygon.io**: Coming soon
- 🚧 **Alpha Vantage**: Coming soon

## License

MIT
