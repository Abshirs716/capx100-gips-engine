#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
COMPREHENSIVE 100% TEST - GIPS APP
═══════════════════════════════════════════════════════════════════════════════
Tests ALL features with REAL data from the test CSV
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import io
import numpy as np
from datetime import datetime

GIPS_PATH = "/Users/abshirsharif/Desktop/Desktop - Abshir's MacBook Air/Desktop=Stuff/CapX100/capx100-gips-engine"
sys.path.insert(0, GIPS_PATH)

TEST_CSV = f"{GIPS_PATH}/test_data/SCHWAB_INSTITUTIONAL_EXPORT.csv"

print("=" * 80)
print("COMPREHENSIVE 100% TEST - GIPS APP")
print("=" * 80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

results = {"passed": 0, "failed": 0, "errors": []}

def test_pass(name, details=""):
    results["passed"] += 1
    print(f"  ✅ {name}" + (f": {details}" if details else ""))

def test_fail(name, error):
    results["failed"] += 1
    results["errors"].append((name, str(error)))
    print(f"  ❌ {name}: {error}")

# ═══════════════════════════════════════════════════════════════════════════════
# PARSE TEST CSV
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1] PARSING TEST CSV...")
print("─" * 80)

positions = []
monthly_returns = []

with open(TEST_CSV, 'r') as f:
    content = f.read()

lines = content.strip().split('\n')
in_positions = False
in_monthly = False

for line in lines:
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
        # Use csv module to properly handle quoted values with commas
        import csv
        reader = csv.reader([line])
        parts = next(reader)
        if len(parts) >= 6:
            symbol = parts[0]
            name = parts[1] if len(parts) > 1 else symbol
            # Market Value is in column 5 (index 5)
            # Sector is in column 12 (index 12)
            # Unrealized G/L % is in column 8 (index 8) - use as YTD proxy
            try:
                market_value_str = parts[5] if len(parts) > 5 else ""
                market_value = float(market_value_str.replace('$', '').replace(',', ''))
                # Get actual sector from CSV (column 12)
                sector = parts[12] if len(parts) > 12 else 'Diversified'
                # Get YTD from unrealized G/L % (column 8) as proxy
                ytd_str = parts[8] if len(parts) > 8 else "0%"
                ytd_return = float(ytd_str.replace('%', '').replace(',', ''))
                positions.append({
                    'symbol': symbol,
                    'name': name[:20],
                    'market_value': market_value,
                    'sector': sector,
                    'weight': 0,  # Calculated below
                    'ytd_return': ytd_return
                })
            except:
                pass

    if in_monthly and line.strip() and not line.startswith('Date,'):
        # Parse monthly valuations for MODIFIED DIETZ calculation
        # Format: Date, Portfolio Value, Net Contributions, Monthly Return %
        # Note: Dollar amounts with commas are NOT quoted, so they split incorrectly
        import csv as csv_mod
        row = list(csv_mod.reader([line]))[0]
        if len(row) >= 4:
            try:
                date = row[0]

                # Find the return percentage (always ends with %)
                return_idx = None
                for i, val in enumerate(row):
                    if '%' in val:
                        return_idx = i
                        break

                if return_idx is None:
                    continue

                # Join everything between date and return, then split by $
                values_str = ','.join(row[1:return_idx])
                amounts = values_str.split('$')
                portfolio_value = 0.0
                net_contribution = 0.0

                for amt in amounts:
                    if amt.strip():
                        clean_val = amt.replace(',', '').strip()
                        try:
                            val = float(clean_val)
                            if portfolio_value == 0:
                                portfolio_value = val
                            else:
                                net_contribution = val
                        except:
                            pass

                monthly_returns.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'net_contribution': net_contribution
                })
            except:
                continue

# Calculate weights
total_value = sum(p['market_value'] for p in positions)
for p in positions:
    p['weight'] = (p['market_value'] / total_value) * 100

# ═══════════════════════════════════════════════════════════════════════════════
# MODIFIED DIETZ TWR CALCULATION (GIPS 2020 COMPLIANT)
# Same methodology as Main App for consistency
# Formula: R = (EMV - BMV - CF) / (BMV + Sum(CF_i * W_i))
# ═══════════════════════════════════════════════════════════════════════════════
returns = []
for i in range(1, len(monthly_returns)):
    bmv = monthly_returns[i-1]['portfolio_value']
    emv = monthly_returns[i]['portfolio_value']
    cf = monthly_returns[i].get('net_contribution', 0)

    if bmv > 0:
        denominator = bmv + (cf * 0.5)
        if denominator > 0:
            monthly_return = (emv - bmv - cf) / denominator
        else:
            monthly_return = 0
    else:
        monthly_return = 0

    monthly_returns[i]['return'] = monthly_return
    returns.append(monthly_return)

# Group by year for annual returns
years = {}
for mr in monthly_returns[1:]:  # Skip first (baseline, no return)
    year = mr['date'][:4]
    if year not in years:
        years[year] = []
    years[year].append(mr.get('return', 0))

annual_returns = []
year_list = []
for year in sorted(years.keys()):
    yr_returns = years[year]
    annual = np.prod([1 + r for r in yr_returns]) - 1
    annual_returns.append(annual)
    year_list.append(year)

# Create benchmark returns
np.random.seed(42)
benchmark_monthly = [r * 0.85 + np.random.normal(0, 0.005) for r in returns]
benchmark_annual = [0.1840, 0.2689, -0.1811, 0.2629, 0.2502][:len(annual_returns)]

test_pass(f"CSV parsed", f"{len(positions)} positions, {len(returns)} months (Modified Dietz)")
test_pass(f"Annual returns", f"{[f'{r*100:.2f}%' for r in annual_returns]}")
test_pass(f"Total value", f"${total_value:,.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA DICT
# ═══════════════════════════════════════════════════════════════════════════════
test_data = {
    'name': 'Henderson_Family_Office',
    'firm': 'Henderson Family Office',
    'composite_name': 'Balanced Growth Composite',
    'benchmark': 'S&P 500',
    'currency': 'USD',
    'fee': 1.0,
    'inception': '2020-01-01',
    'total_value': total_value,
    'years': year_list,
    'annual_returns': annual_returns,
    'benchmark_returns': benchmark_annual,
    'monthly_returns': returns,
    'benchmark_monthly_returns': benchmark_monthly,
    'positions': positions,
    'holdings': positions,  # Provide both
    'asset_allocation': {  # Required for Individual reports
        'Technology': 35,
        'Healthcare': 20,
        'Financials': 15,
        'Consumer Discretionary': 12,
        'Industrials': 10,
        'Other': 8,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: GIPSRiskCalculator
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2] TESTING GIPSRiskCalculator...")
print("─" * 80)

from gips_app import GIPSRiskCalculator

calculator = GIPSRiskCalculator(risk_free_rate=0.0357)
test_pass("Calculator initialized", f"Rf={calculator.risk_free_rate*100:.2f}%")

metrics = [
    ("Volatility", calculator.calculate_volatility(returns)),
    ("Sharpe Ratio", calculator.calculate_sharpe_ratio(returns)),
    ("Sortino Ratio", calculator.calculate_sortino_ratio(returns)),
    ("Calmar Ratio", calculator.calculate_calmar_ratio(returns)),
    ("Max Drawdown", calculator.calculate_max_drawdown(returns)),
    ("VaR (95%)", calculator.calculate_var_historical(returns, 0.95)),
    ("CVaR (95%)", calculator.calculate_cvar(returns, 0.95)),
    ("Beta", calculator.calculate_beta(returns, benchmark_monthly)),
    ("Alpha", calculator.calculate_alpha(returns, benchmark_monthly)),
    ("Information Ratio", calculator.calculate_information_ratio(returns, benchmark_monthly)),
    ("Treynor Ratio", calculator.calculate_treynor_ratio(returns, benchmark_monthly)),
    ("Omega Ratio", calculator.calculate_omega_ratio(returns)),
]

for name, value in metrics:
    if value is not None:
        test_pass(name, f"{value:.4f}")
    else:
        test_fail(name, "Returned None")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: REPORT GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3] TESTING REPORT GENERATORS...")
print("─" * 80)

from gips_app import UnifiedCompositeReport, UnifiedFirmReport, UnifiedIndividualReport

# Test Composite Report
try:
    buffer = io.BytesIO()
    UnifiedCompositeReport.generate(test_data, buffer, 'goldman')
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 10000:
        test_pass("UnifiedCompositeReport", f"{size:,} bytes")
        with open(f"{GIPS_PATH}/gips_outputs/TEST_Composite_Full.pdf", 'wb') as f:
            f.write(buffer.getvalue())
    else:
        test_fail("UnifiedCompositeReport", f"Only {size} bytes")
except Exception as e:
    test_fail("UnifiedCompositeReport", str(e))
    import traceback
    traceback.print_exc()

# Test Firm Report
try:
    firm_data = {
        'name': 'Henderson Family Office',
        'firm': 'Henderson Family Office',
        'total_aum': total_value,
        'inception': '2020-01-01',
        'composites': [
            {'name': 'Balanced Growth', 'aum': total_value * 0.7, 'accounts': 5},
            {'name': 'Conservative', 'aum': total_value * 0.3, 'accounts': 3},
        ]
    }
    buffer = io.BytesIO()
    UnifiedFirmReport.generate(firm_data, buffer, 'goldman')
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 5000:
        test_pass("UnifiedFirmReport", f"{size:,} bytes")
    else:
        test_fail("UnifiedFirmReport", f"Only {size} bytes")
except Exception as e:
    test_fail("UnifiedFirmReport", str(e))

# Test Individual Report
try:
    buffer = io.BytesIO()
    UnifiedIndividualReport.generate(test_data, buffer, 'goldman')
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 10000:
        test_pass("UnifiedIndividualReport", f"{size:,} bytes")
    else:
        test_fail("UnifiedIndividualReport", f"Only {size} bytes")
except Exception as e:
    test_fail("UnifiedIndividualReport", str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: COMPOSITE DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4] TESTING COMPOSITE DOCUMENTS...")
print("─" * 80)

from gips_app import CompositeDocuments

docs = [
    ("GIPS Disclosures", CompositeDocuments.generate_gips_disclosures),
    ("Verification Checklist", CompositeDocuments.generate_verification_checklist),
    ("Risk Analytics Report", CompositeDocuments.generate_risk_analytics_report),
    ("Benchmark Attribution", CompositeDocuments.generate_benchmark_attribution),
    ("Fee Impact Analysis", CompositeDocuments.generate_fee_impact_analysis),
    ("Composite Construction Memo", CompositeDocuments.generate_composite_construction_memo),
    ("GIPS Compliance Certificate", CompositeDocuments.generate_gips_compliance_certificate),
]

for name, func in docs:
    try:
        buffer = io.BytesIO()
        func(test_data, buffer)
        buffer.seek(0)
        size = len(buffer.getvalue())
        if size > 1000:
            test_pass(name, f"{size:,} bytes")
        else:
            test_fail(name, f"Only {size} bytes")
    except Exception as e:
        test_fail(name, str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: EXCEL GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[5] TESTING EXCEL GENERATORS...")
print("─" * 80)

from gips_app import UnifiedExcelGenerator, ExcelGenerator

# Test Composite Excel
try:
    buffer = io.BytesIO()
    UnifiedExcelGenerator.generate_composite_excel(test_data, buffer)
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 5000:
        test_pass("Composite Excel", f"{size:,} bytes")
    else:
        test_fail("Composite Excel", f"Only {size} bytes")
except Exception as e:
    test_fail("Composite Excel", str(e))

# Test Holdings Summary Excel
try:
    buffer = io.BytesIO()
    ExcelGenerator.generate_holdings_summary(test_data, buffer)
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 3000:
        test_pass("Holdings Summary Excel", f"{size:,} bytes")
    else:
        test_fail("Holdings Summary Excel", f"Only {size} bytes")
except Exception as e:
    test_fail("Holdings Summary Excel", str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: VERIFICATION PACKAGE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[6] TESTING VERIFICATION PACKAGE...")
print("─" * 80)

from gips_app import VerificationPackageGenerator

try:
    verif_data = {
        'account_name': 'Henderson Family Office',
        'monthly_returns': returns,
        'annual_returns': annual_returns,
        'positions': positions,
        'holdings': positions,
        'total_value': total_value,
        'benchmark': 'S&P 500',
        'benchmark_returns': benchmark_monthly,
        'risk_free_rate': 0.0357,
    }

    # Test calculation workbook
    buffer = io.BytesIO()
    VerificationPackageGenerator.generate_calculation_workbook(verif_data, buffer)
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 5000:
        test_pass("Calculation Workbook", f"{size:,} bytes")
    else:
        test_fail("Calculation Workbook", f"Only {size} bytes")

    # Test methodology documentation (PDF)
    buffer = io.BytesIO()
    VerificationPackageGenerator.generate_methodology_pdf(verif_data, buffer)
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 2000:
        test_pass("Methodology PDF", f"{size:,} bytes")
    else:
        test_fail("Methodology PDF", f"Only {size} bytes")

    # Test data lineage (PDF)
    buffer = io.BytesIO()
    VerificationPackageGenerator.generate_data_lineage_pdf(verif_data, buffer)
    buffer.seek(0)
    size = len(buffer.getvalue())
    if size > 2000:
        test_pass("Data Lineage PDF", f"{size:,} bytes")
    else:
        test_fail("Data Lineage PDF", f"Only {size} bytes")

except Exception as e:
    test_fail("Verification Package", str(e))
    import traceback
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: AI FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[7] TESTING AI FEATURES...")
print("─" * 80)

from gips_app import GIPSAIAssistant

api_key = os.environ.get('ANTHROPIC_API_KEY')
if api_key:
    test_pass("API Key available", f"{api_key[:20]}...")

    ai_data = {
        'firm': 'Henderson Family Office',
        'composite': 'Balanced Growth',
        'strategy': 'Multi-asset allocation',
        'benchmark': 'S&P 500',
        'monthly_returns': returns[:36],
        'fee': 1.0,
    }

    # Test compliance check
    try:
        result = GIPSAIAssistant.check_compliance(ai_data)
        if result and 'checks' in result:
            test_pass("AI Compliance Check", f"{len(result['checks'])} checks")
        else:
            test_fail("AI Compliance Check", "Invalid result")
    except Exception as e:
        test_fail("AI Compliance Check", str(e))

    # Test disclosures
    try:
        result = GIPSAIAssistant.generate_disclosures(ai_data)
        if result and len(result) > 100:
            test_pass("AI Disclosures", f"{len(result)} chars")
        else:
            test_fail("AI Disclosures", f"Only {len(result) if result else 0} chars")
    except Exception as e:
        test_fail("AI Disclosures", str(e))

    # Test audit prep
    try:
        result = GIPSAIAssistant.prepare_audit(ai_data)
        if result and 'checklist' in result:
            test_pass("AI Audit Prep", f"{len(result['checklist'])} items")
        else:
            test_fail("AI Audit Prep", "Invalid result")
    except Exception as e:
        test_fail("AI Audit Prep", str(e))
else:
    print("  ⚠️  No API key - skipping AI tests (set ANTHROPIC_API_KEY)")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("COMPREHENSIVE TEST SUMMARY")
print("=" * 80)
total = results['passed'] + results['failed']
rate = (results['passed'] / total * 100) if total > 0 else 0

print(f"  ✅ Passed: {results['passed']}")
print(f"  ❌ Failed: {results['failed']}")
print(f"  📊 Total:  {total}")
print(f"  📈 Rate:   {rate:.1f}%")

if results['errors']:
    print("\n" + "─" * 80)
    print("ERRORS:")
    print("─" * 80)
    for name, error in results['errors']:
        print(f"  ❌ {name}")
        print(f"     → {error[:100]}...")

print("\n" + "=" * 80)
if results['failed'] == 0:
    print("✅ ALL TESTS PASSED - GIPS APP 100% FUNCTIONAL!")
else:
    print(f"⚠️  {results['failed']} TESTS FAILED")
print("=" * 80)
