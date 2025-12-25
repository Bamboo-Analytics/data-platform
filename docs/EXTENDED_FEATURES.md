# Extended Features Guide

## Overview

The data platform now supports comprehensive cross-asset, sentiment, and alternative data ingestion beyond traditional price/return metrics.

## New Feature Categories

### 1. **Volatility Metrics**
- **Volatility Index** (`volatility_index`): VIX, VVIX, other implied volatility indices
- **Realized Volatility** (`realized_volatility`): Historical volatility calculations
- **Implied Volatility** (`implied_volatility`): Options-derived vol surfaces

**Data Sources**: Yahoo Finance (VIX), CBOE, options data providers

### 2. **Sentiment & Alternative Data**
- **Sentiment Score** (`sentiment_score`): -1 to 1 scale from text analysis
- **Fear & Greed Index** (`fear_greed_index`): 0-100 scale market sentiment
- **Social Volume** (`social_volume`): Twitter mentions, Reddit posts
- **News Count** (`news_count`): Number of news articles per day
- **Search Interest** (`search_interest`): Google Trends data (0-100)

**Data Sources**:
- CNN Fear & Greed Index (web scraping required)
- Alternative.me (Crypto Fear & Greed)
- Twitter API v2
- Reddit API
- News API
- Google Trends (pytrends)

### 3. **On-Chain Metrics** (Cryptocurrency)
- **On-Chain Volume** (`on_chain_volume`): Transaction volume on blockchain
- **Active Addresses** (`active_addresses`): Unique wallet activity
- **Hash Rate** (`hash_rate`): Network security metric
- **Network Value** (`network_value`): Market cap, NVT ratio

**Data Sources**: Glassnode, CoinMetrics, Blockchain.com APIs

### 4. **Macro Indicators**
- **Economic Indicator** (`economic_indicator`): GDP, PMI, etc.
- **Interest Rate** (`interest_rate`): Central bank rates
- **Unemployment Rate** (`unemployment_rate`): Labor market data
- **Inflation Rate** (`inflation_rate`): CPI, PCE inflation

**Data Sources**: FRED (Federal Reserve Economic Data), national statistics agencies

### 5. **Technical Indicators**
- **RSI** (`rsi`): Relative Strength Index
- **MACD** (`macd`): Moving Average Convergence Divergence
- **Moving Averages** (`moving_average_50`, `moving_average_200`): SMA/EMA

**Calculation**: Computed from price data in transformation layer

## Asset Class Additions

- **VOLATILITY**: VIX, VVIX indices
- **ALTERNATIVE**: Sentiment scores, social metrics
- **MACRO_INDICATOR**: Economic data, central bank rates
- **EQUITY_SINGLE**: Individual stocks (vs indices/ETFs)

## Vendor Additions

### Free/Open Sources
- **FRED**: Free macro data with API key
- **CBOE**: VIX data (via Yahoo Finance proxy)
- **Alternative.me**: Free crypto fear & greed API

### Commercial/API Required
- **Glassnode**: On-chain crypto metrics (paid)
- **CoinMetrics**: Alternative on-chain provider (paid)
- **Twitter API**: Social sentiment (requires v2 credentials)
- **News API**: News counts/sentiment (freemium)
- **Google Trends**: Search interest (pytrends library)

## Implementation Status

### ✅ Implemented
- VIX connector (via Yahoo Finance)
- Extended data models (AssetDataPoint, DailyFactRecord)
- ClickHouse schema with all new fields
- Configuration templates in `sources.yaml`

### 🚧 Stubs Created (Require Implementation)
- Fear & Greed Index connectors
- Twitter/Reddit sentiment
- Google Trends
- Glassnode on-chain metrics
- FRED macro indicators

### 📋 TODO
- Implement sentiment analysis pipeline (VADER, TextBlob, or transformer models)
- Add rate limiting for API connectors
- Create scheduled jobs for alternative data (may not be daily)
- Build aggregation views for sentiment trends

## Configuration Examples

### VIX (Ready to Use)
```yaml
- name: "vix"
  vendor: "yahoo_finance"
  asset_class: "volatility"
  ticker: "^VIX"
  features:
    - volatility_index
  enabled: true
```

### Crypto Fear & Greed (Requires Implementation)
```yaml
- name: "crypto_fear_greed"
  vendor: "alternative_me"
  asset_class: "alternative"
  ticker: "CRYPTO_FG"
  features:
    - fear_greed_index
  enabled: false  # Set to true after implementing connector
```

### FRED Unemployment (Requires API Key)
```yaml
- name: "us_unemployment"
  vendor: "fred"
  asset_class: "macro_indicator"
  ticker: "UNRATE"
  features:
    - unemployment_rate
  enabled: false
```

## API Key Setup

1. **FRED** (Free): https://research.stlouisfed.org/docs/api/api_key.html
2. **Twitter** (Essential tier free): https://developer.twitter.com/en/portal/dashboard
3. **Glassnode** (Paid): https://glassnode.com/pricing
4. **News API** (Freemium): https://newsapi.org/pricing

Add keys to `.env`:
```bash
FRED_API_KEY=your_key_here
TWITTER_BEARER_TOKEN=your_token
GLASSNODE_API_KEY=your_key
NEWS_API_KEY=your_key
```

## ClickHouse Query Examples

### Sentiment Analysis
```sql
SELECT 
    date,
    ticker,
    sentiment_score,
    social_volume,
    fear_greed_index
FROM daily_features
WHERE asset_class = 'alternative'
    AND date >= '2024-01-01'
ORDER BY date DESC;
```

### Cross-Asset Correlation with Sentiment
```sql
SELECT 
    btc.date,
    btc.close_price AS btc_price,
    btc.sentiment_score,
    sp.close_price AS sp500_price,
    btc.correlation_30d
FROM daily_features AS btc
LEFT JOIN daily_features AS sp ON btc.date = sp.date AND sp.ticker = '^GSPC'
WHERE btc.ticker = 'BTC-USD'
    AND btc.date >= '2024-01-01'
ORDER BY btc.date;
```

### Volatility Regime Analysis
```sql
SELECT 
    toStartOfMonth(date) AS month,
    avg(volatility_index) AS avg_vix,
    avg(realized_volatility) AS avg_rv,
    avg(sentiment_score) AS avg_sentiment
FROM daily_features
WHERE ticker IN ('^VIX', '^GSPC')
GROUP BY month
ORDER BY month DESC;
```

## Next Steps

1. **Implement Priority Connectors**: Start with FRED (free) and Alternative.me (crypto fear/greed)
2. **Build Sentiment Pipeline**: Integrate VADER/TextBlob for Twitter sentiment
3. **Create Airflow DAGs**: Separate DAGs for alternative data (different schedules)
4. **Add Data Quality Checks**: Validate sentiment scores (-1 to 1), indices (0-100)
5. **Build Dashboards**: Grafana/Superset for sentiment visualization

## References

- FRED API Docs: https://fred.stlouisfed.org/docs/api/fred/
- Alternative.me API: https://alternative.me/crypto/fear-and-greed-index/
- Twitter API v2: https://developer.twitter.com/en/docs/twitter-api
- Glassnode Docs: https://docs.glassnode.com/
- Google Trends (pytrends): https://github.com/GeneralMills/pytrends
