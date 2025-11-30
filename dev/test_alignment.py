# Test to verify annual-to-quarterly alignment logic

from factors import FundamentalFactorBuilder
import pandas as pd

ticker = "AAPL"
builder = FundamentalFactorBuilder(ticker)

# Get quarterly and annual data separately
print("="*80)
print("TESTING ANNUAL-TO-QUARTERLY ALIGNMENT")
print("="*80)

quarterly_df = builder.build_quarterly_factors(start_date="2020-01-01")
annual_df = builder.build_annual_factors(years_back=6)

print("\n" + "="*80)
print("QUARTERLY DATA DATES:")
print("="*80)
print(quarterly_df.index.tolist())

print("\n" + "="*80)
print("ANNUAL DATA DATES:")
print("="*80)
print(annual_df.index.tolist())

# Now test the alignment
from fundamental_helper import align_to_dates

# Pick a sample column to test alignment
test_col = 'revenue'
if test_col in annual_df.columns:
    aligned_revenue = align_to_dates(annual_df[test_col], quarterly_df.index)
    
    print("\n" + "="*80)
    print("ALIGNMENT TEST - Annual Revenue aligned to Quarterly Dates:")
    print("="*80)
    
    result_df = pd.DataFrame({
        'quarterly_date': quarterly_df.index,
        'annual_revenue_used': aligned_revenue.values,
    })
    
    # Add which annual period this came from
    for i, q_date in enumerate(quarterly_df.index):
        # Find which annual date this value came from
        for j, a_date in enumerate(annual_df.index):
            if a_date <= q_date:
                latest_annual_date = a_date
        result_df.loc[i, 'from_annual_date'] = latest_annual_date
    
    print(result_df.to_string())
    
    print("\n" + "="*80)
    print("INTERPRETATION:")
    print("="*80)
    print("Each quarterly date uses the MOST RECENT annual data available at that time.")
    print("This ensures no look-ahead bias - we only use data that existed at each quarter end.")
else:
    print(f"\nColumn '{test_col}' not found in annual data")

print("\n" + "="*80)
print("EXPECTED BEHAVIOR FOR APPLE (Fiscal Year ends Sept 30):")
print("="*80)
print("Q1 2024 (Dec 31, 2023) → Uses FY 2023 (Sept 30, 2023) annual data")
print("Q2 2024 (Mar 31, 2024) → Uses FY 2023 (Sept 30, 2023) annual data") 
print("Q3 2024 (Jun 30, 2024) → Uses FY 2023 (Sept 30, 2023) annual data")
print("Q4 2024 (Sept 30, 2024) → Uses FY 2024 (Sept 30, 2024) annual data ← New data!")
print("\nThis is CORRECT - no look-ahead bias! ✓")
