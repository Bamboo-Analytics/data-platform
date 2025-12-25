# Design Extensions Summary

## Changes Made

Based on preliminary dataset ideas exploration, the data platform has been extended to support comprehensive alternative data beyond traditional cross-asset pricing.

### 1. Expanded Data Models

**Enums Extended** (`src/data_platform/models.py`):

- **AssetClass**: Added `EQUITY_SINGLE`, `VOLATILITY`, `ALTERNATIVE`, `MACRO_INDICATOR`
- **Vendor**: Added 11 new vendors including FRED, CBOE, Twitter, Reddit, Google Trends, Glassnode, Alternative.me, etc.
- **FeatureType**: Expanded from 7 to 30+ feature types covering:
  - Volatility metrics (realized, implied, indices)
  - Sentiment (scores, fear/greed, social volume)
  - On-chain metrics (active addresses, hash rate)
  - Macro indicators (unemployment, CPI, interest rates)
  - Technical indicators (RSI, MACD, moving averages)

**DailyFactRecord** (`src/data_platform/models.py`):

Added 30+ optional fields for all new feature types with comprehensive mapping logic in `from_data_points()` method.

### 2. Updated Database Schema

**ClickHouse DDL** (`schema/clickhouse_ddl.sql`):

Extended `daily_features` table with columns for:
- Volatility metrics (3 columns)
- Sentiment indicators (5 columns)
- On-chain metrics (4 columns)
- Macro indicators (4 columns)
- Technical indicators (4 columns)

### 3. Data Source Configurations

**sources.yaml** (`config/sources.yaml`):

Added `alternative_sources` section with 12 pre-configured sources including:
- VIX (ready to use)
- Fear & Greed indices (stubs)
- On-chain metrics (stubs)
- Macro indicators from FRED (stubs)
- Social sentiment sources (stubs)

### 4. Connector Implementations

**Alternative Data Connectors** (`src/data_platform/connectors/alternative_data.py`):

Created comprehensive connector framework with:
- ✅ **VIXConnector**: Fully implemented via Yahoo Finance
- 🚧 **FearGreedConnector**: Stub for CNN index
- 🚧 **CryptoFearGreedConnector**: Stub for Alternative.me API
- 🚧 **TwitterSentimentConnector**: Stub with implementation notes
- 🚧 **GoogleTrendsConnector**: Stub using pytrends
- 🚧 **GlassnodeConnector**: Stub for on-chain metrics
- 🚧 **FREDConnector**: Stub for macro indicators

Each stub includes:
- Clear TODO implementation notes
- API endpoint documentation
- Required credential information
- Supported features list

### 5. Documentation

**Extended Features Guide** (`docs/EXTENDED_FEATURES.md`):

Comprehensive guide covering:
- All 5 new feature categories
- Data source requirements and costs
- API key setup instructions
- ClickHouse query examples
- Implementation status tracking
- Next steps and priorities

**Updated README** (`README.md`):

Added feature comparison tables showing:
- Coverage matrix for all feature types
- Vendor comparison with API requirements
- Implementation status for each category

## Design Principles

1. **Backward Compatibility**: All changes are additive - existing pipelines continue to work
2. **Explicit Stubs**: Unimplemented connectors raise `NotImplementedError` with clear instructions
3. **Gradual Enablement**: New sources disabled by default (`enabled: false` in config)
4. **Type Safety**: All new fields are properly typed and validated through Pydantic
5. **Extensibility**: Plugin architecture makes adding new vendors straightforward

## Next Steps

### Priority 1: Free/Easy Wins
1. Enable VIX ingestion (already implemented)
2. Implement FRED connector (free API key)
3. Implement Alternative.me crypto fear/greed (free API, no key)

### Priority 2: Sentiment Pipeline
1. Build Twitter sentiment analysis (requires v2 API)
2. Implement VADER/TextBlob for text scoring
3. Create aggregation logic for daily sentiment scores

### Priority 3: On-Chain Metrics
1. Evaluate Glassnode vs CoinMetrics pricing
2. Implement priority on-chain connectors
3. Create validation rules for crypto-specific metrics

### Priority 4: Technical Indicators
1. Build technical indicator calculation module
2. Add TA-Lib integration or pure Python alternatives
3. Create materialized views for common indicators

## Migration Path

For existing deployments:

1. **Schema Migration**: Run ClickHouse ALTER TABLE to add new columns
   ```sql
   ALTER TABLE daily_features ADD COLUMN sentiment_score Nullable(Float64);
   -- ... repeat for all new columns
   ```

2. **Code Deployment**: Deploy updated models and connectors

3. **Gradual Enablement**: Enable new sources one by one in `sources.yaml`

4. **Validation**: Monitor data quality for new feature types

5. **Backfill**: Optionally backfill alternative data where historical APIs exist

## Testing Checklist

- [ ] Unit tests for new FeatureType enum values
- [ ] Integration tests for VIX connector
- [ ] Schema validation for extended DailyFactRecord
- [ ] ClickHouse DDL migration test (existing table → extended schema)
- [ ] End-to-end test: VIX ingestion → ClickHouse → query
- [ ] Stub connectors properly raise NotImplementedError
- [ ] Configuration validation for alternative_sources

## Known Limitations

1. **Sentiment Analysis**: Requires NLP pipeline (not included)
2. **API Costs**: Some vendors (Glassnode) have significant costs
3. **Rate Limits**: Twitter, Google Trends have strict rate limits
4. **Data Quality**: Alternative data often noisier than market data
5. **Delayed Data**: Some macro indicators published with lag (e.g., GDP quarterly)

## References

- Extended Features Guide: `docs/EXTENDED_FEATURES.md`
- Connector Stubs: `src/data_platform/connectors/alternative_data.py`
- Updated Schema: `schema/clickhouse_ddl.sql`
- Configuration: `config/sources.yaml`
