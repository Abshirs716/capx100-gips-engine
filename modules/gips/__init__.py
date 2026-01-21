"""
GIPS (Global Investment Performance Standards) Module
======================================================
Full Phase 2 GIPS Compliance Implementation

Provides:
- Time-Weighted Return (TWR) calculations
- Composite management and aggregation
- GIPS-compliant statistics (3-year annualized, dispersion)
- Multi-account household support
- Required disclosures generation

Target Markets:
- GIPS-Ready: Small RIAs wanting institutional credibility
- GIPS-Compliant: Institutional clients requiring full compliance
"""

from .models import (
    Firm,
    Composite,
    Account,
    Household,
    Transaction,
    Valuation,
    PerformanceReturn,
    TransactionType,
    CompositeType,
)

from .calculators import (
    TWRCalculator,
    CompositeCalculator,
    GIPSStatistics,
)

from .parser import GIPSTransactionParser

from .benchmarks import (
    fetch_benchmark_returns_yfinance,
    get_3year_benchmark_stats,
    get_benchmark_stats_for_period,
    compare_to_benchmark,
    BenchmarkData,
    BenchmarkReturn,
    BENCHMARK_REGISTRY,
)

from .reports import (
    GIPSReportGenerator,
    GIPSReportData,
    generate_account_performance_report,
    create_gips_excel_data,
)

__all__ = [
    # Models
    'Firm',
    'Composite',
    'Account',
    'Household',
    'Transaction',
    'Valuation',
    'PerformanceReturn',
    'TransactionType',
    'CompositeType',
    # Calculators
    'TWRCalculator',
    'CompositeCalculator',
    'GIPSStatistics',
    # Parser
    'GIPSTransactionParser',
    # Benchmarks
    'fetch_benchmark_returns_yfinance',
    'get_3year_benchmark_stats',
    'get_benchmark_stats_for_period',
    'compare_to_benchmark',
    'BenchmarkData',
    'BenchmarkReturn',
    'BENCHMARK_REGISTRY',
    # Reports
    'GIPSReportGenerator',
    'GIPSReportData',
    'generate_account_performance_report',
    'create_gips_excel_data',
]

__version__ = '2.0.0'
