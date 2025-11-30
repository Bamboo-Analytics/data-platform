# factors.py

import pandas as pd
from fundamental_helper import (
    BaseFinanceLoader,
    get_row,
    align_to_dates,
)


def safe_divide(numerator, denominator, default=pd.NA):
    """Safely divide two series, returning default if denominator doesn't exist or is invalid."""
    try:
        result = numerator / denominator
        return result
    except (KeyError, ZeroDivisionError):
        return default


class FundamentalFactorBuilder(BaseFinanceLoader):
    """
    Example of INHERITING from BaseFinanceLoader.
    This class gets all the loader methods for free and adds
    higher-level factor building logic on top.
    """

    def build_annual_factors(self, years_back: int = 5) -> pd.DataFrame:
        income, balance, cashflow = self.get_annual_statements()
        price_hist, shares_series = self.get_price_and_shares()
        t = self.yf_ticker

        if income.empty or balance.empty or cashflow.empty:
            raise ValueError(f"Missing financial statement data for {self.ticker}")

        # ---- raw lines from statements ----
        net_income       = get_row(income,  ["NetIncome", "Net Income"])
        revenue          = get_row(income,  ["TotalRevenue", "Total Revenue"])
        gross_profit     = get_row(income,  ["GrossProfit", "Gross Profit"])
        operating_income = get_row(income,  ["OperatingIncome", "Operating Income"])
        ebit             = get_row(income,  ["Ebit", "EBIT"])
        interest_exp     = get_row(income,  ["InterestExpense", "Interest Expense"])

        ocf              = get_row(cashflow, ["OperatingCashFlow",
                                              "Total Cash From Operating Activities"])
        capex            = get_row(cashflow, ["CapitalExpenditures",
                                              "Capital Expenditure"])

        shareholder_equity = get_row(balance, ["TotalStockholderEquity",
                                               "Total Stockholder Equity"])
        total_assets       = get_row(balance, ["TotalAssets", "Total Assets"])
        total_liabilities  = get_row(balance, ["TotalLiab", "Total Liabilities",
                                               "Total Liab"])
        current_assets     = get_row(balance, ["TotalCurrentAssets",
                                               "Total Current Assets"])
        current_liab       = get_row(balance, ["TotalCurrentLiabilities",
                                               "Total Current Liabilities"])
        inventory          = get_row(balance, ["Inventory"])
        total_debt         = get_row(balance, ["TotalDebt", "Total Debt"])
        cash               = get_row(balance, ["CashAndCashEquivalents",
                                               "Cash And Cash Equivalents"])
        retained_earnings  = get_row(balance, ["RetainedEarnings",
                                               "Retained Earnings"])

        df = pd.DataFrame({
            "net_income":        net_income,
            "revenue":           revenue,
            "gross_profit":      gross_profit,
            "operating_income":  operating_income,
            "ebit":              ebit,
            "interest_exp":      interest_exp,
            "ocf":               ocf,
            "capex":             capex,
            "shareholder_equity": shareholder_equity,
            "total_assets":      total_assets,
            "total_liabilities": total_liabilities,
            "current_assets":    current_assets,
            "current_liab":      current_liab,
            "inventory":         inventory,
            "total_debt":        total_debt,
            "cash":              cash,
            "retained_earnings": retained_earnings,
        })

        df.index.name = "fiscal_date"
        df = df.sort_index()
        df = df.tail(years_back)  # last N fiscal periods

        # --- price & shares ---
        df["shares"] = align_to_dates(shares_series, df.index)
        df["price"]  = align_to_dates(price_hist, df.index)
        df["market_cap"] = df["price"] * df["shares"]

        # --- valuation ---
        df["eps"] = df["net_income"] / df["shares"]
        df["pe_trailing"] = df["price"] / df["eps"]

        info = t.get_info()
        df["forward_pe_snapshot"]  = info.get("forwardPE")
        df["forward_eps_snapshot"] = info.get("forwardEps")

        # Check if shareholder_equity exists before using it
        if "shareholder_equity" in df.columns and not df["shareholder_equity"].isna().all():
            bvps = df["shareholder_equity"] / df["shares"]
            df["pb"] = df["price"] / bvps
        else:
            df["pb"] = pd.NA
            
        df["ps"] = df["market_cap"] / df["revenue"]

        df["ev"] = df["market_cap"] + df["total_debt"] - df["cash"]
        # EBITDA
        ebitda_row = get_row(income, ["Ebitda", "EBITDA"])
        if not ebitda_row.empty:
            df["ebitda"] = ebitda_row.reindex(df.index)
        else:
            df["ebitda"] = df["ebit"]  # fallback
        df["ev_ebitda"] = df["ev"] / df["ebitda"]

        # FCF + yield
        df["fcf"] = df["ocf"] + df["capex"]    # capex is usually negative
        df["fcf_yield"] = df["fcf"] / df["market_cap"]

        # growth (YoY)
        df["revenue_growth_yoy"]  = df["revenue"].pct_change()
        df["earnings_growth_yoy"] = df["net_income"].pct_change()
        df["ocf_growth_yoy"]      = df["ocf"].pct_change()
        df["fcf_growth_yoy"]      = df["fcf"].pct_change()

        # profitability & leverage
        df["roe"]              = safe_divide(df.get("net_income"), df.get("shareholder_equity"))
        df["roa"]              = safe_divide(df.get("net_income"), df.get("total_assets"))
        df["gross_margin"]     = safe_divide(df.get("gross_profit"), df.get("revenue"))
        df["operating_margin"] = safe_divide(df.get("operating_income"), df.get("revenue"))
        df["debt_to_equity"]   = safe_divide(df.get("total_debt"), df.get("shareholder_equity"))
        
        if "ebit" in df.columns and "interest_exp" in df.columns:
            df["interest_coverage"] = safe_divide(df["ebit"], df["interest_exp"].abs())
        else:
            df["interest_coverage"] = pd.NA

        # balance sheet strength
        df["current_ratio"] = safe_divide(df.get("current_assets"), df.get("current_liab"))
        
        if "current_assets" in df.columns and "current_liab" in df.columns and "inventory" in df.columns:
            df["quick_ratio"] = safe_divide(df["current_assets"] - df["inventory"], df["current_liab"])
        else:
            df["quick_ratio"] = pd.NA

        # Altman Z - only calculate if all required columns exist
        required_altman_cols = ["current_assets", "current_liab", "total_assets", "retained_earnings", 
                                "ebit", "market_cap", "total_liabilities", "revenue"]
        if all(col in df.columns for col in required_altman_cols):
            df["X1"] = (df["current_assets"] - df["current_liab"]) / df["total_assets"]
            df["X2"] = df["retained_earnings"] / df["total_assets"]
            df["X3"] = df["ebit"] / df["total_assets"]
            df["X4"] = df["market_cap"] / df["total_liabilities"]
            df["X5"] = df["revenue"] / df["total_assets"]
            df["altman_z"] = (
                1.2 * df["X1"] +
                1.4 * df["X2"] +
                3.3 * df["X3"] +
                0.6 * df["X4"] +
                1.0 * df["X5"]
            )
        else:
            df["altman_z"] = pd.NA

        return df

    def build_quarterly_factors(self, start_date: str = "2020-01-01") -> pd.DataFrame:
        """
        Build quarterly fundamental factors using quarterly financial statements.
        Each row represents one fiscal quarter with fundamental metrics calculated
        based on that quarter's financial data.
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format to filter quarters (default: '2020-01-01')
        
        Returns:
            DataFrame with quarterly fundamental factors (one row per quarter)
        """
        # Get quarterly statements and price data
        income, balance, cashflow = self.get_quarterly_statements()
        price_hist, shares_series = self.get_price_and_shares()
        t = self.yf_ticker

        if income.empty or balance.empty or cashflow.empty:
            raise ValueError(f"Missing financial statement data for {self.ticker}")

        # ---- Extract raw lines from quarterly statements ----
        net_income       = get_row(income,  ["NetIncome", "Net Income"])
        revenue          = get_row(income,  ["TotalRevenue", "Total Revenue"])
        gross_profit     = get_row(income,  ["GrossProfit", "Gross Profit"])
        operating_income = get_row(income,  ["OperatingIncome", "Operating Income"])
        ebit             = get_row(income,  ["Ebit", "EBIT"])
        interest_exp     = get_row(income,  ["InterestExpense", "Interest Expense"])

        ocf              = get_row(cashflow, ["OperatingCashFlow",
                                              "Total Cash From Operating Activities"])
        capex            = get_row(cashflow, ["CapitalExpenditures",
                                              "Capital Expenditure"])

        shareholder_equity = get_row(balance, ["TotalStockholderEquity",
                                               "Total Stockholder Equity", "StockholdersEquity"])
        total_assets       = get_row(balance, ["TotalAssets", "Total Assets"])
        total_liabilities  = get_row(balance, ["TotalLiab", "Total Liabilities"])
        current_assets     = get_row(balance, ["TotalCurrentAssets",
                                               "Total Current Assets", "CurrentAssets"])
        current_liab       = get_row(balance, ["TotalCurrentLiabilities",
                                               "Total Current Liabilities", "CurrentLiabilities"])
        inventory          = get_row(balance, ["Inventory"])
        total_debt         = get_row(balance, ["TotalDebt", "Total Debt"])
        cash               = get_row(balance, ["CashAndCashEquivalents",
                                               "Cash And Cash Equivalents", "CashCashEquivalentsAndShortTermInvestments"])
        retained_earnings  = get_row(balance, ["RetainedEarnings",
                                               "Retained Earnings"])
        
        # Get EBITDA
        ebitda_row = get_row(income, ["Ebitda", "EBITDA"])

        # Create DataFrame with quarterly data
        df = pd.DataFrame({
            "net_income":        net_income,
            "revenue":           revenue,
            "gross_profit":      gross_profit,
            "operating_income":  operating_income,
            "ebit":              ebit,
            "interest_exp":      interest_exp,
            "ocf":               ocf,
            "capex":             capex,
            "shareholder_equity": shareholder_equity,
            "total_assets":      total_assets,
            "total_liabilities": total_liabilities,
            "current_assets":    current_assets,
            "current_liab":      current_liab,
            "inventory":         inventory,
            "total_debt":        total_debt,
            "cash":              cash,
            "retained_earnings": retained_earnings,
        })

        if not ebitda_row.empty:
            df["ebitda"] = ebitda_row.reindex(df.index)
        else:
            df["ebitda"] = df.get("ebit", pd.NA)

        df.index.name = "fiscal_quarter_end"
        df = df.sort_index()
        
        # Filter by start_date
        df = df[df.index >= start_date]
        
        if df.empty:
            raise ValueError(f"No quarterly data found after {start_date}")
        
        print(f"Found {len(df)} quarters from {df.index[0].date()} to {df.index[-1].date()}")

        # --- Add price & shares for each quarter end date ---
        df["shares"] = align_to_dates(shares_series, df.index)
        df["price"]  = align_to_dates(price_hist, df.index)
        df["market_cap"] = df["price"] * df["shares"]

        # --- Calculate fundamental factors ---
        
        # Valuation metrics
        df["eps"] = safe_divide(df["net_income"], df["shares"])
        df["pe_trailing"] = safe_divide(df["price"], df["eps"])

        # Get forward PE/EPS snapshot (current values)
        info = t.get_info()
        df["forward_pe_snapshot"]  = info.get("forwardPE")
        df["forward_eps_snapshot"] = info.get("forwardEps")

        # P/B ratio
        if "shareholder_equity" in df.columns and not df["shareholder_equity"].isna().all():
            bvps = safe_divide(df["shareholder_equity"], df["shares"])
            df["pb"] = safe_divide(df["price"], bvps)
        else:
            df["pb"] = pd.NA
            
        df["ps"] = safe_divide(df["market_cap"], df["revenue"])

        # Enterprise Value
        df["ev"] = df["market_cap"] + df["total_debt"] - df["cash"]
        df["ev_ebitda"] = safe_divide(df["ev"], df["ebitda"])

        # Free Cash Flow
        df["fcf"] = df["ocf"] + df["capex"]  # capex is usually negative
        df["fcf_yield"] = safe_divide(df["fcf"], df["market_cap"])

        # Growth (Quarter-over-Quarter)
        df["revenue_growth_qoq"]  = df["revenue"].pct_change(fill_method=None)
        df["earnings_growth_qoq"] = df["net_income"].pct_change(fill_method=None)
        df["ocf_growth_qoq"]      = df["ocf"].pct_change(fill_method=None)
        df["fcf_growth_qoq"]      = df["fcf"].pct_change(fill_method=None)

        # Profitability & Leverage
        df["roe"] = safe_divide(df["net_income"], df["shareholder_equity"])
        df["roa"] = safe_divide(df["net_income"], df["total_assets"])
        df["gross_margin"] = safe_divide(df["gross_profit"], df["revenue"])
        df["operating_margin"] = safe_divide(df["operating_income"], df["revenue"])
        df["debt_to_equity"] = safe_divide(df["total_debt"], df["shareholder_equity"])
        
        if "ebit" in df.columns and "interest_exp" in df.columns:
            df["interest_coverage"] = safe_divide(df["ebit"], df["interest_exp"].abs())
        else:
            df["interest_coverage"] = pd.NA

        # Balance sheet strength
        df["current_ratio"] = safe_divide(df["current_assets"], df["current_liab"])
        
        if "current_assets" in df.columns and "current_liab" in df.columns and "inventory" in df.columns:
            df["quick_ratio"] = safe_divide(df["current_assets"] - df["inventory"], df["current_liab"])
        else:
            df["quick_ratio"] = pd.NA

        # Altman Z-Score
        required_altman_cols = ["current_assets", "current_liab", "total_assets", "retained_earnings", 
                                "ebit", "market_cap", "total_liabilities", "revenue"]
        if all(col in df.columns for col in required_altman_cols):
            df["X1"] = safe_divide(df["current_assets"] - df["current_liab"], df["total_assets"])
            df["X2"] = safe_divide(df["retained_earnings"], df["total_assets"])
            df["X3"] = safe_divide(df["ebit"], df["total_assets"])
            df["X4"] = safe_divide(df["market_cap"], df["total_liabilities"])
            df["X5"] = safe_divide(df["revenue"], df["total_assets"])
            df["altman_z"] = (
                1.2 * df["X1"] +
                1.4 * df["X2"] +
                3.3 * df["X3"] +
                0.6 * df["X4"] +
                1.0 * df["X5"]
            )
        else:
            df["altman_z"] = pd.NA

        print(f"✓ Generated {len(df)} quarters of fundamental data")
        return df

    def build_combined_factors(self, start_date: str = "2020-01-01") -> pd.DataFrame:
        """
        Build a combined dataframe with both quarterly and annual fundamental factors.
        This creates a wide-format dataframe suitable for OLAP databases like ClickHouse.
        
        The dataframe will have quarterly data as rows, with columns prefixed as:
        - 'quarterly_*' for quarterly metrics
        - 'annual_*' for annual metrics
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format to filter data (default: '2020-01-01')
        
        Returns:
            DataFrame with combined quarterly and annual factors (column-major format)
        """
        print("\n" + "="*60)
        print("Building COMBINED (Quarterly + Annual) factors...")
        print("="*60)
        
        # Build quarterly factors
        print("\n[1/2] Fetching quarterly data...")
        quarterly_df = self.build_quarterly_factors(start_date=start_date)
        
        # Build annual factors
        print("\n[2/2] Fetching annual data...")
        # Calculate years_back from start_date
        start_year = pd.Timestamp(start_date).year
        current_year = pd.Timestamp.now().year
        years_back = current_year - start_year + 1
        annual_df = self.build_annual_factors(years_back=years_back)
        
        # Prefix column names
        quarterly_df = quarterly_df.add_prefix('quarterly_')
        annual_df = annual_df.add_prefix('annual_')
        
        # Rename index to avoid conflicts
        quarterly_df.index.name = 'date'
        annual_df.index.name = 'date'
        
        # For each quarterly date, find the corresponding annual data
        # (use the most recent annual report available at that quarter end)
        print("\n[3/3] Aligning annual data to quarterly dates...")
        
        # Create a mapping of quarterly dates to their corresponding annual values
        aligned_annual_data = {}
        for col in annual_df.columns:
            aligned_annual_data[col] = align_to_dates(annual_df[col], quarterly_df.index)
        
        aligned_annual_df = pd.DataFrame(aligned_annual_data, index=quarterly_df.index)
        
        # Concatenate quarterly and annual data horizontally
        combined_df = pd.concat([quarterly_df, aligned_annual_df], axis=1)
        combined_df.index.name = 'fiscal_date'
        
        print(f"\n✓ Combined dataframe shape: {combined_df.shape}")
        print(f"  - Quarterly columns: {len(quarterly_df.columns)}")
        print(f"  - Annual columns: {len(aligned_annual_df.columns)}")
        print(f"  - Total columns: {len(combined_df.columns)}")
        print(f"  - Rows (quarterly periods): {len(combined_df)}")
        
        return combined_df


# ---------- earnings-related helpers (use BaseFinanceLoader, not inheritance) ----------

def get_eps_surprises(ticker: str, limit: int = 16) -> pd.DataFrame:
    """
    Use helpers indirectly: just instantiate BaseFinanceLoader and access .yf_ticker.
    """
    loader = BaseFinanceLoader(ticker)
    t = loader.yf_ticker

    ed = t.get_earnings_dates(limit=limit)
    if ed is None or ed.empty:
        return pd.DataFrame()

    est = ed.get("EPS Estimate")
    act = ed.get("Reported EPS")

    out = pd.DataFrame({
        "eps_estimate": est,
        "eps_actual":   act,
    })
    out["eps_surprise"] = out["eps_actual"] - out["eps_estimate"]
    out["eps_surprise_pct"] = out["eps_surprise"] / out["eps_estimate"].abs()
    return out


def get_days_to_next_earnings(ticker: str):
    loader = BaseFinanceLoader(ticker)
    t = loader.yf_ticker

    ed = t.get_earnings_dates(limit=8)
    if ed is None or ed.empty:
        return None

    now = pd.Timestamp.now(tz="UTC")
    future = ed[ed.index >= now]
    if future.empty:
        return None

    next_date = future.index.min()
    return (next_date - now).days
