"""
GIPS Report Generator
=====================
Generate GIPS-compliant performance reports.

Output formats:
- PDF: Full GIPS composite report
- Excel: Detailed performance data
- JSON: API-friendly format
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import json

from .models import Firm, Composite, Account, PerformanceReturn
from .calculators import TWRCalculator, CompositeCalculator, GIPSStatistics


@dataclass
class GIPSReportData:
    """Structured data for GIPS report generation."""

    # Firm info
    firm_name: str
    firm_description: str
    firm_total_assets: Decimal
    gips_compliant_since: Optional[date]
    verifier_name: Optional[str]

    # Composite info
    composite_name: str
    composite_description: str
    composite_type: str
    inception_date: date
    benchmark_name: Optional[str]
    minimum_assets: Decimal
    currency: str

    # Statistics
    composite_assets: Decimal
    num_accounts: int
    pct_of_firm: Decimal

    # Returns (by year)
    annual_returns: Dict[int, Dict[str, Any]]  # {year: {gross, net, benchmark, dispersion}}

    # Risk metrics
    three_year_return: Optional[Decimal]
    three_year_std_dev: Optional[Decimal]
    benchmark_three_year_return: Optional[Decimal]
    benchmark_three_year_std_dev: Optional[Decimal]

    # Monthly returns for charts
    monthly_returns: List[Dict[str, Any]]

    # Disclosures
    disclosures: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/API."""
        return {
            'firm': {
                'name': self.firm_name,
                'description': self.firm_description,
                'total_assets': float(self.firm_total_assets),
                'gips_compliant_since': self.gips_compliant_since.isoformat() if self.gips_compliant_since else None,
                'verifier': self.verifier_name,
            },
            'composite': {
                'name': self.composite_name,
                'description': self.composite_description,
                'type': self.composite_type,
                'inception_date': self.inception_date.isoformat(),
                'benchmark': self.benchmark_name,
                'minimum_assets': float(self.minimum_assets),
                'currency': self.currency,
                'total_assets': float(self.composite_assets),
                'num_accounts': self.num_accounts,
                'pct_of_firm': float(self.pct_of_firm),
            },
            'returns': {
                'annual': self.annual_returns,
                'monthly': self.monthly_returns,
            },
            'risk': {
                '3yr_annualized_return': float(self.three_year_return) if self.three_year_return else None,
                '3yr_annualized_std_dev': float(self.three_year_std_dev) if self.three_year_std_dev else None,
                'benchmark_3yr_return': float(self.benchmark_three_year_return) if self.benchmark_three_year_return else None,
                'benchmark_3yr_std_dev': float(self.benchmark_three_year_std_dev) if self.benchmark_three_year_std_dev else None,
            },
            'disclosures': self.disclosures,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class GIPSReportGenerator:
    """Generate GIPS-compliant reports."""

    def __init__(self, firm: Firm):
        self.firm = firm
        self.twr_calc = TWRCalculator()
        self.composite_calc = CompositeCalculator()
        self.stats = GIPSStatistics()

    def generate_composite_report(
        self,
        composite: Composite,
        as_of_date: date = None
    ) -> GIPSReportData:
        """Generate report data for a composite."""
        if as_of_date is None:
            as_of_date = date.today()

        # Calculate annual returns
        current_year = as_of_date.year
        annual_returns = {}

        for year in range(current_year - 10, current_year + 1):
            year_data = self._calculate_annual_return(composite, year)
            if year_data:
                annual_returns[year] = year_data

        # Calculate 3-year statistics
        all_monthly_returns = []
        for account in composite.eligible_accounts:
            all_monthly_returns.extend([r for r in account.returns if r.is_monthly])

        three_year_return = None
        three_year_std = None
        if len(all_monthly_returns) >= 36:
            sorted_returns = sorted(all_monthly_returns, key=lambda r: r.period_start)[-36:]
            cumulative = Decimal('1')
            for r in sorted_returns:
                cumulative *= (Decimal('1') + r.net_return)
            three_year_return = (cumulative ** (Decimal('1') / Decimal('3')) - Decimal('1'))
            three_year_std = self.stats.calculate_3yr_annualized_std(sorted_returns)

        # Monthly returns for charts
        monthly_data = []
        for r in sorted(all_monthly_returns, key=lambda x: x.period_start)[-36:]:
            monthly_data.append({
                'period_end': r.period_end.isoformat(),
                'gross_return': float(r.gross_return * 100),
                'net_return': float(r.net_return * 100),
            })

        # Percentage of firm
        pct_of_firm = Decimal('0')
        if self.firm.total_assets > 0:
            pct_of_firm = (composite.total_assets / self.firm.total_assets * 100)

        # Generate disclosures
        disclosures = self._generate_disclosures(composite)

        return GIPSReportData(
            firm_name=self.firm.firm_name,
            firm_description=self.firm.firm_description,
            firm_total_assets=self.firm.total_assets,
            gips_compliant_since=self.firm.gips_compliant_since,
            verifier_name=self.firm.verifier_name,
            composite_name=composite.composite_name,
            composite_description=composite.description,
            composite_type=composite.composite_type.value,
            inception_date=composite.inception_date,
            benchmark_name=composite.benchmark_name,
            minimum_assets=composite.minimum_assets,
            currency=composite.currency,
            composite_assets=composite.total_assets,
            num_accounts=composite.num_accounts,
            pct_of_firm=pct_of_firm,
            annual_returns=annual_returns,
            three_year_return=three_year_return,
            three_year_std_dev=three_year_std,
            benchmark_three_year_return=None,  # TODO: Fetch from benchmark
            benchmark_three_year_std_dev=None,
            monthly_returns=monthly_data,
            disclosures=disclosures,
        )

    def _calculate_annual_return(
        self,
        composite: Composite,
        year: int
    ) -> Optional[Dict[str, Any]]:
        """Calculate annual return for a specific year."""
        period_start = date(year, 1, 1)
        period_end = date(year, 12, 31)

        eligible_accounts = composite.eligible_accounts
        if not eligible_accounts:
            return None

        # Get returns for each account
        account_returns = []
        for account in eligible_accounts:
            year_returns = [r for r in account.returns
                          if r.period_start.year == year and r.is_monthly]
            if year_returns:
                # Link monthly returns
                cumulative = Decimal('1')
                for r in year_returns:
                    cumulative *= (Decimal('1') + r.net_return)
                account_returns.append({
                    'account_id': account.account_id,
                    'return': cumulative - Decimal('1'),
                    'value': account.total_market_value,
                })

        if not account_returns:
            return None

        # Asset-weighted return
        total_value = sum(a['value'] for a in account_returns)
        if total_value <= 0:
            return None

        weighted_return = sum(a['return'] * a['value'] for a in account_returns) / total_value

        # Calculate dispersion if 6+ accounts
        dispersion = None
        if len(account_returns) >= 6:
            returns = [float(a['return']) for a in account_returns]
            mean = sum(returns) / len(returns)
            variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
            dispersion = variance ** 0.5

        return {
            'year': year,
            'gross_return': float(weighted_return * 100),  # TODO: Calculate gross
            'net_return': float(weighted_return * 100),
            'benchmark_return': None,  # TODO: Fetch benchmark
            'num_accounts': len(account_returns),
            'composite_assets': float(total_value),
            'dispersion': dispersion * 100 if dispersion else None,
        }

    def _generate_disclosures(self, composite: Composite) -> List[str]:
        """Generate required GIPS disclosures."""
        disclosures = [
            f"{self.firm.firm_name} claims compliance with the Global Investment Performance Standards (GIPS®).",
            "GIPS® is a registered trademark of CFA Institute. CFA Institute does not endorse or promote this organization, nor does it warrant the accuracy or quality of the content contained herein.",
            f"The {composite.composite_name} composite includes all fee-paying, discretionary accounts managed in this strategy.",
            "Returns are calculated using time-weighted methodology with geometric linking of periodic returns.",
            "Returns are presented net of management fees and trading costs.",
            f"The composite was created on {composite.inception_date.strftime('%B %d, %Y')}.",
            f"The minimum account size for this composite is ${float(composite.minimum_assets):,.0f}.",
            f"Valuations are computed in {composite.currency}.",
        ]

        if composite.benchmark_name:
            disclosures.append(
                f"The benchmark is the {composite.benchmark_name}. The benchmark is used for comparative purposes only."
            )

        if self.firm.verifier_name and self.firm.verification_date:
            disclosures.append(
                f"{self.firm.firm_name} has been independently verified by {self.firm.verifier_name} "
                f"as of {self.firm.verification_date.strftime('%B %d, %Y')}."
            )
        else:
            disclosures.append(
                f"{self.firm.firm_name} has not been independently verified."
            )

        disclosures.append(
            "A complete list and description of all composites is available upon request."
        )

        disclosures.append(
            "Past performance is not indicative of future results."
        )

        return disclosures


def generate_account_performance_report(
    account: Account,
    returns: List[PerformanceReturn]
) -> Dict[str, Any]:
    """Generate performance report for a single account."""
    if not returns:
        return {
            'account_id': account.account_id,
            'account_name': account.account_name,
            'returns': [],
            'summary': None,
        }

    # Sort returns
    sorted_returns = sorted(returns, key=lambda r: r.period_start)

    # Calculate cumulative return
    cumulative_gross = Decimal('1')
    cumulative_net = Decimal('1')

    monthly_data = []
    for r in sorted_returns:
        cumulative_gross *= (Decimal('1') + r.gross_return)
        cumulative_net *= (Decimal('1') + r.net_return)

        monthly_data.append({
            'period_start': r.period_start.isoformat(),
            'period_end': r.period_end.isoformat(),
            'gross_return': float(r.gross_return * 100),
            'net_return': float(r.net_return * 100),
            'cumulative_gross': float((cumulative_gross - 1) * 100),
            'cumulative_net': float((cumulative_net - 1) * 100),
            'beginning_value': float(r.beginning_value),
            'ending_value': float(r.ending_value),
        })

    # Annualized return (if 12+ months)
    annualized = None
    if len(sorted_returns) >= 12:
        years = len(sorted_returns) / 12
        annualized = float(
            ((cumulative_net ** (Decimal('1') / Decimal(str(years)))) - 1) * 100
        )

    return {
        'account_id': account.account_id,
        'account_name': account.account_name,
        'inception_date': account.inception_date.isoformat(),
        'market_value': float(account.total_market_value),
        'returns': monthly_data,
        'summary': {
            'total_periods': len(sorted_returns),
            'date_range': {
                'start': sorted_returns[0].period_start.isoformat(),
                'end': sorted_returns[-1].period_end.isoformat(),
            },
            'cumulative_gross_return': float((cumulative_gross - 1) * 100),
            'cumulative_net_return': float((cumulative_net - 1) * 100),
            'annualized_return': annualized,
            'total_fees': float(sum(r.fees_charged for r in sorted_returns)),
        },
    }


def create_gips_excel_data(report: GIPSReportData) -> Dict[str, List[List[Any]]]:
    """Create data structure for Excel export."""
    sheets = {}

    # Summary sheet
    summary_data = [
        ['GIPS COMPOSITE REPORT'],
        [''],
        ['Firm Information'],
        ['Firm Name', report.firm_name],
        ['Total Firm Assets', f"${float(report.firm_total_assets):,.0f}"],
        ['GIPS Compliant Since', report.gips_compliant_since.isoformat() if report.gips_compliant_since else 'N/A'],
        ['Verifier', report.verifier_name or 'Not Verified'],
        [''],
        ['Composite Information'],
        ['Composite Name', report.composite_name],
        ['Strategy Type', report.composite_type],
        ['Inception Date', report.inception_date.isoformat()],
        ['Benchmark', report.benchmark_name or 'N/A'],
        ['Minimum Account Size', f"${float(report.minimum_assets):,.0f}"],
        ['Currency', report.currency],
        [''],
        ['Current Statistics'],
        ['Composite Assets', f"${float(report.composite_assets):,.0f}"],
        ['Number of Accounts', report.num_accounts],
        ['% of Firm Assets', f"{float(report.pct_of_firm):.2f}%"],
        ['3-Year Annualized Return', f"{float(report.three_year_return * 100):.2f}%" if report.three_year_return else 'N/A'],
        ['3-Year Annualized Std Dev', f"{float(report.three_year_std_dev * 100):.2f}%" if report.three_year_std_dev else 'N/A'],
    ]
    sheets['SUMMARY'] = summary_data

    # Annual returns sheet
    annual_headers = ['Year', 'Net Return (%)', 'Gross Return (%)', 'Benchmark (%)',
                      'Num Accounts', 'Composite Assets', 'Dispersion (%)']
    annual_rows = [annual_headers]

    for year in sorted(report.annual_returns.keys(), reverse=True):
        data = report.annual_returns[year]
        annual_rows.append([
            year,
            data.get('net_return'),
            data.get('gross_return'),
            data.get('benchmark_return') or '',
            data.get('num_accounts'),
            data.get('composite_assets'),
            data.get('dispersion') or '',
        ])

    sheets['ANNUAL_RETURNS'] = annual_rows

    # Monthly returns sheet
    monthly_headers = ['Period End', 'Net Return (%)', 'Gross Return (%)']
    monthly_rows = [monthly_headers]

    for m in report.monthly_returns:
        monthly_rows.append([
            m['period_end'],
            m['net_return'],
            m['gross_return'],
        ])

    sheets['MONTHLY_RETURNS'] = monthly_rows

    # Disclosures sheet
    disclosure_rows = [['REQUIRED DISCLOSURES'], ['']]
    for i, d in enumerate(report.disclosures, 1):
        disclosure_rows.append([f"{i}. {d}"])

    sheets['DISCLOSURES'] = disclosure_rows

    return sheets
