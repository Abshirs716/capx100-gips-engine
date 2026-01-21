"""
GIPS Performance Calculators
============================
Time-Weighted Return (TWR) and composite calculations.

GIPS 2020 Requirements:
- TWR must be used (not MWR/IRR) for composites
- Daily valuation preferred, monthly minimum
- Geometric linking for multi-period returns
- Asset-weighted composite returns
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
import calendar

from .models import (
    Account, Composite, Household, Transaction, Valuation,
    PerformanceReturn, TransactionType
)


@dataclass
class TWRCalculator:
    """
    Time-Weighted Return Calculator.

    TWR eliminates the effect of external cash flows,
    making it the GIPS-required method for comparing managers.

    Formula (Modified Dietz for sub-periods):
    R = (EMV - BMV - CF) / (BMV + Weighted CF)

    Where:
    - EMV = Ending Market Value
    - BMV = Beginning Market Value
    - CF = Net Cash Flows
    - Weighted CF = Time-weighted cash flows
    """

    def calculate_period_return(
        self,
        beginning_value: Decimal,
        ending_value: Decimal,
        cash_flows: List[Tuple[date, Decimal]],  # List of (date, amount)
        period_start: date,
        period_end: date,
        fees: Decimal = Decimal('0')
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate gross and net return for a period using Modified Dietz.

        Returns: (gross_return, net_return)
        """
        if beginning_value <= 0:
            return Decimal('0'), Decimal('0')

        total_days = (period_end - period_start).days
        if total_days <= 0:
            return Decimal('0'), Decimal('0')

        # Calculate net cash flows and weighted cash flows
        net_cf = Decimal('0')
        weighted_cf = Decimal('0')

        for cf_date, cf_amount in cash_flows:
            net_cf += cf_amount
            # Weight = (total_days - days_held) / total_days
            days_held = (period_end - cf_date).days
            weight = Decimal(str(total_days - days_held)) / Decimal(str(total_days))
            weighted_cf += cf_amount * weight

        # Modified Dietz formula
        # Gross Return = (EMV - BMV - CF) / (BMV + Weighted CF)
        numerator = ending_value - beginning_value - net_cf
        denominator = beginning_value + weighted_cf

        if denominator <= 0:
            gross_return = Decimal('0')
        else:
            gross_return = numerator / denominator

        # Net return = Gross - fees (as percentage of assets)
        if beginning_value > 0:
            fee_rate = fees / beginning_value
            net_return = gross_return - fee_rate
        else:
            net_return = gross_return

        # Round to 6 decimal places
        gross_return = gross_return.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        net_return = net_return.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

        return gross_return, net_return

    def calculate_monthly_returns(
        self,
        valuations: List[Valuation],
        transactions: List[Transaction],
        fees_per_month: Optional[Dict[str, Decimal]] = None
    ) -> List[PerformanceReturn]:
        """
        Calculate monthly TWR returns from valuations and transactions.

        GIPS requires at least monthly valuation and return calculation.
        """
        if len(valuations) < 2:
            return []

        # Sort valuations by date
        sorted_vals = sorted(valuations, key=lambda v: v.date)

        # Group transactions by month
        transactions_by_month: Dict[str, List[Tuple[date, Decimal]]] = {}
        for t in transactions:
            if t.is_external_flow:
                month_key = t.date.strftime('%Y-%m')
                if month_key not in transactions_by_month:
                    transactions_by_month[month_key] = []
                transactions_by_month[month_key].append((t.date, t.net_external_flow))

        returns = []

        # Calculate return for each month
        for i in range(len(sorted_vals) - 1):
            start_val = sorted_vals[i]
            end_val = sorted_vals[i + 1]

            # Get cash flows for this period
            month_key = end_val.date.strftime('%Y-%m')
            cash_flows = transactions_by_month.get(month_key, [])

            # Filter to only flows within the period
            period_flows = [
                (d, amt) for d, amt in cash_flows
                if start_val.date < d <= end_val.date
            ]

            # Get fees for this month
            fees = Decimal('0')
            if fees_per_month and month_key in fees_per_month:
                fees = fees_per_month[month_key]

            gross_ret, net_ret = self.calculate_period_return(
                beginning_value=start_val.total_value,
                ending_value=end_val.total_value,
                cash_flows=period_flows,
                period_start=start_val.date,
                period_end=end_val.date,
                fees=fees
            )

            returns.append(PerformanceReturn(
                period_start=start_val.date,
                period_end=end_val.date,
                gross_return=gross_ret,
                net_return=net_ret,
                beginning_value=start_val.total_value,
                ending_value=end_val.total_value,
                net_external_flows=sum(amt for _, amt in period_flows),
                fees_charged=fees,
                account_id=start_val.account_id,
            ))

        return returns

    def link_returns(self, returns: List[PerformanceReturn]) -> Decimal:
        """
        Geometrically link periodic returns.

        GIPS requires geometric linking:
        Cumulative = (1+R1) * (1+R2) * ... * (1+Rn) - 1
        """
        if not returns:
            return Decimal('0')

        cumulative = Decimal('1')
        for r in returns:
            cumulative *= (Decimal('1') + r.net_return)

        return cumulative - Decimal('1')

    def annualize_return(
        self,
        cumulative_return: Decimal,
        num_periods: int,
        periods_per_year: int = 12
    ) -> Decimal:
        """
        Annualize a cumulative return.

        Formula: (1 + Cumulative) ^ (periods_per_year / num_periods) - 1
        """
        if num_periods < periods_per_year:
            # Less than 1 year - don't annualize per GIPS
            return cumulative_return

        years = Decimal(str(num_periods)) / Decimal(str(periods_per_year))
        annualized = (Decimal('1') + cumulative_return) ** (Decimal('1') / years) - Decimal('1')

        return annualized.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


@dataclass
class CompositeCalculator:
    """
    Composite-level return calculations.

    GIPS requires asset-weighted composite returns:
    Composite Return = Sum(Weight_i * Return_i)

    Where Weight_i = Account_i Beginning Value / Total Beginning Value
    """

    def calculate_composite_return(
        self,
        accounts: List[Account],
        period_start: date,
        period_end: date,
        use_beginning_weights: bool = True
    ) -> Optional[PerformanceReturn]:
        """
        Calculate asset-weighted composite return for a period.
        """
        total_beginning_value = Decimal('0')
        total_ending_value = Decimal('0')
        weighted_gross = Decimal('0')
        weighted_net = Decimal('0')
        total_flows = Decimal('0')
        total_fees = Decimal('0')

        account_returns = []

        for account in accounts:
            # Find returns for this period
            period_returns = account.get_returns_for_period(period_start, period_end)
            if not period_returns:
                continue

            # Aggregate multiple returns within period
            acc_gross = Decimal('1')
            acc_net = Decimal('1')
            acc_begin = period_returns[0].beginning_value if period_returns else Decimal('0')
            acc_end = period_returns[-1].ending_value if period_returns else Decimal('0')
            acc_flows = Decimal('0')
            acc_fees = Decimal('0')

            for r in period_returns:
                acc_gross *= (Decimal('1') + r.gross_return)
                acc_net *= (Decimal('1') + r.net_return)
                acc_flows += r.net_external_flows
                acc_fees += r.fees_charged

            acc_gross -= Decimal('1')
            acc_net -= Decimal('1')

            account_returns.append({
                'account_id': account.account_id,
                'beginning_value': acc_begin,
                'ending_value': acc_end,
                'gross_return': acc_gross,
                'net_return': acc_net,
                'flows': acc_flows,
                'fees': acc_fees,
            })

            total_beginning_value += acc_begin
            total_ending_value += acc_end
            total_flows += acc_flows
            total_fees += acc_fees

        if total_beginning_value <= 0:
            return None

        # Calculate weighted returns
        for acc_data in account_returns:
            weight = acc_data['beginning_value'] / total_beginning_value
            weighted_gross += weight * acc_data['gross_return']
            weighted_net += weight * acc_data['net_return']

        return PerformanceReturn(
            period_start=period_start,
            period_end=period_end,
            gross_return=weighted_gross.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
            net_return=weighted_net.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
            beginning_value=total_beginning_value,
            ending_value=total_ending_value,
            net_external_flows=total_flows,
            fees_charged=total_fees,
        )

    def calculate_annual_composite_returns(
        self,
        composite: Composite,
        years: List[int]
    ) -> List[PerformanceReturn]:
        """
        Calculate annual composite returns for specified years.
        """
        annual_returns = []

        for year in years:
            period_start = date(year, 1, 1)
            period_end = date(year, 12, 31)

            result = self.calculate_composite_return(
                accounts=composite.eligible_accounts,
                period_start=period_start,
                period_end=period_end,
            )

            if result:
                annual_returns.append(result)

        return annual_returns


@dataclass
class GIPSStatistics:
    """
    GIPS-required statistical calculations.

    Required disclosures:
    - 3-year annualized return (ex-post standard deviation)
    - Dispersion (for composites with 6+ accounts)
    - Composite assets and number of accounts
    """

    def calculate_3yr_annualized_std(
        self,
        monthly_returns: List[PerformanceReturn]
    ) -> Optional[Decimal]:
        """
        Calculate 3-year annualized standard deviation.

        GIPS requires this as a measure of risk.
        Formula: Monthly StdDev * sqrt(12)
        """
        if len(monthly_returns) < 36:  # Need 3 years of monthly data
            return None

        # Get last 36 months
        last_36 = sorted(monthly_returns, key=lambda r: r.period_start)[-36:]

        returns = [float(r.net_return) for r in last_36]

        # Calculate standard deviation
        mean = sum(returns) / len(returns)
        variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
        monthly_std = variance ** 0.5

        # Annualize: multiply by sqrt(12)
        annual_std = monthly_std * (12 ** 0.5)

        return Decimal(str(annual_std)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    def calculate_dispersion(
        self,
        accounts: List[Account],
        year: int
    ) -> Optional[Decimal]:
        """
        Calculate equal-weighted standard deviation of account returns.

        GIPS requires dispersion when composite has 6+ accounts.
        """
        annual_returns = []

        for account in accounts:
            for r in account.returns:
                if r.is_annual and r.period_start.year == year:
                    annual_returns.append(float(r.net_return))
                    break

        if len(annual_returns) < 6:
            return None  # GIPS doesn't require dispersion for < 6 accounts

        # Calculate standard deviation
        mean = sum(annual_returns) / len(annual_returns)
        variance = sum((x - mean) ** 2 for x in annual_returns) / (len(annual_returns) - 1)
        std_dev = variance ** 0.5

        return Decimal(str(std_dev)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    def calculate_composite_statistics(
        self,
        composite: Composite,
        as_of_date: date = None
    ) -> Dict:
        """
        Calculate all GIPS-required composite statistics.
        """
        if as_of_date is None:
            as_of_date = date.today()

        eligible = composite.eligible_accounts
        all_returns = []
        for acc in eligible:
            all_returns.extend(acc.returns)

        # Sort by date
        all_returns = sorted(all_returns, key=lambda r: r.period_start)

        # Calculate statistics
        stats = {
            'composite_id': composite.composite_id,
            'composite_name': composite.composite_name,
            'as_of_date': as_of_date.isoformat(),
            'total_assets': float(composite.total_assets),
            'num_accounts': len(eligible),
            'benchmark': composite.benchmark_name,
        }

        # 3-year annualized return and std dev
        monthly_returns = [r for r in all_returns if r.is_monthly]
        if len(monthly_returns) >= 36:
            last_36 = monthly_returns[-36:]

            # Cumulative return
            cumulative = Decimal('1')
            for r in last_36:
                cumulative *= (Decimal('1') + r.net_return)
            cumulative -= Decimal('1')

            # Annualize
            annualized = (Decimal('1') + cumulative) ** (Decimal('1') / Decimal('3')) - Decimal('1')

            stats['3yr_annualized_return'] = float(annualized.quantize(Decimal('0.0001')))
            stats['3yr_annualized_std'] = float(self.calculate_3yr_annualized_std(monthly_returns) or 0)
        else:
            stats['3yr_annualized_return'] = None
            stats['3yr_annualized_std'] = None

        # Annual returns for recent years
        current_year = as_of_date.year
        annual_returns = {}
        for year in range(current_year - 5, current_year + 1):
            period_start = date(year, 1, 1)
            period_end = date(year, 12, 31)

            year_returns = [r for r in all_returns
                          if r.period_start.year == year and r.is_monthly]

            if year_returns:
                cumulative = Decimal('1')
                for r in year_returns:
                    cumulative *= (Decimal('1') + r.net_return)
                annual_returns[year] = float((cumulative - Decimal('1')).quantize(Decimal('0.0001')))

        stats['annual_returns'] = annual_returns

        # Dispersion for years with 6+ accounts
        dispersion = {}
        for year in annual_returns.keys():
            disp = self.calculate_dispersion(eligible, year)
            if disp is not None:
                dispersion[year] = float(disp)

        stats['dispersion'] = dispersion

        return stats

    def generate_gips_disclosure(
        self,
        composite: Composite,
        firm_name: str,
        firm_total_assets: Decimal
    ) -> str:
        """
        Generate GIPS-required disclosure statement.
        """
        stats = self.calculate_composite_statistics(composite)

        pct_of_firm = (composite.total_assets / firm_total_assets * 100
                       if firm_total_assets > 0 else Decimal('0'))

        disclosure = f"""
GIPS COMPOSITE REPORT
=====================

{firm_name} claims compliance with the Global Investment Performance Standards (GIPS®).

COMPOSITE: {composite.composite_name}
COMPOSITE TYPE: {composite.composite_type.value}
INCEPTION DATE: {composite.inception_date.isoformat()}
BENCHMARK: {composite.benchmark_name or 'N/A'}

DESCRIPTION:
{composite.description}

COMPOSITE STATISTICS (as of {stats['as_of_date']}):
- Total Composite Assets: ${stats['total_assets']:,.2f}
- Number of Accounts: {stats['num_accounts']}
- Percentage of Firm Assets: {float(pct_of_firm):.2f}%
- 3-Year Annualized Return: {stats['3yr_annualized_return']:.2%} if stats.get('3yr_annualized_return') else 'N/A'
- 3-Year Annualized Std Dev: {stats['3yr_annualized_std']:.2%} if stats.get('3yr_annualized_std') else 'N/A'

ANNUAL RETURNS:
"""
        for year, ret in sorted(stats.get('annual_returns', {}).items()):
            disp = stats.get('dispersion', {}).get(year)
            disp_str = f" (Dispersion: {disp:.2%})" if disp else ""
            disclosure += f"  {year}: {ret:.2%}{disp_str}\n"

        disclosure += f"""
REQUIRED DISCLOSURES:
1. {firm_name} claims compliance with the Global Investment Performance Standards (GIPS®).
2. GIPS® is a registered trademark of CFA Institute.
3. Returns are calculated using time-weighted methodology.
4. Returns are presented net of fees unless otherwise noted.
5. The composite includes all fee-paying, discretionary accounts managed in this strategy.
6. Minimum account size: ${float(composite.minimum_assets):,.0f}
7. Base currency: {composite.currency}

For a complete list and description of all composites, please contact the firm.
"""
        return disclosure


def create_sample_valuations(
    account_id: str,
    start_date: date,
    end_date: date,
    initial_value: Decimal = Decimal('1000000'),
    monthly_return: Decimal = Decimal('0.007')  # ~8.7% annual
) -> List[Valuation]:
    """
    Create sample monthly valuations for testing.

    Used for demo/testing when real data not available.
    """
    valuations = []
    current_value = initial_value
    current_date = start_date

    while current_date <= end_date:
        valuations.append(Valuation(
            date=current_date,
            market_value=current_value,
            accrued_income=Decimal('0'),
            account_id=account_id,
        ))

        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

        # Apply return with some randomness
        import random
        variance = Decimal(str(random.uniform(-0.02, 0.03)))
        period_return = monthly_return + variance
        current_value = current_value * (Decimal('1') + period_return)

    return valuations
