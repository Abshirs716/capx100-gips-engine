"""
CapX100 Universal Data Processor - THE MOUTH
=============================================
Ingestion Layer for Real-World RIA Data

Project: LIFELINE
Purpose: Clean messy Schwab/Fidelity/Pershing CSV exports before Risk Engine

CAPABILITIES:
- Universal Header Mapping (variations → standard names)
- Currency/Percent Sanitization ($1,000.00 → 1000.0)
- Date Normalization (auto-detect formats)
- Asset Class Mapping (variations → standard categories)
- NaN/Null Handling (smart fill or drop)

VECTOR'S DIRECTIVE: Real RIA data is MESSY. This module makes it clean.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


# =============================================================================
# UNIVERSAL COLUMN MAPPINGS
# =============================================================================
# Maps variations from Schwab, Fidelity, Pershing, etc. to our standard names

COLUMN_MAPPINGS = {
    # -------------------------------------------------------------------------
    # SYMBOL / TICKER
    # -------------------------------------------------------------------------
    'symbol': 'Symbol',
    'ticker': 'Symbol',
    'asset': 'Symbol',
    'security': 'Symbol',
    'cusip': 'CUSIP',
    'isin': 'ISIN',
    'sedol': 'SEDOL',
    'security_id': 'Symbol',
    'fund': 'Symbol',
    'holding': 'Symbol',
    'investment': 'Symbol',

    # -------------------------------------------------------------------------
    # MARKET VALUE
    # -------------------------------------------------------------------------
    'market_value': 'Market_Value',
    'mkt_val': 'Market_Value',
    'mkt val': 'Market_Value',
    'marketvalue': 'Market_Value',
    'current_value': 'Market_Value',
    'current value': 'Market_Value',
    'currentvalue': 'Market_Value',
    'value': 'Market_Value',
    'amt': 'Market_Value',
    'amount': 'Market_Value',
    'total_value': 'Market_Value',
    'total value': 'Market_Value',
    'ending_value': 'Market_Value',
    'ending value': 'Market_Value',
    'balance': 'Market_Value',
    'position_value': 'Market_Value',

    # -------------------------------------------------------------------------
    # QUANTITY / SHARES
    # -------------------------------------------------------------------------
    'quantity': 'Quantity',
    'qty': 'Quantity',
    'shares': 'Quantity',
    'units': 'Quantity',
    'position': 'Quantity',
    'holding_qty': 'Quantity',
    'num_shares': 'Quantity',

    # -------------------------------------------------------------------------
    # PRICE
    # -------------------------------------------------------------------------
    'price': 'Price',
    'current_price': 'Price',
    'current price': 'Price',
    'last_price': 'Price',
    'last price': 'Price',
    'close': 'Price',
    'closing_price': 'Price',
    'nav': 'Price',
    'unit_price': 'Price',

    # -------------------------------------------------------------------------
    # COST BASIS
    # -------------------------------------------------------------------------
    'cost_basis': 'Cost_Basis',
    'cost basis': 'Cost_Basis',
    'costbasis': 'Cost_Basis',
    'cost': 'Cost_Basis',
    'avg_cost': 'Cost_Basis',
    'average_cost': 'Cost_Basis',
    'purchase_price': 'Cost_Basis',
    'book_value': 'Cost_Basis',
    'acquisition_cost': 'Cost_Basis',

    # -------------------------------------------------------------------------
    # GAIN / LOSS
    # -------------------------------------------------------------------------
    'gain_loss': 'Gain_Loss',
    'gain/loss': 'Gain_Loss',
    'gainloss': 'Gain_Loss',
    'unrealized_gain': 'Gain_Loss',
    'unrealized gain': 'Gain_Loss',
    'unrealized_pl': 'Gain_Loss',
    'pnl': 'Gain_Loss',
    'p&l': 'Gain_Loss',
    'profit_loss': 'Gain_Loss',

    # -------------------------------------------------------------------------
    # RETURN / PERFORMANCE
    # -------------------------------------------------------------------------
    'return': 'Return',
    'returns': 'Return',
    'total_return': 'Return',
    'total return': 'Return',
    'pct_return': 'Return',
    'percent_return': 'Return',
    'performance': 'Return',
    'ytd_return': 'YTD_Return',
    'mtd_return': 'MTD_Return',
    'qtd_return': 'QTD_Return',

    # -------------------------------------------------------------------------
    # DATE
    # -------------------------------------------------------------------------
    'date': 'Date',
    'trade_date': 'Date',
    'trade date': 'Date',
    'transaction_date': 'Date',
    'as_of_date': 'Date',
    'as of date': 'Date',
    'period': 'Date',
    'month': 'Date',
    'settlement_date': 'Settlement_Date',

    # -------------------------------------------------------------------------
    # ASSET CLASS / CATEGORY
    # -------------------------------------------------------------------------
    'asset_class': 'Asset_Class',
    'asset class': 'Asset_Class',
    'asset class code': 'Asset_Class',
    'asset_class_code': 'Asset_Class',
    'assetclasscode': 'Asset_Class',
    'assetclass': 'Asset_Class',
    'category': 'Asset_Class',
    'type': 'Asset_Class',
    'asset_type': 'Asset_Class',
    'asset type': 'Asset_Class',
    'security_type': 'Asset_Class',
    'investment_type': 'Asset_Class',
    'sector': 'Sector',
    'industry': 'Industry',

    # -------------------------------------------------------------------------
    # ACCOUNT
    # -------------------------------------------------------------------------
    'account': 'Account',
    'account_number': 'Account',
    'account number': 'Account',
    'acct': 'Account',
    'account_id': 'Account',
    'portfolio': 'Account',
    'client': 'Client',
    'client_id': 'Client',

    # -------------------------------------------------------------------------
    # WEIGHT / ALLOCATION
    # -------------------------------------------------------------------------
    'weight': 'Weight',
    'allocation': 'Weight',
    'pct_of_portfolio': 'Weight',
    'percent_of_portfolio': 'Weight',
    '% of portfolio': 'Weight',
    'portfolio_weight': 'Weight',

    # -------------------------------------------------------------------------
    # DESCRIPTION / NAME
    # -------------------------------------------------------------------------
    'description': 'Description',
    'name': 'Description',
    'security_name': 'Description',
    'security name': 'Description',
    'asset_name': 'Description',
    'holding_name': 'Description',

    # -------------------------------------------------------------------------
    # TRANSACTION ACTION (for wash sales detection)
    # -------------------------------------------------------------------------
    'action': 'Action',
    'transaction_type': 'Action',
    'transaction type': 'Action',
    'trans_type': 'Action',
    'type': 'Action',
    'activity': 'Action',
    'activity_type': 'Action',
    'trade_type': 'Action',
    'order_type': 'Action',
    'side': 'Action',  # Buy/Sell side

    # -------------------------------------------------------------------------
    # TRANSACTION ID
    # -------------------------------------------------------------------------
    'transaction_id': 'Transaction_ID',
    'trans_id': 'Transaction_ID',
    'order_id': 'Transaction_ID',
    'trade_id': 'Transaction_ID',
    'confirmation': 'Transaction_ID',
    'confirm_number': 'Transaction_ID',

    # -------------------------------------------------------------------------
    # FEES / COMMISSION
    # -------------------------------------------------------------------------
    'commission': 'Commission',
    'comm': 'Commission',
    'fees': 'Fees',
    'fee': 'Fees',
    'charges': 'Fees',

    # -------------------------------------------------------------------------
    # GROSS / NET AMOUNTS
    # -------------------------------------------------------------------------
    'gross_amount': 'Gross_Amount',
    'gross amount': 'Gross_Amount',
    'net_amount': 'Net_Amount',
    'net amount': 'Net_Amount',
    'proceeds': 'Net_Amount',
    'total_amount': 'Net_Amount',
}


# =============================================================================
# ASSET CLASS MAPPINGS
# =============================================================================
# Normalizes various asset class names to standard categories

ASSET_CLASS_MAPPINGS = {
    # =========================================================================
    # INDUSTRY CODE MAPPINGS (Schwab, Fidelity, Pershing standardized codes)
    # =========================================================================
    # Equity codes (EQ-*)
    'eq-us-lc': 'Equity',         # US Large Cap
    'eq-us-mc': 'Equity',         # US Mid Cap
    'eq-us-sc': 'Equity',         # US Small Cap
    'eq-us-val': 'Equity',        # US Value
    'eq-us-growth': 'Equity',     # US Growth
    'eq-us-tech': 'Equity',       # US Technology
    'eq-us-blend': 'Equity',      # US Blend
    'eq-intl-dev': 'International Equity',  # International Developed
    'eq-intl-em': 'Emerging Markets',       # Emerging Markets
    'eq-intl': 'International Equity',      # International (generic)

    # Fixed Income codes (FI-*)
    'fi-ig-core': 'Fixed Income',   # Investment Grade Core
    'fi-ig-corp': 'Fixed Income',   # Investment Grade Corporate
    'fi-ig-govt': 'Fixed Income',   # Investment Grade Government
    'fi-hy': 'High Yield',          # High Yield
    'fi-muni': 'Municipal Bonds',   # Municipal Bonds
    'fi-tips': 'Fixed Income',      # TIPS/Inflation Protected
    'fi-em': 'Fixed Income',        # Emerging Market Bonds
    'fi-corp': 'Fixed Income',      # Corporate Bonds (generic)

    # Cash codes (CASH-*)
    'cash-eq': 'Cash',              # Cash Equivalent
    'cash-mm': 'Cash',              # Money Market
    'cash-st': 'Cash',              # Short Term

    # Alternative codes (ALT-*)
    'alt-crypto': 'Alternatives',   # Cryptocurrency
    'alt-pe': 'Alternatives',       # Private Equity
    'alt-hf': 'Alternatives',       # Hedge Funds
    'alt-re': 'Real Estate',        # Real Estate (Alt bucket)
    'alt-comm': 'Commodities',      # Commodities
    'alt-infra': 'Alternatives',    # Infrastructure

    # Real Estate codes (RE-*)
    're-reit': 'Real Estate',       # REITs
    're-direct': 'Real Estate',     # Direct Real Estate

    # =========================================================================
    # TRADITIONAL MAPPINGS (plain text variations)
    # =========================================================================
    # Equity
    'equity': 'Equity',
    'equities': 'Equity',
    'stock': 'Equity',
    'stocks': 'Equity',
    'us stocks': 'Equity',
    'us stock': 'Equity',
    'domestic equity': 'Equity',
    'domestic equities': 'Equity',
    'us equity': 'Equity',
    'american stocks': 'Equity',
    'large cap': 'Equity',
    'mid cap': 'Equity',
    'small cap': 'Equity',
    'growth': 'Equity',
    'value': 'Equity',
    'blend': 'Equity',

    # International Equity
    'international equity': 'International Equity',
    'international equities': 'International Equity',
    'intl equity': 'International Equity',
    'foreign equity': 'International Equity',
    'foreign stocks': 'International Equity',
    'developed markets': 'International Equity',
    'emerging markets': 'Emerging Markets',
    'em': 'Emerging Markets',
    'eafe': 'International Equity',

    # Fixed Income
    'fixed income': 'Fixed Income',
    'bonds': 'Fixed Income',
    'bond': 'Fixed Income',
    'debt': 'Fixed Income',
    'fixed': 'Fixed Income',
    'corporate bonds': 'Fixed Income',
    'government bonds': 'Fixed Income',
    'treasuries': 'Fixed Income',
    'treasury': 'Fixed Income',
    'municipal bonds': 'Municipal Bonds',
    'muni': 'Municipal Bonds',
    'munis': 'Municipal Bonds',
    'high yield': 'High Yield',
    'junk bonds': 'High Yield',
    'investment grade': 'Fixed Income',

    # Cash & Equivalents
    'cash': 'Cash',
    'cash equivalents': 'Cash',
    'cash & equivalents': 'Cash',
    'money market': 'Cash',
    'mm': 'Cash',
    'mmf': 'Cash',
    'short term': 'Cash',
    'liquidity': 'Cash',

    # Alternatives
    'alternative': 'Alternatives',
    'alternatives': 'Alternatives',
    'alts': 'Alternatives',
    'hedge fund': 'Alternatives',
    'hedge funds': 'Alternatives',
    'private equity': 'Alternatives',
    'pe': 'Alternatives',
    'real assets': 'Alternatives',
    'commodities': 'Commodities',
    'commodity': 'Commodities',
    'gold': 'Commodities',
    'crypto': 'Alternatives',
    'cryptocurrency': 'Alternatives',
    'bitcoin': 'Alternatives',

    # Real Estate
    'real estate': 'Real Estate',
    'reits': 'Real Estate',
    'reit': 'Real Estate',
    'property': 'Real Estate',

    # Other
    'other': 'Other',
    'misc': 'Other',
    'miscellaneous': 'Other',
    'unknown': 'Other',
}


# =============================================================================
# MAIN DATA PROCESSOR CLASS
# =============================================================================

class DataProcessor:
    """
    Universal Data Processor for RIA CSV/Excel files.

    Handles messy exports from Schwab, Fidelity, Pershing, etc.
    Cleans and standardizes data for the Risk Engine.
    """

    def __init__(self, verbose: bool = True):
        self.column_mappings = COLUMN_MAPPINGS
        self.asset_class_mappings = ASSET_CLASS_MAPPINGS
        self.verbose = verbose
        self.processing_log = []

    def log(self, message: str):
        """Add message to processing log."""
        self.processing_log.append(message)

    def get_log(self) -> List[str]:
        """Return processing log."""
        return self.processing_log

    def clear_log(self):
        """Clear processing log."""
        self.processing_log = []

    # =========================================================================
    # JUNK ROW DETECTION & HEADER FINDING
    # =========================================================================
    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Detect the actual header row in messy CSV files.

        Looks for rows containing typical column header keywords like:
        'symbol', 'ticker', 'value', 'quantity', 'price', 'description', etc.

        Returns:
            Row index of the actual header row (0-based)
        """
        header_keywords = [
            'symbol', 'ticker', 'cusip', 'isin', 'security',
            'value', 'market', 'quantity', 'qty', 'shares',
            'price', 'cost', 'description', 'name', 'asset',
            'account', 'weight', 'allocation', 'return'
        ]

        # Check first 20 rows for header keywords
        max_rows = min(20, len(df))

        for idx in range(max_rows):
            row_values = df.iloc[idx].astype(str).str.lower()
            matches = sum(1 for val in row_values for kw in header_keywords if kw in val)

            # If we find 3+ header keywords in a row, it's likely the header
            if matches >= 3:
                self.log(f"🔍 Found header row at index {idx}")
                return idx

        return 0  # Default to first row if no header detected

    def skip_junk_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Skip junk rows at the top of messy CSV files and reset headers.

        Handles files from Schwab, Fidelity, etc. that have report metadata
        at the top before the actual data.
        """
        header_idx = self.find_header_row(df)

        if header_idx > 0:
            self.log(f"⏭️ Skipping {header_idx} junk rows at top of file")

            # Set the correct row as header
            new_headers = df.iloc[header_idx].astype(str).tolist()

            # Take data starting from row after header
            df = df.iloc[header_idx + 1:].copy()
            df.columns = new_headers
            df = df.reset_index(drop=True)

            # Remove any trailing junk rows (totals, disclaimers, etc.)
            # Look for rows with mostly NaN or rows starting with keywords like "Total", "**"
            junk_indicators = ['total', '**', '*', 'disclaimer', 'note:']
            rows_to_drop = []

            for idx, row in df.iterrows():
                first_val = str(row.iloc[0]).lower().strip() if pd.notna(row.iloc[0]) else ''
                if any(first_val.startswith(ind) for ind in junk_indicators):
                    rows_to_drop.append(idx)
                    continue

                # Also drop rows that are mostly empty
                non_null = row.dropna()
                if len(non_null) <= 1:
                    rows_to_drop.append(idx)

            if rows_to_drop:
                df = df.drop(rows_to_drop)
                df = df.reset_index(drop=True)
                self.log(f"🗑️ Removed {len(rows_to_drop)} junk/total rows from bottom")

        return df

    # =========================================================================
    # HEADER MAPPING
    # =========================================================================
    def map_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map column headers to standard names.

        Uses fuzzy matching to handle variations like:
        - 'Mkt Val' -> 'Market_Value'
        - 'Ticker' -> 'Symbol'
        """
        df = df.copy()
        renamed_count = 0

        new_columns = {}
        used_names = set()  # Track used names to avoid duplicates

        for col in df.columns:
            col_lower = col.lower().strip()

            # Direct match
            if col_lower in self.column_mappings:
                target_name = self.column_mappings[col_lower]
                # Avoid duplicates
                if target_name in used_names:
                    target_name = f"{target_name}_{len(used_names)}"
                new_columns[col] = target_name
                used_names.add(target_name)
                renamed_count += 1
            else:
                # Fuzzy match - check if any key is contained in column name
                matched = False
                for key, standard in self.column_mappings.items():
                    if key in col_lower or col_lower in key:
                        target_name = standard
                        # Avoid duplicates
                        if target_name in used_names:
                            target_name = f"{target_name}_{len(used_names)}"
                        new_columns[col] = target_name
                        used_names.add(target_name)
                        renamed_count += 1
                        matched = True
                        break

                if not matched:
                    # Keep original but clean it
                    clean_name = col.strip().replace(' ', '_')
                    if clean_name in used_names:
                        clean_name = f"{clean_name}_{len(used_names)}"
                    new_columns[col] = clean_name
                    used_names.add(clean_name)

        df.rename(columns=new_columns, inplace=True)
        self.log(f"✅ Header mapping: Renamed {renamed_count} columns")

        return df

    # =========================================================================
    # CURRENCY & NUMBER SANITIZATION
    # =========================================================================
    def sanitize_currency(self, value: Any) -> Optional[float]:
        """
        Convert currency strings to float.

        Handles: $1,000.00, €500, £1.5K, (1,000) for negatives
        """
        if pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str):
            return None

        original = value
        value = value.strip()

        # Handle empty strings
        if not value or value in ['-', '--', 'N/A', 'n/a', 'NA', 'null', 'NULL']:
            return None

        # Check for negative in parentheses: (1,000.00)
        is_negative = False
        if value.startswith('(') and value.endswith(')'):
            is_negative = True
            value = value[1:-1]

        # Also check for minus sign
        if value.startswith('-'):
            is_negative = True
            value = value[1:]

        # Remove currency symbols
        value = re.sub(r'[$€£¥₹]', '', value)

        # Remove commas and spaces
        value = value.replace(',', '').replace(' ', '')

        # Handle K/M/B suffixes
        multiplier = 1
        if value.upper().endswith('K'):
            multiplier = 1000
            value = value[:-1]
        elif value.upper().endswith('M'):
            multiplier = 1000000
            value = value[:-1]
        elif value.upper().endswith('B'):
            multiplier = 1000000000
            value = value[:-1]

        try:
            result = float(value) * multiplier
            if is_negative:
                result = -result
            return result
        except ValueError:
            self.log(f"⚠️ Could not parse currency: '{original}'")
            return None

    def sanitize_percentage(self, value: Any) -> Optional[float]:
        """
        Convert percentage strings to decimal.

        Handles: 5.4%, -2.1%, +3.5%
        Returns: 0.054, -0.021, 0.035
        """
        if pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            # If already a number, check if it needs conversion
            # Values > 1 or < -1 are likely percentages
            if abs(value) > 1:
                return value / 100
            return float(value)

        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value or value in ['-', '--', 'N/A', 'n/a']:
            return None

        # Remove % sign
        if '%' in value:
            value = value.replace('%', '').strip()

        # Remove + sign
        value = value.replace('+', '')

        try:
            result = float(value) / 100  # Convert to decimal
            return result
        except ValueError:
            self.log(f"⚠️ Could not parse percentage: '{value}'")
            return None

    def sanitize_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sanitize all numeric columns (currency, percentages).
        """
        df = df.copy()

        # Columns that should be currency values
        currency_columns = [
            'Market_Value', 'Cost_Basis', 'Price', 'Gain_Loss',
            'Amount', 'Balance', 'Value'
        ]

        # Columns that should be percentages (convert to decimal)
        percentage_columns = [
            'Return', 'YTD_Return', 'MTD_Return', 'QTD_Return',
            'Weight', 'Allocation'
        ]

        # Process currency columns
        for col in df.columns:
            if col in currency_columns:
                df[col] = df[col].apply(self.sanitize_currency)
                self.log(f"💵 Sanitized currency column: {col}")

        # Process percentage columns
        for col in df.columns:
            if col in percentage_columns:
                df[col] = df[col].apply(self.sanitize_percentage)
                self.log(f"📊 Sanitized percentage column: {col}")

        # Auto-detect and clean remaining numeric-looking columns
        for col in df.columns:
            if col not in currency_columns and col not in percentage_columns:
                try:
                    col_data = df[col]
                    # Handle case where column selection returns DataFrame (duplicate cols)
                    if isinstance(col_data, pd.DataFrame):
                        col_data = col_data.iloc[:, 0]

                    if str(col_data.dtype) == 'object':
                        # Sample first non-null value
                        non_null = col_data.dropna()
                        if len(non_null) > 0:
                            sample = non_null.iloc[0]
                            if isinstance(sample, str):
                                # Check if it looks like currency
                                if '$' in sample or '€' in sample or '£' in sample:
                                    df[col] = col_data.apply(self.sanitize_currency)
                                    self.log(f"💵 Auto-detected currency: {col}")
                                # Check if it looks like percentage
                                elif '%' in sample:
                                    df[col] = col_data.apply(self.sanitize_percentage)
                                    self.log(f"📊 Auto-detected percentage: {col}")
                except Exception as e:
                    self.log(f"⚠️ Skipped column {col}: {str(e)}")

        return df

    # =========================================================================
    # DATE NORMALIZATION
    # =========================================================================
    def normalize_date(self, value: Any) -> Optional[datetime]:
        """
        Auto-detect and normalize date formats.

        Handles: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.
        """
        if pd.isna(value):
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()

        if not isinstance(value, str):
            return None

        value = value.strip()

        # Common date formats to try
        date_formats = [
            '%Y-%m-%d',      # 2025-01-15
            '%m/%d/%Y',      # 01/15/2025
            '%d/%m/%Y',      # 15/01/2025
            '%m-%d-%Y',      # 01-15-2025
            '%d-%m-%Y',      # 15-01-2025
            '%Y/%m/%d',      # 2025/01/15
            '%b %d, %Y',     # Jan 15, 2025
            '%B %d, %Y',     # January 15, 2025
            '%d %b %Y',      # 15 Jan 2025
            '%d %B %Y',      # 15 January 2025
            '%Y%m%d',        # 20250115
            '%m/%d/%y',      # 01/15/25
            '%d/%m/%y',      # 15/01/25
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        self.log(f"⚠️ Could not parse date: '{value}'")
        return None

    def normalize_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize all date columns.
        """
        df = df.copy()

        date_columns = ['Date', 'Settlement_Date', 'Trade_Date', 'As_Of_Date']

        for col in df.columns:
            if col in date_columns or 'date' in col.lower():
                df[col] = df[col].apply(self.normalize_date)
                self.log(f"📅 Normalized date column: {col}")

        return df

    # =========================================================================
    # ASSET CLASS NORMALIZATION - FUZZY KEYWORD MAPPER
    # =========================================================================

    # FUZZY KEYWORD GROUPS - catches messy data from Schwab/Fidelity/Pershing
    # NOTE: Order matters! Alternatives checked FIRST to catch "Private Equity" before "Equity"

    FUZZY_ALTERNATIVES_KEYWORDS = [
        'alternative', 'alts', 'hedge', 'private equity', 'private',
        'commodity', 'commodities', 'gold', 'silver', 'crypto', 'infrastructure',
        'real asset', 'other investment'
    ]

    # Exact match alternatives (for short words like "Alt" that could be substring of other words)
    FUZZY_ALTERNATIVES_EXACT = ['alt']

    FUZZY_CASH_KEYWORDS = [
        'cash', 'money market', 'money mkt', 'mm fund', 'mmf', 'sweep',
        'liquidity', 'short term', 'equivalent', 'settlement'
    ]

    FUZZY_FIXED_INCOME_KEYWORDS = [
        'bond', 'fixed', 'income', 'muni', 'municipal', 'treasury',
        'govt', 'government', 'corporate', 'corp', 'investment grade',
        'high yield', 'tips', 'aggregate', 'debt', 'note', 'bill'
    ]

    FUZZY_EQUITY_KEYWORDS = [
        'stock', 'equity', 'eqty', 'equities', 'common', 'share', 'etf',
        'domestic', 'intl', 'international', 'emerging', 'large cap',
        'mid cap', 'small cap', 'growth', 'value', 'blend', 'tech',
        'technology', 'healthcare', 'financial', 'consumer', 'energy',
        'industrials', 'materials', 'utilities', 'reit', 'real estate'
    ]

    def normalize_asset_class(self, value: Any) -> str:
        """
        Normalize asset class names to standard categories using FUZZY KEYWORD MATCHING.

        AGGRESSIVE MATCHING - catches messy variations:
        - 'US Stocks' -> 'Equity'
        - 'Domestic Equity' -> 'Equity'
        - 'Technology' -> 'Equity' (sector implies equity)
        - 'Muni Bond Fund' -> 'Fixed Income'
        """
        if pd.isna(value):
            return 'Other'

        if not isinstance(value, str):
            return 'Other'

        value_lower = value.lower().strip()

        # Step 1: Direct match in mappings dictionary
        if value_lower in self.asset_class_mappings:
            return self.asset_class_mappings[value_lower]

        # Step 2: Check if any mapping key is contained in value
        for key, standard in self.asset_class_mappings.items():
            if key in value_lower:
                return standard

        # Step 3: FUZZY KEYWORD MATCHING (catches everything else)
        # ORDER MATTERS! Check more specific categories FIRST

        # Check Alternatives FIRST (to catch "Private Equity" before "Equity")
        for kw in self.FUZZY_ALTERNATIVES_KEYWORDS:
            if kw in value_lower:
                self.log(f"🎯 Fuzzy matched '{value}' -> Alternatives (keyword: {kw})")
                return 'Alternatives'

        # Check exact-match alternatives (short words like "Alt")
        if value_lower in self.FUZZY_ALTERNATIVES_EXACT:
            self.log(f"🎯 Exact matched '{value}' -> Alternatives")
            return 'Alternatives'

        # Check Cash keywords
        for kw in self.FUZZY_CASH_KEYWORDS:
            if kw in value_lower:
                self.log(f"🎯 Fuzzy matched '{value}' -> Cash (keyword: {kw})")
                return 'Cash'

        # Check Fixed Income keywords
        for kw in self.FUZZY_FIXED_INCOME_KEYWORDS:
            if kw in value_lower:
                self.log(f"🎯 Fuzzy matched '{value}' -> Fixed Income (keyword: {kw})")
                return 'Fixed Income'

        # Check Equity keywords LAST (most general category)
        for kw in self.FUZZY_EQUITY_KEYWORDS:
            if kw in value_lower:
                self.log(f"🎯 Fuzzy matched '{value}' -> Equity (keyword: {kw})")
                return 'Equity'

        # Step 4: Last resort - return original (NOT "Other" to preserve data)
        self.log(f"⚠️ Could not classify asset class: '{value}'")
        return value.strip()

    def normalize_asset_class_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize Asset_Class column if present.
        """
        df = df.copy()

        if 'Asset_Class' in df.columns:
            df['Asset_Class'] = df['Asset_Class'].apply(self.normalize_asset_class)
            self.log(f"🏷️ Normalized asset classes")

        return df

    # =========================================================================
    # TICKER-BASED ASSET CLASS CLASSIFICATION
    # =========================================================================

    # Common ETFs and their asset classes - DYNAMIC classification
    TICKER_ASSET_MAP = {
        # Fixed Income ETFs
        'AGG': 'Fixed Income', 'BND': 'Fixed Income', 'LQD': 'Fixed Income',
        'TLT': 'Fixed Income', 'IEF': 'Fixed Income', 'SHY': 'Fixed Income',
        'VCIT': 'Fixed Income', 'VCSH': 'Fixed Income', 'MUB': 'Fixed Income',
        'HYG': 'Fixed Income', 'JNK': 'Fixed Income', 'EMB': 'Fixed Income',
        'BNDX': 'Fixed Income', 'TIP': 'Fixed Income', 'TIPS': 'Fixed Income',
        'GOVT': 'Fixed Income', 'SCHZ': 'Fixed Income', 'IUSB': 'Fixed Income',

        # Cash / Money Market
        'SHV': 'Cash', 'BIL': 'Cash', 'SGOV': 'Cash', 'MINT': 'Cash',
        'SWVXX': 'Cash', 'SNAXX': 'Cash', 'VMFXX': 'Cash', 'FDRXX': 'Cash',
        'SPRXX': 'Cash', 'SPAXX': 'Cash', 'FZFXX': 'Cash', 'TTTXX': 'Cash',

        # Alternatives / Commodities / Real Estate
        'GLD': 'Alternatives', 'IAU': 'Alternatives', 'SLV': 'Alternatives',
        'DBC': 'Alternatives', 'GSG': 'Alternatives', 'PDBC': 'Alternatives',
        'VNQ': 'Alternatives', 'IYR': 'Alternatives', 'XLRE': 'Alternatives',
        'SCHH': 'Alternatives', 'RWR': 'Alternatives', 'REIT': 'Alternatives',
        'BITO': 'Alternatives', 'GBTC': 'Alternatives',

        # International Equity
        'VXUS': 'Equity', 'EFA': 'Equity', 'VEU': 'Equity', 'VWO': 'Equity',
        'EEM': 'Equity', 'IEFA': 'Equity', 'IEMG': 'Equity', 'IXUS': 'Equity',
    }

    # Keywords for description-based classification
    DESCRIPTION_ASSET_KEYWORDS = {
        'Fixed Income': ['bond', 'fixed', 'treasury', 'govt', 'municipal', 'muni',
                         'corporate', 'aggregate', 'income', 'debt', 'note'],
        'Cash': ['money', 'sweep', 'cash', 'liquidity', 'mm fund', 'money market'],
        'Alternatives': ['gold', 'silver', 'commodity', 'real estate', 'reit',
                         'alternative', 'hedge', 'private', 'infrastructure'],
    }

    def classify_by_ticker(self, ticker: str, description: str = '') -> str:
        """
        Classify asset class based on ticker symbol and description.

        DYNAMIC: Works with ANY ticker or description.

        Args:
            ticker: Stock/ETF ticker symbol
            description: Security description

        Returns:
            Asset class ('Equity', 'Fixed Income', 'Cash', 'Alternatives')
        """
        if not ticker:
            return 'Other'

        ticker_upper = ticker.upper().strip()

        # Priority 1: Known ticker mapping
        if ticker_upper in self.TICKER_ASSET_MAP:
            return self.TICKER_ASSET_MAP[ticker_upper]

        # Priority 2: Check description keywords
        if description:
            desc_lower = description.lower()
            for asset_class, keywords in self.DESCRIPTION_ASSET_KEYWORDS.items():
                for kw in keywords:
                    if kw in desc_lower:
                        return asset_class

        # Priority 3: Default to Equity (individual stocks)
        # Most tickers without specific mapping are equities
        return 'Equity'

    def add_asset_class_from_ticker(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Asset_Class column based on ticker/symbol classification.

        DYNAMIC: Used when no Asset_Class column exists in source data.

        Args:
            df: DataFrame with Symbol/Ticker column

        Returns:
            DataFrame with Asset_Class column added
        """
        df = df.copy()

        # Find symbol column
        symbol_col = None
        for col in ['Symbol', 'Ticker', 'symbol', 'ticker', 'SYMBOL', 'TICKER']:
            if col in df.columns:
                symbol_col = col
                break

        if symbol_col is None:
            self.log("⚠️ No Symbol/Ticker column found for asset classification")
            df['Asset_Class'] = 'Other'
            return df

        # Find description column
        desc_col = None
        for col in ['Description', 'Security Name', 'Name', 'description', 'name']:
            if col in df.columns:
                desc_col = col
                break

        # Classify each row
        asset_classes = []
        for idx, row in df.iterrows():
            ticker = str(row.get(symbol_col, '')).strip()
            description = str(row.get(desc_col, '')) if desc_col else ''
            asset_class = self.classify_by_ticker(ticker, description)
            asset_classes.append(asset_class)

        df['Asset_Class'] = asset_classes
        self.log(f"🏷️ Classified {len(df)} positions by ticker/description")

        # Log classification breakdown
        class_counts = df['Asset_Class'].value_counts()
        for cls, count in class_counts.items():
            self.log(f"   - {cls}: {count} positions")

        return df

    # =========================================================================
    # NULL / NaN HANDLING
    # =========================================================================
    def handle_nulls(
        self,
        df: pd.DataFrame,
        fill_numeric: float = 0.0,
        drop_if_missing: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Handle null/NaN values.

        - Numeric columns: Fill with specified value (default 0)
        - Drop rows if critical columns are missing
        """
        df = df.copy()

        # Drop rows missing critical columns
        if drop_if_missing:
            before_count = len(df)
            for col in drop_if_missing:
                if col in df.columns:
                    df = df.dropna(subset=[col])
            after_count = len(df)
            if before_count != after_count:
                self.log(f"🗑️ Dropped {before_count - after_count} rows with missing critical data")

        # Fill numeric nulls
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            null_count = df[col].isna().sum()
            if null_count > 0:
                df[col].fillna(fill_numeric, inplace=True)
                self.log(f"📝 Filled {null_count} nulls in '{col}' with {fill_numeric}")

        return df

    # =========================================================================
    # QUANTITY HANDLING (Long/Short)
    # =========================================================================
    def detect_short_positions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect and flag short positions.

        Adds 'Is_Short' column based on negative quantity or market value.
        """
        df = df.copy()

        if 'Quantity' in df.columns:
            # Convert to numeric first
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Is_Short'] = df['Quantity'] < 0
            short_count = df['Is_Short'].sum()
            if short_count > 0:
                self.log(f"📉 Detected {short_count} short positions")
        elif 'Market_Value' in df.columns:
            df['Is_Short'] = pd.to_numeric(df['Market_Value'], errors='coerce').fillna(0) < 0
            short_count = df['Is_Short'].sum()
            if short_count > 0:
                self.log(f"📉 Detected {short_count} short positions (from Market_Value)")
        else:
            df['Is_Short'] = False

        return df

    # =========================================================================
    # MASTER CLEAN FUNCTION
    # =========================================================================
    def clean_and_map(
        self,
        df: pd.DataFrame,
        critical_columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        MASTER FUNCTION: Clean and map a dirty DataFrame.

        Executes all cleaning steps in order:
        1. Map headers to standard names
        2. Sanitize currency and percentages
        3. Normalize dates
        4. Normalize asset classes
        5. Handle nulls
        6. Detect short positions

        Args:
            df: Raw DataFrame from CSV/Excel
            critical_columns: Columns that must have values (rows dropped if missing)

        Returns:
            Tuple of (cleaned DataFrame, processing log)
        """
        self.clear_log()
        self.log("🚀 Starting data processing...")
        self.log(f"📊 Input: {len(df)} rows, {len(df.columns)} columns")

        # Step 0: Skip junk header rows (Schwab, Fidelity, Pershing reports)
        df = self.skip_junk_rows(df)

        # Step 1: Map headers
        df = self.map_headers(df)

        # Step 2: Sanitize numeric columns
        df = self.sanitize_numeric_columns(df)

        # Step 3: Normalize dates
        df = self.normalize_date_columns(df)

        # Step 4: Normalize asset classes
        df = self.normalize_asset_class_column(df)

        # Step 5: Handle nulls
        df = self.handle_nulls(df, drop_if_missing=critical_columns)

        # Step 6: Detect short positions
        df = self.detect_short_positions(df)

        self.log(f"✅ Processing complete: {len(df)} rows, {len(df.columns)} columns")

        return df, self.get_log()

    # =========================================================================
    # FILE LOADING UTILITIES
    # =========================================================================
    @staticmethod
    def load_file(file_path: str) -> pd.DataFrame:
        """
        Load CSV or Excel file.

        Auto-detects format based on extension.
        """
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    def process_file(
        self,
        file_path: str,
        critical_columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Load and process a file in one step.
        """
        df = self.load_file(file_path)
        return self.clean_and_map(df, critical_columns)

    # =========================================================================
    # MULTI-SECTION CUSTODIAN EXPORT PARSER
    # =========================================================================

    # =========================================================================
    # UNIVERSAL SNIFFER - KEYWORD CONCEPTS FOR FUZZY SECTION DETECTION
    # Vector's Protocol: 1000% Dynamic - No Hardcoded Strings
    # =========================================================================

    # Concept: POSITIONS - Any line containing these = start of positions section
    POSITIONS_KEYWORDS = [
        'positions', 'holdings', 'assets', 'investment detail', 'current value',
        'portfolio holdings', 'account positions', 'securities held', 'position detail',
        'investment holdings', 'my holdings', 'stock positions', 'equity holdings',
        'fixed income holdings', 'bond positions', 'fund holdings', 'etf holdings'
    ]

    # Concept: TRANSACTIONS - Any line containing these = start of transactions section
    TRANSACTIONS_KEYWORDS = [
        'transaction', 'activity', 'history', 'ledger', 'journal', 'trade',
        'buy/sell', 'purchases', 'sales', 'transfers', 'activity detail',
        'account activity', 'trade history', 'order history', 'transaction detail'
    ]

    # Concept: VALUATIONS - Any line containing these = start of valuations section
    VALUATIONS_KEYWORDS = [
        'valuation', 'performance', 'monthly', 'quarterly', 'return', 'value history',
        'account value', 'portfolio value', 'market value history', 'nav history',
        'period return', 'time-weighted', 'twrr', 'performance data'
    ]

    # Valid POSITION header must contain at least one from each group
    POSITION_HEADER_GROUP_A = ['symbol', 'ticker', 'cusip', 'security', 'name', 'description']
    POSITION_HEADER_GROUP_B = ['quantity', 'shares', 'units', 'value', 'market', 'price', 'cost']

    # Valid TRANSACTION header must contain at least one from each group
    TRANSACTION_HEADER_GROUP_A = ['date', 'trade date', 'settle', 'settlement']
    TRANSACTION_HEADER_GROUP_B = ['action', 'type', 'activity', 'transaction', 'buy', 'sell', 'amount']

    # Valid VALUATION header must contain at least one from each group
    VALUATION_HEADER_GROUP_A = ['date', 'period', 'month', 'quarter', 'year']
    VALUATION_HEADER_GROUP_B = ['value', 'return', 'balance', 'nav', 'total', 'portfolio']

    def _detect_section_concept(self, line: str, is_collecting_data: bool = False) -> Optional[str]:
        """
        UNIVERSAL SNIFFER: Detect section concept using fuzzy keyword matching.
        Returns: 'positions', 'transactions', 'valuations', or None

        DYNAMIC FIX: When already collecting data (is_collecting_data=True), only detect
        section changes from EXPLICIT section markers (=== SECTION ===, --- SECTION ---, etc.)
        NOT from keywords that happen to appear in data values.
        """
        line_lower = line.lower()
        line_stripped = line.strip()

        # CRITICAL: HARD STOP - Never treat SUMMARY lines as new sections
        # "POSITION SUMMARY:" should STOP reading, not start a new section
        if 'summary' in line_lower:
            return None

        # SMART DETECTION: If we're already collecting data, only switch sections
        # if this line looks like an EXPLICIT section marker, not just contains a keyword
        if is_collecting_data:
            # Only detect section change from explicit markers like:
            # === TRANSACTIONS ===, --- VALUATIONS ---, [POSITIONS], etc.
            is_section_marker = (
                (line_stripped.startswith('===') and line_stripped.endswith('===')) or
                (line_stripped.startswith('---') and line_stripped.endswith('---')) or
                (line_stripped.startswith('[') and line_stripped.endswith(']')) or
                (line_stripped.startswith('###')) or
                (line_stripped.startswith('***')) or
                # Also check for standalone section titles (short lines with keywords, no commas)
                (len(line_stripped) < 50 and ',' not in line_stripped and any(
                    kw in line_lower for kw in ['position', 'transaction', 'valuation', 'holdings', 'activity', 'history']
                ))
            )
            if not is_section_marker:
                return None  # Don't switch sections - this is just data with a keyword

        # Check for positions concept
        for kw in self.POSITIONS_KEYWORDS:
            if kw in line_lower:
                return 'positions'

        # Check for transactions concept
        for kw in self.TRANSACTIONS_KEYWORDS:
            if kw in line_lower:
                return 'transactions'

        # Check for valuations concept
        for kw in self.VALUATIONS_KEYWORDS:
            if kw in line_lower:
                return 'valuations'

        return None

    def _is_valid_header_row(self, line: str, section_type: str) -> bool:
        """
        HEADER HUNTER: Validate if a line is a valid CSV header for the section type.
        Must contain at least one keyword from each required group.
        """
        line_lower = line.lower()

        if section_type == 'positions':
            has_group_a = any(kw in line_lower for kw in self.POSITION_HEADER_GROUP_A)
            has_group_b = any(kw in line_lower for kw in self.POSITION_HEADER_GROUP_B)
            return has_group_a and has_group_b

        elif section_type == 'transactions':
            has_group_a = any(kw in line_lower for kw in self.TRANSACTION_HEADER_GROUP_A)
            has_group_b = any(kw in line_lower for kw in self.TRANSACTION_HEADER_GROUP_B)
            return has_group_a and has_group_b

        elif section_type == 'valuations':
            has_group_a = any(kw in line_lower for kw in self.VALUATION_HEADER_GROUP_A)
            has_group_b = any(kw in line_lower for kw in self.VALUATION_HEADER_GROUP_B)
            return has_group_a and has_group_b

        return False

    def _is_data_row(self, line: str) -> bool:
        """Check if line looks like a data row (has commas, not a section marker)."""
        if not line or not line.strip():
            return False
        if line.strip().startswith('===') or line.strip().startswith('---'):
            return False
        if line.strip().startswith('#'):
            return False
        # Must have at least one comma to be CSV data
        return ',' in line

    def parse_custodian_export(self, file_content: str) -> Dict[str, pd.DataFrame]:
        """
        UNIVERSAL SNIFFER: Parse ANY multi-section custodian export file.

        Uses SEMANTIC DETECTION instead of hardcoded strings.
        Works with Schwab, Fidelity, Pershing, TD Ameritrade, or ANY custodian format.

        Detection Logic:
        1. Scan each line for CONCEPT keywords (positions, transactions, valuations)
        2. When concept detected, HUNT for valid header row in next 5 lines
        3. Collect all data rows until next section or end of file

        Args:
            file_content: Raw file content as string

        Returns:
            Dictionary with parsed DataFrames:
            {
                'positions': DataFrame of current holdings,
                'transactions': DataFrame of trade history,
                'valuations': DataFrame of monthly values,
                'metadata': Dict of account info
            }
        """
        from io import StringIO

        self.clear_log()
        self.log("🏦 UNIVERSAL SNIFFER: Parsing custodian export...")

        lines = file_content.strip().split('\n')

        # Track sections with their data
        sections = {
            'positions': [],
            'transactions': [],
            'valuations': [],
        }

        metadata = {}
        current_section = None
        header_found = False
        header_line_content = None

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped:
                continue

            # Skip obvious non-data lines
            if line_stripped.startswith('=') and '=' * 5 in line_stripped:
                continue

            # Extract metadata from header lines (key: value format)
            if ':' in line_stripped and current_section is None:
                parts = line_stripped.split(':', 1)
                if len(parts) == 2 and len(parts[0]) < 30:  # Reasonable key length
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and not any(c in key for c in ['$', '%', ',']):
                        metadata[key] = value

            # UNIVERSAL SNIFFER: Detect section concept
            # DYNAMIC FIX: If we're already in a section (even if header not found yet),
            # we need stricter section detection to avoid false positives from data keywords
            detected_concept = self._detect_section_concept(line_stripped, is_collecting_data=(current_section is not None))

            if detected_concept and detected_concept != current_section:
                # New section detected! Log it
                self.log(f"📍 SNIFFER detected '{detected_concept.upper()}' concept at line {i+1}: {line_stripped[:50]}...")
                current_section = detected_concept
                header_found = False
                header_line_content = None

                # HEADER HUNTING: Check if this line IS the header
                if self._is_valid_header_row(line_stripped, current_section):
                    header_found = True
                    header_line_content = line_stripped
                    sections[current_section].append(line_stripped)
                    self.log(f"   ✓ Header found on same line")
                continue

            # If we're in a section but haven't found header yet, hunt for it
            if current_section and not header_found:
                if self._is_valid_header_row(line_stripped, current_section):
                    header_found = True
                    header_line_content = line_stripped
                    sections[current_section].append(line_stripped)
                    self.log(f"   ✓ Header hunted at line {i+1}")
                continue

            # If we have a section and header, collect data rows
            if current_section and header_found:
                # Check if this line starts a NEW section
                # DYNAMIC FIX: Pass is_collecting_data=True to prevent false positives
                # from keywords appearing in data values (e.g., "Portfolio Valuation" in transaction description)
                new_concept = self._detect_section_concept(line_stripped, is_collecting_data=True)
                if new_concept and new_concept != current_section:
                    # Section change - will be handled in next iteration
                    self.log(f"📍 SNIFFER detected '{new_concept.upper()}' concept at line {i+1}")
                    current_section = new_concept
                    header_found = False
                    header_line_content = None
                    if self._is_valid_header_row(line_stripped, current_section):
                        header_found = True
                        header_line_content = line_stripped
                        sections[current_section].append(line_stripped)
                        self.log(f"   ✓ Header found on same line")
                    continue

                # Check for end markers
                if 'END OF REPORT' in line_stripped.upper() or 'SUMMARY' in line_stripped.upper():
                    if 'POSITION SUMMARY' in line_stripped.upper() or 'ACCOUNT SUMMARY' in line_stripped.upper():
                        current_section = None
                        header_found = False
                        continue

                # Collect data row
                if self._is_data_row(line_stripped):
                    sections[current_section].append(line_stripped)

        # Log section detection stats
        self.log(f"📊 SNIFFER RESULTS:")
        self.log(f"   - Positions: {len(sections['positions'])} lines collected")
        self.log(f"   - Transactions: {len(sections['transactions'])} lines collected")
        self.log(f"   - Valuations: {len(sections['valuations'])} lines collected")
        self.log(f"   - Metadata: {len(metadata)} fields extracted")

        # Parse each section into DataFrame
        result = {'metadata': metadata}

        # Parse Positions
        if sections['positions']:
            pos_content = '\n'.join(sections['positions'])
            try:
                pos_df = pd.read_csv(StringIO(pos_content))
                pos_df, _ = self.clean_and_map(pos_df)
                result['positions'] = pos_df
                self.log(f"✅ Parsed {len(pos_df)} positions")
            except Exception as e:
                self.log(f"⚠️ Error parsing positions: {str(e)}")
                result['positions'] = pd.DataFrame()

        # Parse Transactions
        if sections['transactions']:
            txn_content = '\n'.join(sections['transactions'])
            try:
                txn_df = pd.read_csv(StringIO(txn_content))
                txn_df = self.map_headers(txn_df)
                txn_df = self.sanitize_numeric_columns(txn_df)
                result['transactions'] = txn_df
                self.log(f"✅ Parsed {len(txn_df)} transactions")
            except Exception as e:
                self.log(f"⚠️ Error parsing transactions: {str(e)}")
                result['transactions'] = pd.DataFrame()

        # Parse Valuations (Monthly Performance)
        if sections['valuations']:
            val_content = '\n'.join(sections['valuations'])
            try:
                # VECTOR'S FIX: Handle currency values with commas like $208,168,686.62
                # These get split incorrectly by CSV parser
                # Solution: Remove commas from within dollar amounts BEFORE parsing
                import re
                # Match dollar amounts with commas: $123,456,789.00
                def fix_currency(line):
                    # Find all $xxx,xxx,xxx patterns and remove internal commas
                    return re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)',
                                  lambda m: '$' + m.group(1).replace(',', ''), line)

                fixed_lines = [fix_currency(line) for line in val_content.split('\n')]
                val_content_fixed = '\n'.join(fixed_lines)
                self.log(f"📊 Pre-processed valuations to handle currency commas")

                val_df = pd.read_csv(StringIO(val_content_fixed))
                val_df = self.map_headers(val_df)
                val_df = self.sanitize_numeric_columns(val_df)
                result['valuations'] = val_df
                self.log(f"✅ Parsed {len(val_df)} valuation periods")
            except Exception as e:
                self.log(f"⚠️ Error parsing valuations: {str(e)}")
                result['valuations'] = pd.DataFrame()

        result['log'] = self.get_log()
        return result

    def extract_returns_from_valuations(self, valuations_df: pd.DataFrame) -> List[float]:
        """
        Extract portfolio returns from monthly valuations DataFrame.

        DYNAMIC: Handles ANY column naming convention from ANY custodian.

        Args:
            valuations_df: DataFrame with return column (any naming convention)

        Returns:
            List of decimal returns (e.g., 0.02 for 2%)
        """
        returns = []

        # Find the return column - DYNAMIC detection for ANY naming convention
        return_col = None
        return_keywords = ['return', 'ret', 'perf', 'performance', 'gain', 'pnl', 'p&l', 'profit']

        # Priority 1: Exact match for common names
        exact_matches = ['return', 'returns', 'return %', 'return%', 'portfolio return',
                         'monthly return', 'period return', 'twrr', 'twr']
        for col in valuations_df.columns:
            col_lower = col.lower().strip()
            if col_lower in exact_matches:
                return_col = col
                self.log(f"📊 Found return column (exact): '{col}'")
                break

        # Priority 2: Column contains 'return' keyword
        if return_col is None:
            for col in valuations_df.columns:
                col_lower = col.lower()
                if 'return' in col_lower:
                    return_col = col
                    self.log(f"📊 Found return column (keyword): '{col}'")
                    break

        # Priority 3: Any return-related keyword
        if return_col is None:
            for col in valuations_df.columns:
                col_lower = col.lower()
                for kw in return_keywords:
                    if kw in col_lower:
                        return_col = col
                        self.log(f"📊 Found return column (fuzzy): '{col}'")
                        break
                if return_col:
                    break

        if return_col is None:
            self.log(f"⚠️ Could not find return column. Available: {list(valuations_df.columns)}")
            return returns

        for val in valuations_df[return_col]:
            if pd.isna(val):
                continue
            # Convert percentage string to decimal
            if isinstance(val, str):
                val = val.replace('%', '').replace(' ', '').strip()
                try:
                    val = float(val) / 100  # Convert 2.5% to 0.025
                except ValueError:
                    continue
            else:
                val = float(val) / 100 if abs(val) > 1 else float(val)
            returns.append(val)

        self.log(f"📈 Extracted {len(returns)} return periods")
        return returns

    def calculate_modified_dietz_returns(
        self,
        transactions_df: pd.DataFrame,
        valuations_df: pd.DataFrame
    ) -> List[float]:
        """
        Calculate monthly returns using Modified Dietz method.

        Modified Dietz Formula:
        R = (EMV - BMV - CF) / (BMV + Sum(CF_i * W_i))

        Where:
        - EMV = Ending Market Value
        - BMV = Beginning Market Value
        - CF = Cash Flows (contributions/withdrawals ONLY - NOT market appreciation)
        - W_i = Weight of each cash flow (days remaining / total days)

        VECTOR'S FIX: NetFlows must ONLY include deposits/withdrawals, NOT trade activity
        or market appreciation. If the data mixes them, we detect and correct.

        Args:
            transactions_df: DataFrame of transactions
            valuations_df: DataFrame of monthly valuations

        Returns:
            List of monthly returns as decimals
        """
        returns = []

        # =====================================================================
        # MANDATORY: ALWAYS CALCULATE MODIFIED DIETZ - NEVER USE PRE-CALCULATED
        # =====================================================================
        # We NEVER trust custodian-provided returns because:
        # 1. Unknown methodology (could be simple return, not TWR)
        # 2. Cannot verify correctness
        # 3. GIPS requires documented, consistent methodology
        # 4. Fiduciary liability - we must prove our calculations
        #
        # Even if "Portfolio Return %" column exists, we IGNORE it and
        # calculate Modified Dietz ourselves from valuations + cash flows
        # =====================================================================
        self.log("📊 MODIFIED DIETZ: Calculating TWR from valuations (NEVER using pre-calculated returns)")

        # Find value column - DYNAMIC detection
        value_col = None
        value_keywords = ['market', 'value', 'nav', 'portfolio', 'balance', 'total', 'amount', 'worth']

        for col in valuations_df.columns:
            col_lower = col.lower()
            # Skip return/flow columns - we want value columns
            if 'return' in col_lower or 'flow' in col_lower or 'net' in col_lower:
                continue
            for kw in value_keywords:
                if kw in col_lower:
                    value_col = col
                    self.log(f"📊 Found value column: '{col}'")
                    break
            if value_col:
                break

        if value_col is None:
            self.log(f"⚠️ Could not find value column. Available: {list(valuations_df.columns)}")
            return returns

        # Find net flows column - DYNAMIC detection
        # CRITICAL: We ONLY want actual cash deposits/withdrawals, NOT market changes
        flows_col = None
        # Priority order: contribution/withdrawal first, then generic flow
        contribution_keywords = ['contribution', 'withdrawal', 'deposit', 'redemption', 'transfer', 'external']
        generic_flow_keywords = ['flow', 'net']

        # First pass: Look for contribution/withdrawal columns (more specific)
        for col in valuations_df.columns:
            col_lower = col.lower()
            for kw in contribution_keywords:
                if kw in col_lower:
                    flows_col = col
                    self.log(f"📊 Found EXTERNAL flows column: '{col}'")
                    break
            if flows_col:
                break

        # Second pass: Generic flow column (might include market changes - will validate)
        if flows_col is None:
            for col in valuations_df.columns:
                col_lower = col.lower()
                for kw in generic_flow_keywords:
                    if kw in col_lower:
                        flows_col = col
                        self.log(f"⚠️ Found generic flows column: '{col}' - will validate")
                        break
                if flows_col:
                    break

        values = []
        for val in valuations_df[value_col]:
            if pd.isna(val):
                values.append(0)
            elif isinstance(val, str):
                val = self.sanitize_currency(val)
                values.append(val if val else 0)
            else:
                values.append(float(val))

        flows = []
        if flows_col:
            for val in valuations_df[flows_col]:
                if pd.isna(val):
                    flows.append(0)
                elif isinstance(val, str):
                    val = self.sanitize_currency(val)
                    flows.append(val if val else 0)
                else:
                    flows.append(float(val))

            # VECTOR'S FIX: Detect if "flows" are actually market appreciation
            # If flows approximately equal (EMV - BMV), they're market changes, not cash flows
            suspect_market_flows = 0
            for i in range(1, min(5, len(values))):  # Check first few periods
                expected_market_change = values[i] - values[i-1]
                actual_flow = flows[i] if i < len(flows) else 0
                if abs(actual_flow) > 0 and abs(expected_market_change) > 0:
                    ratio = actual_flow / expected_market_change if expected_market_change != 0 else 0
                    if 0.8 < ratio < 1.2:  # Flow is ~same as value change
                        suspect_market_flows += 1

            if suspect_market_flows >= 2:
                self.log(f"⚠️ DETECTED: 'Net Flows' appear to include market appreciation. Setting flows to ZERO.")
                flows = [0] * len(values)

            # =============================================================
            # CRITICAL #3: CASH FLOW SIGN CONVENTION VALIDATION
            # =============================================================
            # GIPS/Industry Standard:
            #   - CONTRIBUTIONS (money IN)  = POSITIVE (+)
            #   - WITHDRAWALS (money OUT)   = NEGATIVE (-)
            #
            # Modified Dietz Formula expects this convention:
            #   R = (EMV - BMV - CF) / (BMV + CF × W)
            #
            # If signs are REVERSED, returns will be COMPLETELY WRONG!
            #
            # VALIDATION LOGIC:
            # If CF is POSITIVE (contribution), then:
            #   - Some of EMV increase should come from the deposit
            #   - So: (EMV - BMV) should be GREATER than market return alone
            #   - Simplified: EMV should be >= BMV + (CF * 0.3) even with losses
            #
            # If CF is NEGATIVE (withdrawal), then:
            #   - EMV should be LESS than BMV (money was taken out)
            #   - Even with gains, EMV should be < BMV + some_gain
            # =============================================================
            if len(flows) > 3 and any(f != 0 for f in flows):
                self.log("📊 VALIDATING: Cash flow sign convention...")

                sign_correct_count = 0
                sign_wrong_count = 0

                for i in range(1, len(values)):
                    if i >= len(flows):
                        break
                    cf = flows[i]
                    if abs(cf) < 1000:  # Skip tiny flows (less than $1000)
                        continue

                    bmv = values[i-1]
                    emv = values[i]

                    if bmv <= 0:
                        continue

                    # Calculate what % of BMV the cash flow represents
                    cf_pct = cf / bmv

                    # Calculate the actual value change
                    value_change_pct = (emv - bmv) / bmv

                    # LOGIC:
                    # If CF is positive (contribution), value should increase
                    # more than a typical market return (say 2% monthly max)
                    # If CF is positive but value decreased significantly,
                    # or increased by less than half the CF, something is wrong

                    if cf > 0:  # Supposed contribution
                        # Contribution should add to value
                        # If EMV < BMV + CF*0.3, the "contribution" didn't add value
                        # This could mean it's actually a withdrawal coded wrong
                        expected_min_emv = bmv + (cf * 0.3)  # Allow 70% market loss
                        if emv >= expected_min_emv:
                            sign_correct_count += 1
                        else:
                            sign_wrong_count += 1
                            self.log(f"   ⚠️ Period {i}: +${cf:,.0f} flow but EMV (${emv:,.0f}) < expected (${expected_min_emv:,.0f})")

                    elif cf < 0:  # Supposed withdrawal
                        # Withdrawal should reduce value
                        # If EMV > BMV + |CF|*0.5, the "withdrawal" added value
                        # This could mean it's actually a contribution coded wrong
                        expected_max_emv = bmv + abs(cf) * 0.5  # Allow 50% apparent gain
                        if emv <= expected_max_emv:
                            sign_correct_count += 1
                        else:
                            sign_wrong_count += 1
                            self.log(f"   ⚠️ Period {i}: -${abs(cf):,.0f} flow but EMV (${emv:,.0f}) > expected (${expected_max_emv:,.0f})")

                self.log(f"   Sign check results: {sign_correct_count} correct, {sign_wrong_count} suspicious")

                if sign_wrong_count > sign_correct_count and sign_wrong_count >= 2:
                    self.log(f"🚨 WARNING: Cash flow signs may be INVERTED!")
                    self.log(f"   Expected: Contributions=POSITIVE, Withdrawals=NEGATIVE")
                    self.log(f"   Your data shows opposite pattern - verify with custodian")
                elif sign_wrong_count > 0:
                    self.log(f"⚠️ CAUTION: {sign_wrong_count} period(s) have unusual cash flow patterns")
                    self.log(f"   This may indicate data quality issues or sign convention problems")
                else:
                    self.log(f"✅ Cash flow sign convention appears CORRECT (Contributions=+, Withdrawals=-)")
        else:
            flows = [0] * len(values)
            self.log(f"⚠️ No cash flow column found - using zero flows (simple return)")

        # =================================================================
        # LARGE CASH FLOW DETECTION (GIPS REQUIREMENT)
        # =================================================================
        # GIPS 2020 Standard 2.A.4: Portfolios must be revalued on the
        # date of all large external cash flows. Large = >10% of BMV.
        #
        # When detected, we FLAG it but still calculate (we don't have
        # intra-period valuations to split the period).
        # =================================================================
        large_flow_warnings = []
        LARGE_FLOW_THRESHOLD = 0.10  # 10% of portfolio value

        # Calculate Modified Dietz for each period
        for i in range(1, len(values)):
            bmv = values[i-1]
            emv = values[i]
            cf = flows[i] if i < len(flows) else 0

            if bmv <= 0:
                returns.append(0)
                continue

            # =============================================================
            # CRITICAL: LARGE CASH FLOW CHECK (>10% of BMV)
            # =============================================================
            if bmv > 0 and abs(cf) > 0:
                cf_pct = abs(cf) / bmv
                if cf_pct > LARGE_FLOW_THRESHOLD:
                    warning = f"⚠️ LARGE CASH FLOW Period {i}: ${cf:,.0f} = {cf_pct*100:.1f}% of BMV (>${LARGE_FLOW_THRESHOLD*100:.0f}% threshold)"
                    large_flow_warnings.append(warning)
                    self.log(warning)
                    self.log(f"   → GIPS requires revaluation on date of large flows")
                    self.log(f"   → Modified Dietz approximation may be less accurate for this period")

            # =============================================================
            # MODIFIED DIETZ FORMULA (GIPS-Compliant)
            # =============================================================
            # R = (EMV - BMV - CF) / (BMV + Σ(CFᵢ × Wᵢ))
            #
            # Where:
            #   EMV = Ending Market Value
            #   BMV = Beginning Market Value
            #   CF  = Total Cash Flows (contributions +, withdrawals -)
            #   Wᵢ  = Weight = (Days Remaining) / (Total Days)
            #
            # SIMPLIFIED VERSION (used when exact dates unknown):
            #   Assume all cash flows occur mid-period → W = 0.5
            #   R = (EMV - BMV - CF) / (BMV + CF × 0.5)
            # =============================================================
            weighted_bmv = bmv + (cf * 0.5)  # Mid-period assumption

            if weighted_bmv <= 0:
                returns.append(0)
                continue

            r = (emv - bmv - cf) / weighted_bmv
            returns.append(r)

            self.log(f"   Period {i}: BMV=${bmv:,.0f} → EMV=${emv:,.0f}, CF=${cf:,.0f}, Return={r*100:.2f}%")

        # Report large flow summary
        if large_flow_warnings:
            self.log(f"🚨 GIPS ALERT: {len(large_flow_warnings)} periods had large cash flows (>10%)")
            self.log(f"   For GIPS compliance, these periods should be sub-divided with intra-period valuations")

        self.log(f"📊 Calculated {len(returns)} Modified Dietz returns")

        # Sanity check: If returns are all near-zero, something is wrong
        avg_abs_return = np.mean([abs(r) for r in returns]) if returns else 0
        if avg_abs_return < 0.001:  # Less than 0.1% average absolute return
            self.log(f"⚠️ WARNING: Returns appear artificially flat (avg abs: {avg_abs_return:.4f})")
            self.log(f"   This may indicate Net Flows incorrectly subtract market appreciation")

        return returns


# =============================================================================
# STREAMLIT UI INTEGRATION
# =============================================================================

def render_data_processor_page():
    """Render Data Processor page in Streamlit."""
    import streamlit as st

    st.markdown("# 🧹 Data Processor")
    st.markdown("*Clean and standardize messy RIA CSV/Excel files*")

    st.divider()

    # File Upload
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx", "xls"]
    )

    if uploaded_file:
        # Load file
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        st.markdown("### 📄 Raw Data Preview")
        st.dataframe(raw_df.head(10))

        st.divider()

        # Process button
        if st.button("🧹 Clean & Standardize", type="primary"):
            processor = DataProcessor()
            cleaned_df, log = processor.clean_and_map(raw_df)

            # Show log
            st.markdown("### 📋 Processing Log")
            for entry in log:
                st.text(entry)

            st.divider()

            # Show cleaned data
            st.markdown("### ✅ Cleaned Data")
            st.dataframe(cleaned_df.head(20))

            # Download button
            csv = cleaned_df.to_csv(index=False)
            st.download_button(
                "📥 Download Cleaned CSV",
                csv,
                "cleaned_data.csv",
                "text/csv"
            )


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Test with sample messy data
    test_data = {
        'Ticker': ['AAPL', 'GOOGL', 'MSFT', 'AMZN'],
        'Mkt Val': ['$10,500.00', '$8,200.50', '($2,000.00)', '$15K'],
        'Return %': ['5.4%', '-2.1%', '+3.5%', '10%'],
        'Trade Date': ['01/15/2025', '2025-01-16', 'Jan 17, 2025', '18/01/2025'],
        'Asset Type': ['US Stocks', 'Domestic Equity', 'equities', 'stock'],
        'Qty': ['100', '-50', '200', '75']
    }

    df = pd.DataFrame(test_data)
    print("=== RAW DATA ===")
    print(df)
    print()

    processor = DataProcessor()
    cleaned, log = processor.clean_and_map(df)

    print("=== PROCESSING LOG ===")
    for entry in log:
        print(entry)
    print()

    print("=== CLEANED DATA ===")
    print(cleaned)
    print()
    print(cleaned.dtypes)
