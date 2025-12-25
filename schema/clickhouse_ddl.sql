-- ClickHouse DDL for Cross-Asset Data Platform
-- 
-- This schema is optimized for time-series analytics with (date, ticker) as primary key.

-- =============================================================================
-- DAILY FEATURES TABLE
-- =============================================================================
-- Main fact table for daily cross-asset features
-- Stores all daily updated metrics (prices, returns, yields, spreads, etc.)

CREATE DATABASE IF NOT EXISTS data_platform;

USE data_platform;

CREATE TABLE IF NOT EXISTS daily_features
(
    -- Primary key components
    date Date NOT NULL,
    ticker String NOT NULL,
    
    -- Asset metadata (denormalized for query performance)
    asset_class String NOT NULL,
    symbol String NOT NULL,
    currency String,
    
    -- Price features
    close_price Nullable(Float64),
    open_price Nullable(Float64),
    high_price Nullable(Float64),
    low_price Nullable(Float64),
    
    -- Return and volume
    daily_return Nullable(Float64),
    log_return Nullable(Float64),
    volume Nullable(Float64),
    dollar_volume Nullable(Float64),
    
    -- Fixed income features
    yield_value Nullable(Float64),
    spread_value Nullable(Float64),
    duration Nullable(Float64),
    
    -- Volatility features
    realized_volatility Nullable(Float64),
    implied_volatility Nullable(Float64),
    volatility_index Nullable(Float64),  -- VIX, VVIX, etc.
    
    -- Correlation and cross-asset metrics
    correlation_30d Nullable(Float64),
    correlation_90d Nullable(Float64),
    beta Nullable(Float64),
    
    -- Sentiment features
    sentiment_score Nullable(Float64),  -- -1 to 1 scale
    fear_greed_index Nullable(Float64),  -- 0-100 scale
    social_volume Nullable(Float64),  -- Number of social media mentions
    news_count Nullable(Float64),  -- Number of news articles
    search_interest Nullable(Float64),  -- Google Trends index
    
    -- On-chain metrics (crypto)
    on_chain_volume Nullable(Float64),
    active_addresses Nullable(Float64),
    hash_rate Nullable(Float64),
    network_value Nullable(Float64),
    
    -- Macro indicators
    economic_indicator Nullable(Float64),
    interest_rate Nullable(Float64),
    unemployment_rate Nullable(Float64),
    inflation_rate Nullable(Float64),
    
    -- Technical indicators
    rsi Nullable(Float64),
    macd Nullable(Float64),
    moving_average_50 Nullable(Float64),
    moving_average_200 Nullable(Float64),
    
    -- Lineage and versioning
    vendor String NOT NULL,
    ingestion_timestamp DateTime NOT NULL,
    data_timestamp DateTime NOT NULL,
    version UInt32 NOT NULL DEFAULT 1,
    
    -- Metadata (JSON as string)
    metadata String DEFAULT '{}'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(date)
ORDER BY (ticker, date)
SETTINGS index_granularity = 8192;

-- Indexes for common query patterns
-- Note: ClickHouse uses ORDER BY for primary index, additional indexes optional

-- Optional: Secondary index on asset_class for filtering
-- ALTER TABLE daily_features ADD INDEX idx_asset_class asset_class TYPE set(100) GRANULARITY 4;

-- Optional: Projection for aggregations by ticker over time
-- CREATE PROJECTION daily_features_by_ticker
-- (
--     SELECT
--         ticker,
--         toStartOfMonth(date) AS month,
--         avg(close_price) AS avg_price,
--         avg(daily_return) AS avg_return,
--         count() AS days
--     GROUP BY ticker, month
-- );


-- =============================================================================
-- QUARTERLY FEATURES TABLE
-- =============================================================================
-- For fundamentals, reference data, and slow-moving features
-- Updated quarterly or less frequently

CREATE TABLE IF NOT EXISTS quarterly_features
(
    -- Primary key components
    quarter String NOT NULL,  -- Format: 'YYYY-Q1', 'YYYY-Q2', etc.
    ticker String NOT NULL,
    
    -- Asset metadata
    asset_class String NOT NULL,
    symbol String NOT NULL,
    
    -- Feature identification
    feature_name String NOT NULL,
    value Nullable(Float64),
    
    -- Lineage
    vendor String NOT NULL,
    ingestion_timestamp DateTime NOT NULL,
    data_timestamp DateTime NOT NULL,
    version UInt32 NOT NULL DEFAULT 1,
    
    -- Metadata
    metadata String DEFAULT '{}'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY quarter
ORDER BY (ticker, quarter, feature_name)
SETTINGS index_granularity = 8192;


-- =============================================================================
-- MATERIALIZED VIEWS (Optional - for common aggregations)
-- =============================================================================

-- Monthly aggregates for faster dashboarding
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_features_monthly
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(month)
ORDER BY (ticker, asset_class, month)
AS
SELECT
    toStartOfMonth(date) AS month,
    ticker,
    asset_class,
    symbol,
    avgState(close_price) AS avg_price,
    avgState(daily_return) AS avg_return,
    minState(close_price) AS min_price,
    maxState(close_price) AS max_price,
    countState() AS trading_days
FROM daily_features
GROUP BY month, ticker, asset_class, symbol;


-- =============================================================================
-- HELPER VIEWS (for easier querying)
-- =============================================================================

-- Latest version of each (date, ticker) record
CREATE VIEW IF NOT EXISTS daily_features_latest AS
SELECT
    date,
    ticker,
    asset_class,
    symbol,
    currency,
    close_price,
    daily_return,
    yield_value,
    spread_value,
    correlation_30d,
    vendor,
    data_timestamp,
    version
FROM daily_features
FINAL;


-- Latest quarterly features
CREATE VIEW IF NOT EXISTS quarterly_features_latest AS
SELECT
    quarter,
    ticker,
    asset_class,
    symbol,
    feature_name,
    value,
    vendor,
    data_timestamp,
    version
FROM quarterly_features
FINAL;


-- =============================================================================
-- USAGE EXAMPLES
-- =============================================================================

-- Query 1: Get S&P 500 prices for last 30 days
-- SELECT date, ticker, close_price, daily_return
-- FROM daily_features_latest
-- WHERE ticker = '^GSPC'
--   AND date >= today() - INTERVAL 30 DAY
-- ORDER BY date DESC;

-- Query 2: Get all tickers for a specific date
-- SELECT ticker, asset_class, close_price, daily_return
-- FROM daily_features_latest
-- WHERE date = '2024-01-15'
-- ORDER BY ticker;

-- Query 3: Compare multiple assets over time
-- SELECT
--     date,
--     ticker,
--     close_price,
--     daily_return
-- FROM daily_features_latest
-- WHERE ticker IN ('^GSPC', 'BTC-USD', 'GC=F')
--   AND date >= '2024-01-01'
-- ORDER BY date, ticker;

-- Query 4: Get correlation between BTC and S&P 500
-- SELECT
--     date,
--     correlation_30d
-- FROM daily_features_latest
-- WHERE ticker = 'BTC-USD'
--   AND date >= today() - INTERVAL 90 DAY
-- ORDER BY date;

-- Query 5: Monthly average returns by asset class
-- SELECT
--     toStartOfMonth(date) AS month,
--     asset_class,
--     avg(daily_return) * 100 AS avg_return_pct,
--     count() AS trading_days
-- FROM daily_features_latest
-- WHERE date >= today() - INTERVAL 12 MONTH
-- GROUP BY month, asset_class
-- ORDER BY month DESC, asset_class;


-- =============================================================================
-- MAINTENANCE QUERIES
-- =============================================================================

-- Check table size
-- SELECT
--     table,
--     formatReadableSize(sum(bytes)) AS size,
--     sum(rows) AS rows,
--     max(modification_time) AS latest_modification
-- FROM system.parts
-- WHERE database = 'data_platform'
--   AND table LIKE '%features%'
--   AND active
-- GROUP BY table;

-- Optimize table (merge parts)
-- OPTIMIZE TABLE daily_features FINAL;

-- Check for duplicate records (should be none after dedup)
-- SELECT date, ticker, count(*) as cnt
-- FROM daily_features
-- GROUP BY date, ticker
-- HAVING cnt > 1;
