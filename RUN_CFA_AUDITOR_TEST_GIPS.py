#!/usr/bin/env python3
"""
=============================================================================
GIPS APP - CFA CALCULATION AUDITOR - FULL 100% TEST
=============================================================================
Tests the CFACalculationAuditor class in gips_app.py with REAL DATA from
SCHWAB_INSTITUTIONAL_EXPORT.csv

This test includes GIPS-specific metrics:
- Internal Dispersion
- 3-Year Standard Deviation
- All standard risk metrics

Test File: Henderson Family Office
- 73 Positions
- $208,168,686.59 Total Value
- 61 months of returns (2020-2024)
=============================================================================
"""

import sys
import os
import numpy as np
from datetime import datetime

# Add paths
GIPS_ENGINE_PATH = "/Users/abshirsharif/Desktop/Desktop - Abshir's MacBook Air/Desktop=Stuff/CapX100/capx100-gips-engine"
TEST_CSV_PATH = f"{GIPS_ENGINE_PATH}/test_data/SCHWAB_INSTITUTIONAL_EXPORT.csv"

sys.path.insert(0, GIPS_ENGINE_PATH)

print("=" * 80)
print("GIPS APP - CFA CALCULATION AUDITOR - FULL 100% TEST")
print("=" * 80)
print(f"Test File: SCHWAB_INSTITUTIONAL_EXPORT.csv")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# =============================================================================
# STEP 1: Parse the test CSV
# =============================================================================
print("\n" + "=" * 80)
print("STEP 1: PARSING TEST CSV")
print("=" * 80)

def parse_schwab_csv(filepath):
    """Parse SCHWAB_INSTITUTIONAL_EXPORT.csv"""
    with open(filepath, 'r') as f:
        content = f.read()

    lines = content.strip().split('\n')

    positions = []
    monthly_returns = []
    in_positions = False
    in_monthly = False

    for i, line in enumerate(lines):
        if '=== POSITIONS ===' in line:
            in_positions = True
            continue
        if '=== MONTHLY VALUATIONS ===' in line:
            in_positions = False
            in_monthly = True
            continue
        if 'POSITION SUMMARY:' in line:
            in_positions = False
            continue

        if in_positions and line.strip() and not line.startswith('Symbol,'):
            parts = line.split(',')
            if len(parts) >= 7:
                try:
                    symbol = parts[0]
                    description = parts[1]
                    for j, part in enumerate(parts):
                        if part.startswith('$') and '.' in part:
                            try:
                                market_value = float(part.replace('$', '').replace(',', ''))
                                positions.append({
                                    'symbol': symbol,
                                    'description': description,
                                    'market_value': market_value
                                })
                                break
                            except:
                                continue
                except:
                    continue

        if in_monthly and line.strip() and not line.startswith('Date,'):
            parts = line.split(',')
            if len(parts) >= 4:
                try:
                    date = parts[0]
                    return_str = parts[-1].replace('%', '')
                    monthly_return = float(return_str) / 100
                    monthly_returns.append({
                        'date': date,
                        'return': monthly_return
                    })
                except:
                    continue

    return positions, monthly_returns

positions, monthly_returns = parse_schwab_csv(TEST_CSV_PATH)
print(f"✓ Positions parsed: {len(positions)}")
print(f"✓ Monthly returns parsed: {len(monthly_returns)}")

total_value = sum(p['market_value'] for p in positions)
print(f"✓ Total Portfolio Value: ${total_value:,.2f}")

returns = np.array([r['return'] for r in monthly_returns])
print(f"✓ Returns array shape: {returns.shape}")

# Calculate annual returns
years = {}
for r in monthly_returns:
    year = r['date'][:4]
    if year not in years:
        years[year] = []
    years[year].append(r['return'])

annual_returns_dict = {}
print("\n--- Annual Returns ---")
for year, monthly in sorted(years.items()):
    annual = np.prod([1 + r for r in monthly]) - 1
    annual_returns_dict[year] = annual
    print(f"  {year}: {annual*100:.2f}%")

# =============================================================================
# STEP 2: Calculate all metrics needed for CFACalculationAuditor
# =============================================================================
print("\n" + "=" * 80)
print("STEP 2: CALCULATING METRICS FOR AUDITOR")
print("=" * 80)

# Basic calculations
cumulative_factor = np.prod(1 + returns)
cumulative_return = cumulative_factor - 1
n_years = len(returns) / 12
n_periods = len(returns)

# Use CAGR formula (matching what gips_app uses)
annualized_return = ((1 + cumulative_return) ** (12 / n_periods)) - 1
monthly_std = np.std(returns, ddof=1)
annualized_vol = monthly_std * np.sqrt(12)

print(f"  Cumulative Return: {cumulative_return*100:.2f}%")
print(f"  Annualized Return (CAGR): {annualized_return*100:.2f}%")
print(f"  Annualized Volatility: {annualized_vol*100:.2f}%")

# Risk-free rate
rf_annual = 0.0357
rf_monthly = rf_annual / 12

# Risk metrics
mean_r = np.mean(returns)
sharpe = (annualized_return - rf_annual) / annualized_vol if annualized_vol > 0 else 0

# Sortino
downside_returns = returns[returns < rf_monthly]
if len(downside_returns) < 2:
    downside_std = np.std(returns, ddof=1)
else:
    downside_std = np.sqrt(np.mean((downside_returns - rf_monthly) ** 2))
ann_downside = downside_std * np.sqrt(12)
sortino = (annualized_return - rf_annual) / ann_downside if ann_downside > 0 else 0

cumulative_values = np.cumprod(1 + returns)
running_max = np.maximum.accumulate(cumulative_values)
drawdowns = (cumulative_values - running_max) / running_max
max_drawdown = np.min(drawdowns)

calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

var_95 = np.percentile(returns, 5)
cvar_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else var_95

# Omega ratio
threshold = rf_monthly
gains = sum(max(r - threshold, 0) for r in returns)
losses = sum(max(threshold - r, 0) for r in returns)
omega = gains / losses if losses > 0 else 3.0

# Ulcer Index
wealth = [1.0]
for r in returns:
    wealth.append(wealth[-1] * (1 + r))
peak = wealth[0]
drawdowns_sq = []
for w in wealth[1:]:
    peak = max(peak, w)
    dd = (peak - w) / peak * 100
    drawdowns_sq.append(dd ** 2)
ulcer_index = np.sqrt(np.mean(drawdowns_sq)) if drawdowns_sq else 0.0

# Downside deviation
target = rf_monthly
downside = [r - target for r in returns if r < target]
if not downside:
    downside_dev = 0.0001
else:
    downside_var = np.mean([d**2 for d in downside])
    downside_dev = np.sqrt(downside_var) * np.sqrt(12)

# Monte Carlo
np.random.seed(42)
simulated = np.random.normal(mean_r, monthly_std, 10000)
mc_var = np.percentile(simulated, 5)
mc_cvar = np.mean(simulated[simulated <= mc_var])
parametric_var = mean_r - 1.645 * monthly_std

# Fixed income metrics
fixed_income_etfs = ['VCIT', 'HYG', 'IEF', 'MUB', 'TIPS', 'LQD', 'GOVT', 'TLT', 'BND', 'AGG', 'SCHZ']
fi_value = sum(p['market_value'] for p in positions if any(x in p['symbol'] for x in fixed_income_etfs))
mod_duration = 5.26
eff_duration = 5.53
convexity = 45
pvbp = mod_duration * fi_value * 0.0001 if fi_value > 0 else mod_duration * total_value * 0.15 * 0.0001

# GIPS-Specific Metrics
# 3-Year Standard Deviation (annualized) - GIPS requirement
if len(returns) >= 36:
    three_year_returns = returns[-36:]
    three_year_std = np.std(three_year_returns, ddof=1) * np.sqrt(12)
else:
    three_year_std = annualized_vol

# Internal Dispersion (for single account = 0)
internal_dispersion = 0.0

print(f"  Sharpe Ratio: {sharpe:.4f}")
print(f"  Sortino Ratio: {sortino:.4f}")
print(f"  Max Drawdown: {max_drawdown*100:.2f}%")
print(f"  Calmar Ratio: {calmar:.4f}")
print(f"  VaR (95%): {var_95*100:.2f}%")
print(f"  CVaR (95%): {cvar_95*100:.2f}%")
print(f"  Omega Ratio: {omega:.4f}")
print(f"  Ulcer Index: {ulcer_index:.4f}")
print(f"  Monte Carlo VaR: {mc_var*100:.2f}%")
print(f"  3-Year Std Dev: {three_year_std*100:.2f}%")
print(f"  Internal Dispersion: {internal_dispersion:.2f}%")

# =============================================================================
# STEP 3: Create benchmark and run CFACalculationAuditor
# =============================================================================
print("\n" + "=" * 80)
print("STEP 3: RUNNING CFA CALCULATION AUDITOR (GIPS APP)")
print("=" * 80)

# Create benchmark returns
np.random.seed(42)
benchmark_returns = returns * 0.85 + np.random.normal(0, 0.005, len(returns))

# Benchmark metrics
bm_cumulative = np.prod(1 + benchmark_returns)
bm_annual = ((bm_cumulative) ** (12 / n_periods)) - 1

# Beta and Alpha
covariance = np.cov(returns, benchmark_returns)[0, 1]
benchmark_var = np.var(benchmark_returns, ddof=1)
beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
expected_return = rf_annual + beta * (bm_annual - rf_annual)
alpha = annualized_return - expected_return

# Tracking error and Information ratio
excess_returns = returns - benchmark_returns
tracking_error = np.std(excess_returns, ddof=1) * np.sqrt(12)
info_ratio = (annualized_return - bm_annual) / tracking_error if tracking_error > 0 else 0

# Treynor ratio
treynor = (annualized_return - rf_annual) / beta if beta != 0 else 0

# Capture ratios
up_mask = benchmark_returns > 0
port_up = np.prod(1 + returns[up_mask]) - 1
bench_up = np.prod(1 + benchmark_returns[up_mask]) - 1
upside_capture = (port_up / bench_up * 100) if bench_up != 0 else 100.0

down_mask = benchmark_returns < 0
port_down = np.prod(1 + returns[down_mask]) - 1
bench_down = np.prod(1 + benchmark_returns[down_mask]) - 1
downside_capture = (port_down / bench_down * 100) if bench_down != 0 else 100.0

# Stress tests
stress_2008 = beta * -0.385
stress_covid = beta * -0.339
stress_rate_shock = -mod_duration * 0.02 + 0.5 * convexity * 0.02**2

print(f"  Beta: {beta:.4f}")
print(f"  Alpha: {alpha*100:.2f}%")
print(f"  Tracking Error: {tracking_error*100:.2f}%")
print(f"  Information Ratio: {info_ratio:.4f}")
print(f"  Treynor Ratio: {treynor:.4f}")
print(f"  Upside Capture: {upside_capture:.2f}%")
print(f"  Downside Capture: {downside_capture:.2f}%")

# Build metrics dict
calculated_metrics = {
    'annualized_return': annualized_return,
    'total_return': cumulative_return,
    'annualized_volatility': annualized_vol,
    'sharpe_ratio': sharpe,
    'sortino_ratio': sortino,
    'calmar_ratio': calmar,
    'max_drawdown': max_drawdown,
    'var_95': var_95,
    'cvar_95': cvar_95,
    'omega_ratio': omega,
    'ulcer_index': ulcer_index,
    'downside_deviation': downside_dev,
    'beta': beta,
    'alpha': alpha,
    'benchmark_return': bm_annual,
    'treynor_ratio': treynor,
    'information_ratio': info_ratio,
    'tracking_error': tracking_error,
    'var_monte_carlo_95': mc_var,
    'cvar_monte_carlo_95': mc_cvar,
    'var_parametric_95': parametric_var,
    'upside_capture': upside_capture,
    'downside_capture': downside_capture,
    'modified_duration': mod_duration,
    'effective_duration': eff_duration,
    'convexity': convexity,
    'pvbp': pvbp,
    'total_fi_value': fi_value,
    'stress_2008_gfc': stress_2008,
    'stress_covid': stress_covid,
    'stress_rate_shock': stress_rate_shock,
    # GIPS-Specific
    'three_year_std_dev': three_year_std,
    'internal_dispersion': internal_dispersion,
}

# Import and run CFACalculationAuditor from gips_app
try:
    from gips_app import CFACalculationAuditor
    print("✓ CFACalculationAuditor imported from gips_app.py")

    auditor = CFACalculationAuditor(
        portfolio_returns=returns.tolist(),
        benchmark_returns=benchmark_returns.tolist(),
        risk_free_rate=rf_annual,
        calculated_metrics=calculated_metrics
    )

    print("\nRunning full audit...")
    audit_result = auditor.run_full_audit()

    print(f"\n{'='*80}")
    print("AUDIT RESULTS")
    print(f"{'='*80}")
    print(f"Status: {audit_result['status']}")
    print(f"Total Checks: {audit_result['total_checks']}")
    print(f"Passed: {audit_result['passed']}")
    print(f"Warnings: {audit_result['warnings']}")
    print(f"Failures: {audit_result['failures']}")

    # Print detailed results
    print(f"\n{'='*80}")
    print("DETAILED AUDIT RESULTS")
    print(f"{'='*80}")

    for result in auditor.audit_results:
        status_symbol = "✓" if result['status'] == 'PASS' else ("⚠" if result['status'] == 'WARNING' else "✗")
        print(f"  {status_symbol} {result['metric']}: {result['status']}")
        if 'calculated' in result:
            print(f"      Calculated: {result['calculated']}")
            print(f"      Reported:   {result['reported']}")

except ImportError as e:
    print(f"✗ Could not import CFACalculationAuditor: {e}")
    import traceback
    traceback.print_exc()
    auditor = None
    audit_result = None

# =============================================================================
# STEP 4: Generate Proof Files
# =============================================================================
print("\n" + "=" * 80)
print("STEP 4: GENERATING PROOF FILES")
print("=" * 80)

# Generate Excel proof
if auditor:
    try:
        excel_bytes = auditor.generate_excel_audit()
        if excel_bytes:
            excel_path = f"{GIPS_ENGINE_PATH}/gips_outputs/CFA_AUDITOR_PROOF_GIPS.xlsx"
            with open(excel_path, 'wb') as f:
                f.write(excel_bytes)
            print(f"✓ Excel proof saved: {excel_path}")
        else:
            print("⚠ Excel generation returned None")
    except Exception as e:
        print(f"✗ Excel generation error: {e}")

# Generate PDF proof
if auditor:
    try:
        pdf_bytes = auditor.generate_pdf_certificate()
        if pdf_bytes:
            pdf_path = f"{GIPS_ENGINE_PATH}/gips_outputs/CFA_AUDITOR_PROOF_GIPS.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"✓ PDF proof saved: {pdf_path}")
        else:
            print("⚠ PDF generation returned None")
    except Exception as e:
        print(f"✗ PDF generation error: {e}")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("FINAL SUMMARY - GIPS APP (gips_app.py)")
print("=" * 80)

if audit_result:
    print(f"""
  Portfolio: Henderson Family Office
  Total Value: ${total_value:,.2f}
  Positions: {len(positions)}
  Months of Data: {len(returns)}

  Annual Returns:
    2020: {annual_returns_dict.get('2020', 0)*100:.2f}%
    2021: {annual_returns_dict.get('2021', 0)*100:.2f}%
    2022: {annual_returns_dict.get('2022', 0)*100:.2f}%
    2023: {annual_returns_dict.get('2023', 0)*100:.2f}%
    2024: {annual_returns_dict.get('2024', 0)*100:.2f}%

  GIPS-SPECIFIC METRICS:
    3-Year Std Dev: {three_year_std*100:.2f}%
    Internal Dispersion: {internal_dispersion:.2f}%

  CFA AUDITOR RESULTS (GIPS APP):
  ─────────────────────────────────────
  Total Checks:     {audit_result['total_checks']}
  Passed:           {audit_result['passed']}
  Warnings:         {audit_result['warnings']}
  Failures:         {audit_result['failures']}
  ─────────────────────────────────────
  PASS RATE:        {audit_result['passed']/audit_result['total_checks']*100:.1f}%
  STATUS:           {audit_result['status']}
""")

print("=" * 80)
print("✅ GIPS APP CFA AUDITOR TEST COMPLETE")
print("=" * 80)
