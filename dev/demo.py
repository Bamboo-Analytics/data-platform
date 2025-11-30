# demo.py

from factors import FundamentalFactorBuilder, get_eps_surprises, get_days_to_next_earnings
import pandas as pd
from pathlib import Path
from datetime import datetime

def main():
    ticker = "AAPL"
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "fundamental_data"
    output_dir.mkdir(exist_ok=True)
    
    # Create ticker-specific subdirectory
    ticker_dir = output_dir / ticker
    ticker_dir.mkdir(exist_ok=True)
    
    # Timestamp for file versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # --- Build COMBINED factors (Quarterly + Annual in one dataframe) ---
    print("\n" + "="*60)
    print("Building COMBINED fundamental factors (Quarterly + Annual)...")
    print("="*60)
    builder = FundamentalFactorBuilder(ticker)
    combined_factors = builder.build_combined_factors(start_date="2020-01-01")
    
    # Display sample of quarterly columns
    quarterly_cols = [col for col in combined_factors.columns if col.startswith('quarterly_')]
    print("\nSample Quarterly Columns:")
    sample_quarterly = combined_factors[quarterly_cols[:10]].head()
    print(sample_quarterly)
    
    # Display sample of annual columns
    annual_cols = [col for col in combined_factors.columns if col.startswith('annual_')]
    print("\nSample Annual Columns:")
    sample_annual = combined_factors[annual_cols[:10]].head()
    print(sample_annual)
    
    # Save combined factors to CSV and Parquet
    combined_csv_path = ticker_dir / f"{ticker}_combined_factors_{timestamp}.csv"
    combined_parquet_path = ticker_dir / f"{ticker}_combined_factors_latest.parquet"
    
    combined_factors.to_csv(combined_csv_path)
    combined_factors.to_parquet(combined_parquet_path)
    print(f"\n✓ Saved combined factors to:\n  - {combined_csv_path}\n  - {combined_parquet_path}")
    
    # Also save individual quarterly and annual for backward compatibility
    quarterly_factors = combined_factors[[col for col in combined_factors.columns if col.startswith('quarterly_')]]
    annual_factors = combined_factors[[col for col in combined_factors.columns if col.startswith('annual_')]]
    
    quarterly_csv_path = ticker_dir / f"{ticker}_quarterly_factors_{timestamp}.csv"
    quarterly_parquet_path = ticker_dir / f"{ticker}_quarterly_factors_latest.parquet"
    quarterly_factors.to_csv(quarterly_csv_path)
    quarterly_factors.to_parquet(quarterly_parquet_path)
    
    annual_csv_path = ticker_dir / f"{ticker}_annual_factors_{timestamp}.csv"
    annual_parquet_path = ticker_dir / f"{ticker}_annual_factors_latest.parquet"
    annual_factors.to_csv(annual_csv_path)
    annual_factors.to_parquet(annual_parquet_path)
    
    # --- Get EPS surprises ---
    eps_df = get_eps_surprises(ticker, limit=8)
    print("\nEPS surprises:")
    print(eps_df)
    
    if not eps_df.empty:
        eps_csv_path = ticker_dir / f"{ticker}_eps_surprises_{timestamp}.csv"
        eps_parquet_path = ticker_dir / f"{ticker}_eps_surprises_latest.parquet"
        
        eps_df.to_csv(eps_csv_path)
        eps_df.to_parquet(eps_parquet_path)
        print(f"\n✓ Saved EPS surprises to:\n  - {eps_csv_path}\n  - {eps_parquet_path}")
    
    # --- Get days to next earnings ---
    days_to_earn = get_days_to_next_earnings(ticker)
    print("\nDays until next earnings:", days_to_earn)
    
    # Save metadata including days to earnings
    metadata = {
        "ticker": ticker,
        "last_updated": datetime.now().isoformat(),
        "days_to_next_earnings": days_to_earn,
        "quarterly_periods_analyzed": len(combined_factors),
        "total_columns": len(combined_factors.columns),
        "quarterly_columns": len([c for c in combined_factors.columns if c.startswith('quarterly_')]),
        "annual_columns": len([c for c in combined_factors.columns if c.startswith('annual_')]),
    }
    
    metadata_df = pd.DataFrame([metadata])
    metadata_path = ticker_dir / f"{ticker}_metadata_latest.csv"
    metadata_df.to_csv(metadata_path, index=False)
    print(f"\n✓ Saved metadata to: {metadata_path}")
    
    # Create a summary file
    summary_path = output_dir / "data_summary.csv"
    summary_data = {
        "ticker": [ticker],
        "last_updated": [datetime.now().isoformat()],
        "combined_factors_file": [str(combined_parquet_path.relative_to(output_dir))],
        "quarterly_factors_file": [str(quarterly_parquet_path.relative_to(output_dir))],
        "annual_factors_file": [str(annual_parquet_path.relative_to(output_dir))],
        "eps_surprises_file": [str(eps_parquet_path.relative_to(output_dir)) if not eps_df.empty else None],
        "metadata_file": [str(metadata_path.relative_to(output_dir))],
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # Append to existing summary or create new
    if summary_path.exists():
        existing_summary = pd.read_csv(summary_path)
        # Remove old entry for same ticker
        existing_summary = existing_summary[existing_summary["ticker"] != ticker]
        summary_df = pd.concat([existing_summary, summary_df], ignore_index=True)
    
    summary_df.to_csv(summary_path, index=False)
    print(f"\n✓ Updated summary file: {summary_path}")
    
    print(f"\n{'='*60}")
    print(f"All data saved to: {ticker_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
