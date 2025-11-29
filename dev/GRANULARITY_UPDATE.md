# Granularity Update Summary

## Changes Made to Support Quarterly Data

### 1. `fundamental_helper.py` - BaseFinanceLoader Class

#### New Primary Method: `get_quarterly_statements()`
- **Purpose**: Fetch quarterly financial statements (income, balance sheet, cashflow)
- **API**: Uses `freq="quarterly"` for newer yfinance API
- **Fallback**: Uses `quarterly_income_stmt`, `quarterly_balance_sheet`, `quarterly_cashflow` for older API

#### Kept for Backward Compatibility: `get_annual_statements()`
- **Purpose**: Fetch annual financial statements
- **API**: Uses `freq="yearly"` for newer yfinance API
- **Fallback**: Uses `income_stmt`, `balance_sheet`, `cashflow` for older API
- **Note**: Still available but quarterly is now the default granularity

#### Unchanged: `get_price_and_shares()`
- Returns daily price history and shares outstanding
- No changes needed - works with any granularity

### 2. `factors.py` - FundamentalFactorBuilder Class

#### New Primary Method: `build_quarterly_factors(start_date="2020-01-01")`
- **Purpose**: Build quarterly fundamental factors (one row per quarter)
- **Data Source**: Calls `self.get_quarterly_statements()`
- **Output**: DataFrame with fiscal quarters as index (e.g., 2020-03-31, 2020-06-30, etc.)
- **Metrics Calculated**:
  - Valuation: PE, PB, PS, EV/EBITDA
  - Profitability: ROE, ROA, Gross Margin, Operating Margin
  - Leverage: Debt/Equity, Interest Coverage
  - Liquidity: Current Ratio, Quick Ratio
  - Financial Health: Altman Z-Score
  - Growth: QoQ revenue, earnings, OCF, FCF growth
  - Free Cash Flow & FCF Yield

#### Kept for Backward Compatibility: `build_annual_factors(years_back=5)`
- **Purpose**: Build annual fundamental factors (one row per year)
- **Data Source**: Calls `self.get_annual_statements()`
- **Output**: DataFrame with fiscal years as index
- **Note**: Still functional but not the primary method

### 3. `demo.py` - Updated to Use Quarterly Data

**Primary Output**: Quarterly factors from 2020-01-01 onwards
- Saves to: `{ticker}_quarterly_factors_{timestamp}.csv`
- Saves to: `{ticker}_quarterly_factors_latest.parquet`

**File Structure**:
```
fundamental_data/
├── AAPL/
│   ├── AAPL_quarterly_factors_YYYYMMDD_HHMMSS.csv
│   ├── AAPL_quarterly_factors_latest.parquet
│   ├── AAPL_eps_surprises_YYYYMMDD_HHMMSS.csv
│   ├── AAPL_eps_surprises_latest.parquet
│   └── AAPL_metadata_latest.csv
└── data_summary.csv
```

## Key Differences: Quarterly vs Annual

| Aspect | Quarterly | Annual |
|--------|-----------|--------|
| **Frequency** | 4 records per year | 1 record per year |
| **Data Points** | ~20 quarters (2020-2025) | ~5 years (2020-2025) |
| **Use Case** | Short-term trends, detailed analysis | Long-term trends, yearly comparison |
| **Method** | `build_quarterly_factors()` | `build_annual_factors()` |
| **API Call** | `get_quarterly_statements()` | `get_annual_statements()` |
| **Growth Metrics** | QoQ (Quarter-over-Quarter) | YoY (Year-over-Year) |

## Migration Guide

### For Existing Code Using Annual Data:
1. **Replace method calls**: 
   - `builder.build_annual_factors()` → `builder.build_quarterly_factors()`
   - `loader.get_annual_statements()` → `loader.get_quarterly_statements()`

2. **Update file references**:
   - `annual_factors_latest.parquet` → `quarterly_factors_latest.parquet`

3. **Adjust expectations**:
   - 4x more data points (quarterly vs yearly)
   - Growth metrics are QoQ instead of YoY
   - Index is fiscal quarter end dates, not fiscal year end dates

### Example Usage:
```python
from factors import FundamentalFactorBuilder

# Build quarterly factors from 2020 onwards
builder = FundamentalFactorBuilder("AAPL")
quarterly_df = builder.build_quarterly_factors(start_date="2020-01-01")

# Output: ~20 rows (5 years × 4 quarters)
# Index: 2020-03-31, 2020-06-30, 2020-09-30, 2020-12-31, ...
```

## Validation Checklist

✅ `BaseFinanceLoader.get_quarterly_statements()` - Returns quarterly data  
✅ `BaseFinanceLoader.get_annual_statements()` - Returns annual data (backward compatible)  
✅ `FundamentalFactorBuilder.build_quarterly_factors()` - Primary method  
✅ `FundamentalFactorBuilder.build_annual_factors()` - Backward compatible  
✅ `demo.py` - Updated to use quarterly as default  
✅ Growth metrics changed from YoY to QoQ for quarterly data  
✅ File naming reflects granularity (quarterly vs annual)  

## Next Steps

1. **Test the code**: Run `demo.py` to generate quarterly data
2. **Update notebooks**: Change data loading to use quarterly files
3. **Verify data quality**: Check that quarterly metrics look correct
4. **Consider adding**: TTM (Trailing Twelve Months) calculations if needed
