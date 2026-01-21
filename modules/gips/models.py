"""
GIPS Data Models
================
Core data structures for GIPS compliance.

Hierarchy:
    Firm → Composite → Account → Household (optional)

Each level has specific GIPS requirements and calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Optional, Any
import json


class TransactionType(Enum):
    """Transaction types for cash flow tracking."""
    BUY = "Buy"
    SELL = "Sell"
    DIVIDEND = "Div"
    INTEREST = "Int"
    FEE = "Fee"
    CONTRIBUTION = "Contribution"  # Cash in
    WITHDRAWAL = "Withdrawal"      # Cash out
    TRANSFER_IN = "Transfer In"
    TRANSFER_OUT = "Transfer Out"
    JOURNAL = "Journ"              # Internal transfer
    END_VALUE = "End Value"        # Period end valuation

    @classmethod
    def from_string(cls, s: str) -> 'TransactionType':
        """Convert string to TransactionType with fuzzy matching."""
        s_upper = s.upper().strip()
        mapping = {
            'BUY': cls.BUY,
            'SELL': cls.SELL,
            'DIV': cls.DIVIDEND,
            'DIVIDEND': cls.DIVIDEND,
            'INT': cls.INTEREST,
            'INTEREST': cls.INTEREST,
            'FEE': cls.FEE,
            'FEES': cls.FEE,
            'CONTRIBUTION': cls.CONTRIBUTION,
            'DEPOSIT': cls.CONTRIBUTION,
            'WITHDRAWAL': cls.WITHDRAWAL,
            'WITHDRAW': cls.WITHDRAWAL,
            'TRANSFER IN': cls.TRANSFER_IN,
            'TRANSFER OUT': cls.TRANSFER_OUT,
            'JOURN': cls.JOURNAL,
            'JOURNAL': cls.JOURNAL,
            'END VALUE': cls.END_VALUE,
            'ENDVALUE': cls.END_VALUE,
        }
        return mapping.get(s_upper, cls.BUY)  # Default to BUY if unknown


class CompositeType(Enum):
    """Types of investment composites."""
    EQUITY_GROWTH = "Equity Growth"
    EQUITY_VALUE = "Equity Value"
    EQUITY_BLEND = "Equity Blend"
    FIXED_INCOME = "Fixed Income"
    BALANCED = "Balanced"
    ALTERNATIVE = "Alternative"
    CUSTOM = "Custom"


@dataclass
class Transaction:
    """
    Individual transaction record.

    GIPS requires tracking external cash flows for accurate TWR calculation.
    External flows = Contributions + Withdrawals (not Buy/Sell which are internal)
    """
    date: date
    transaction_type: TransactionType
    symbol: Optional[str]
    description: str
    quantity: Decimal
    price: Decimal
    amount: Decimal  # Net amount (positive = inflow, negative = outflow)
    fees: Decimal = Decimal('0')
    account_id: str = ""

    @property
    def is_external_flow(self) -> bool:
        """Is this an external cash flow (affects TWR calculation)?"""
        return self.transaction_type in [
            TransactionType.CONTRIBUTION,
            TransactionType.WITHDRAWAL,
            TransactionType.TRANSFER_IN,
            TransactionType.TRANSFER_OUT,
        ]

    @property
    def net_external_flow(self) -> Decimal:
        """Net external flow amount (+ = inflow, - = outflow)."""
        if not self.is_external_flow:
            return Decimal('0')
        if self.transaction_type in [TransactionType.CONTRIBUTION, TransactionType.TRANSFER_IN]:
            return abs(self.amount)
        else:
            return -abs(self.amount)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'type': self.transaction_type.value,
            'symbol': self.symbol,
            'description': self.description,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'amount': float(self.amount),
            'fees': float(self.fees),
            'account_id': self.account_id,
        }


@dataclass
class Valuation:
    """
    Portfolio valuation at a point in time.

    GIPS requires valuations at least monthly (daily preferred).
    Must be fair value, not cost basis.
    """
    date: date
    market_value: Decimal
    accrued_income: Decimal = Decimal('0')  # Accrued interest/dividends
    account_id: str = ""

    @property
    def total_value(self) -> Decimal:
        """Total portfolio value including accrued income."""
        return self.market_value + self.accrued_income

    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'market_value': float(self.market_value),
            'accrued_income': float(self.accrued_income),
            'total_value': float(self.total_value),
            'account_id': self.account_id,
        }


@dataclass
class PerformanceReturn:
    """
    Calculated performance return for a period.

    GIPS requires:
    - Monthly returns (minimum)
    - Gross and net of fees
    - Geometric linking for longer periods
    """
    period_start: date
    period_end: date
    gross_return: Decimal          # Before fees
    net_return: Decimal            # After fees
    beginning_value: Decimal
    ending_value: Decimal
    net_external_flows: Decimal    # Sum of contributions - withdrawals
    fees_charged: Decimal = Decimal('0')
    account_id: str = ""

    @property
    def period_days(self) -> int:
        """Number of days in the period."""
        return (self.period_end - self.period_start).days

    @property
    def is_monthly(self) -> bool:
        """Is this a monthly return?"""
        return 28 <= self.period_days <= 31

    @property
    def is_quarterly(self) -> bool:
        """Is this a quarterly return?"""
        return 89 <= self.period_days <= 92

    @property
    def is_annual(self) -> bool:
        """Is this an annual return?"""
        return 365 <= self.period_days <= 366

    def to_dict(self) -> Dict[str, Any]:
        return {
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'gross_return': float(self.gross_return),
            'net_return': float(self.net_return),
            'gross_return_pct': float(self.gross_return * 100),
            'net_return_pct': float(self.net_return * 100),
            'beginning_value': float(self.beginning_value),
            'ending_value': float(self.ending_value),
            'net_external_flows': float(self.net_external_flows),
            'fees_charged': float(self.fees_charged),
            'period_days': self.period_days,
            'account_id': self.account_id,
        }


@dataclass
class Account:
    """
    Individual investment account.

    GIPS requires:
    - All fee-paying discretionary accounts must be in at least one composite
    - Non-discretionary accounts excluded from composites
    - Account must be in composite for full measurement period
    """
    account_id: str
    account_name: str
    inception_date: date
    is_discretionary: bool = True   # Can we make investment decisions?
    is_fee_paying: bool = True      # Does client pay fees?
    is_active: bool = True
    benchmark_id: Optional[str] = None
    household_id: Optional[str] = None

    # Calculated fields (populated during analysis)
    transactions: List[Transaction] = field(default_factory=list)
    valuations: List[Valuation] = field(default_factory=list)
    returns: List[PerformanceReturn] = field(default_factory=list)

    # Account metadata
    client_name: Optional[str] = None
    strategy: Optional[str] = None
    risk_profile: Optional[str] = None

    @property
    def latest_valuation(self) -> Optional[Valuation]:
        """Most recent portfolio valuation."""
        if not self.valuations:
            return None
        return max(self.valuations, key=lambda v: v.date)

    @property
    def total_market_value(self) -> Decimal:
        """Current market value."""
        latest = self.latest_valuation
        return latest.total_value if latest else Decimal('0')

    @property
    def total_fees(self) -> Decimal:
        """Total fees from transactions."""
        return sum(t.fees for t in self.transactions)

    def get_returns_for_period(self, start: date, end: date) -> List[PerformanceReturn]:
        """Get returns within a date range."""
        return [r for r in self.returns
                if r.period_start >= start and r.period_end <= end]

    def get_annualized_return(self, years: int = 3) -> Optional[Decimal]:
        """
        Calculate annualized return over N years.

        GIPS requires 3-year annualized return using geometric linking.
        """
        if not self.returns:
            return None

        # Get last N years of monthly returns
        cutoff = date.today().replace(year=date.today().year - years)
        period_returns = [r for r in self.returns if r.period_start >= cutoff]

        if len(period_returns) < 12:  # Need at least 1 year of data
            return None

        # Geometric linking: (1+r1) * (1+r2) * ... * (1+rn) - 1
        cumulative = Decimal('1')
        for r in period_returns:
            cumulative *= (Decimal('1') + r.net_return)

        # Annualize: (cumulative) ^ (12/n) - 1
        months = len(period_returns)
        annualized = cumulative ** (Decimal('12') / Decimal(str(months))) - Decimal('1')

        return annualized

    def to_dict(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'inception_date': self.inception_date.isoformat(),
            'is_discretionary': self.is_discretionary,
            'is_fee_paying': self.is_fee_paying,
            'is_active': self.is_active,
            'benchmark_id': self.benchmark_id,
            'household_id': self.household_id,
            'market_value': float(self.total_market_value),
            'client_name': self.client_name,
            'strategy': self.strategy,
            'num_transactions': len(self.transactions),
            'num_valuations': len(self.valuations),
            'num_returns': len(self.returns),
        }


@dataclass
class Household:
    """
    Multi-account household aggregation.

    For GIPS:
    - Household can be treated as single account for composite inclusion
    - Returns are asset-weighted across accounts
    - Useful for families with multiple accounts
    """
    household_id: str
    household_name: str
    accounts: List[Account] = field(default_factory=list)
    primary_contact: Optional[str] = None

    @property
    def total_market_value(self) -> Decimal:
        """Combined market value of all accounts."""
        return sum(a.total_market_value for a in self.accounts)

    @property
    def account_ids(self) -> List[str]:
        """List of account IDs in this household."""
        return [a.account_id for a in self.accounts]

    def get_weighted_return(self, period_start: date, period_end: date) -> Optional[Decimal]:
        """
        Calculate asset-weighted return across all accounts.

        Weight = Account value / Total household value
        Weighted Return = Sum(weight_i * return_i)
        """
        total_value = Decimal('0')
        weighted_return = Decimal('0')

        for account in self.accounts:
            returns = account.get_returns_for_period(period_start, period_end)
            if not returns:
                continue

            # Use beginning value as weight
            account_return = returns[0].net_return
            beginning_value = returns[0].beginning_value

            weighted_return += beginning_value * account_return
            total_value += beginning_value

        if total_value == 0:
            return None

        return weighted_return / total_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'household_id': self.household_id,
            'household_name': self.household_name,
            'primary_contact': self.primary_contact,
            'num_accounts': len(self.accounts),
            'account_ids': self.account_ids,
            'total_market_value': float(self.total_market_value),
        }


@dataclass
class Composite:
    """
    Investment composite (grouping of similar accounts).

    GIPS Requirements:
    - Must include ALL fee-paying discretionary accounts managed to strategy
    - Cannot cherry-pick accounts
    - Must have composite definition document
    - Minimum asset level can be used to exclude small accounts
    """
    composite_id: str
    composite_name: str
    composite_type: CompositeType
    inception_date: date
    description: str

    # Inclusion criteria
    minimum_assets: Decimal = Decimal('0')  # Minimum AUM to include
    strategy_description: str = ""
    benchmark_id: Optional[str] = None
    benchmark_name: Optional[str] = None

    # Member accounts
    accounts: List[Account] = field(default_factory=list)

    # Composite-level returns (asset-weighted)
    returns: List[PerformanceReturn] = field(default_factory=list)

    # GIPS required fields
    is_fee_paying_only: bool = True
    is_discretionary_only: bool = True
    currency: str = "USD"

    @property
    def total_assets(self) -> Decimal:
        """Total AUM across all accounts in composite."""
        return sum(a.total_market_value for a in self.accounts)

    @property
    def num_accounts(self) -> int:
        """Number of accounts in composite."""
        return len(self.accounts)

    @property
    def eligible_accounts(self) -> List[Account]:
        """Accounts that meet composite criteria."""
        eligible = []
        for account in self.accounts:
            if self.is_discretionary_only and not account.is_discretionary:
                continue
            if self.is_fee_paying_only and not account.is_fee_paying:
                continue
            if account.total_market_value < self.minimum_assets:
                continue
            eligible.append(account)
        return eligible

    def add_account(self, account: Account) -> bool:
        """Add account to composite if eligible."""
        if self.is_discretionary_only and not account.is_discretionary:
            return False
        if self.is_fee_paying_only and not account.is_fee_paying:
            return False
        if account.total_market_value < self.minimum_assets:
            return False

        self.accounts.append(account)
        return True

    def get_dispersion(self, year: int) -> Optional[Decimal]:
        """
        Calculate annual return dispersion (standard deviation).

        GIPS requires dispersion when composite has 6+ accounts.
        Uses asset-weighted standard deviation.
        """
        annual_returns = []
        for account in self.eligible_accounts:
            # Get annual return for the year
            for r in account.returns:
                if r.is_annual and r.period_start.year == year:
                    annual_returns.append(float(r.net_return))
                    break

        if len(annual_returns) < 2:
            return None

        # Calculate standard deviation
        mean = sum(annual_returns) / len(annual_returns)
        variance = sum((x - mean) ** 2 for x in annual_returns) / (len(annual_returns) - 1)
        std_dev = variance ** 0.5

        return Decimal(str(std_dev))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'composite_id': self.composite_id,
            'composite_name': self.composite_name,
            'composite_type': self.composite_type.value,
            'inception_date': self.inception_date.isoformat(),
            'description': self.description,
            'minimum_assets': float(self.minimum_assets),
            'benchmark_id': self.benchmark_id,
            'benchmark_name': self.benchmark_name,
            'total_assets': float(self.total_assets),
            'num_accounts': self.num_accounts,
            'currency': self.currency,
        }


@dataclass
class Firm:
    """
    Investment management firm.

    GIPS requires:
    - Firm must be defined as distinct business entity
    - Total firm assets must be disclosed
    - Percentage of firm assets in each composite
    """
    firm_id: str
    firm_name: str
    firm_description: str = ""

    # GIPS required
    total_assets: Decimal = Decimal('0')
    discretionary_assets: Decimal = Decimal('0')

    # Member composites
    composites: List[Composite] = field(default_factory=list)

    # Compliance info
    gips_compliant_since: Optional[date] = None
    verification_date: Optional[date] = None
    verifier_name: Optional[str] = None

    @property
    def num_composites(self) -> int:
        return len(self.composites)

    @property
    def total_composite_assets(self) -> Decimal:
        return sum(c.total_assets for c in self.composites)

    def get_composite(self, composite_id: str) -> Optional[Composite]:
        """Get composite by ID."""
        for c in self.composites:
            if c.composite_id == composite_id:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'firm_id': self.firm_id,
            'firm_name': self.firm_name,
            'firm_description': self.firm_description,
            'total_assets': float(self.total_assets),
            'discretionary_assets': float(self.discretionary_assets),
            'num_composites': self.num_composites,
            'total_composite_assets': float(self.total_composite_assets),
            'gips_compliant_since': self.gips_compliant_since.isoformat() if self.gips_compliant_since else None,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'verifier_name': self.verifier_name,
        }

    def to_json(self) -> str:
        """Serialize firm to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Firm':
        """Deserialize firm from JSON."""
        data = json.loads(json_str)
        return cls(
            firm_id=data['firm_id'],
            firm_name=data['firm_name'],
            firm_description=data.get('firm_description', ''),
            total_assets=Decimal(str(data.get('total_assets', 0))),
            discretionary_assets=Decimal(str(data.get('discretionary_assets', 0))),
            gips_compliant_since=date.fromisoformat(data['gips_compliant_since']) if data.get('gips_compliant_since') else None,
            verification_date=date.fromisoformat(data['verification_date']) if data.get('verification_date') else None,
            verifier_name=data.get('verifier_name'),
        )
