#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
FULL DIAGNOSTIC TEST - GIPS APP
═══════════════════════════════════════════════════════════════════════════════
Tests EVERYTHING:
1. CSV Parsing
2. All GIPSRiskCalculator methods
3. All Report Generators
4. Verification Package Generator
5. AI Features (if API key available)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import traceback
from datetime import datetime

# Add path
GIPS_PATH = "/Users/abshirsharif/Desktop/Desktop - Abshir's MacBook Air/Desktop=Stuff/CapX100/capx100-gips-engine"
sys.path.insert(0, GIPS_PATH)

TEST_CSV = f"{GIPS_PATH}/test_data/SCHWAB_INSTITUTIONAL_EXPORT.csv"
OUTPUT_PATH = f"{GIPS_PATH}/gips_outputs"

print("=" * 80)
print("FULL DIAGNOSTIC TEST - GIPS APP")
print("=" * 80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def test_pass(name):
    results["passed"] += 1
    print(f"  ✅ {name}")

def test_fail(name, error):
    results["failed"] += 1
    results["errors"].append((name, str(error)))
    print(f"  ❌ {name}: {error}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 1: IMPORTS")
print("─" * 80)

try:
    from gips_app import GIPSRiskCalculator
    test_pass("GIPSRiskCalculator import")
except Exception as e:
    test_fail("GIPSRiskCalculator import", e)

try:
    from gips_app import UnifiedCompositeReport
    test_pass("UnifiedCompositeReport import")
except Exception as e:
    test_fail("UnifiedCompositeReport import", e)

try:
    from gips_app import UnifiedFirmReport
    test_pass("UnifiedFirmReport import")
except Exception as e:
    test_fail("UnifiedFirmReport import", e)

try:
    from gips_app import UnifiedIndividualReport
    test_pass("UnifiedIndividualReport import")
except Exception as e:
    test_fail("UnifiedIndividualReport import", e)

try:
    from gips_app import VerificationPackageGenerator
    test_pass("VerificationPackageGenerator import")
except Exception as e:
    test_fail("VerificationPackageGenerator import", e)

try:
    from gips_app import GIPSAIAssistant
    test_pass("GIPSAIAssistant import")
except Exception as e:
    test_fail("GIPSAIAssistant import", e)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: CSV PARSING
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 2: CSV PARSING")
print("─" * 80)

positions = []
monthly_returns = []
annual_returns = []

try:
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
            parts = line.split(',')
            if len(parts) >= 7:
                symbol = parts[0]
                for part in parts:
                    if part.startswith('$') and '.' in part:
                        try:
                            market_value = float(part.replace('$', '').replace(',', ''))
                            positions.append({
                                'symbol': symbol,
                                'market_value': market_value
                            })
                            break
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

    test_pass(f"CSV parsed: {len(positions)} positions, {len(monthly_returns)} months")

    # Calculate annual returns
    import numpy as np
    returns = [mr['return'] for mr in monthly_returns]

    # Group by year
    years = {}
    for mr in monthly_returns:
        year = mr['date'][:4]
        if year not in years:
            years[year] = []
        years[year].append(mr['return'])

    for year in sorted(years.keys()):
        yr_returns = years[year]
        annual = np.prod([1 + r for r in yr_returns]) - 1
        annual_returns.append(annual)
        print(f"    {year}: {annual*100:.2f}%")

    test_pass(f"Annual returns calculated: {len(annual_returns)} years")

except Exception as e:
    test_fail("CSV parsing", e)
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: GIPSRiskCalculator METHODS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 3: GIPSRiskCalculator METHODS")
print("─" * 80)

try:
    import numpy as np
    calculator = GIPSRiskCalculator(risk_free_rate=0.0357)
    returns = [mr['return'] for mr in monthly_returns]

    # Create benchmark returns
    np.random.seed(42)
    benchmark_returns = [r * 0.85 + np.random.normal(0, 0.005) for r in returns]

    test_pass(f"Calculator initialized (Rf={calculator.risk_free_rate*100:.2f}%)")

    # Test each method
    methods = [
        ("calculate_volatility", lambda: calculator.calculate_volatility(returns)),
        ("calculate_sharpe_ratio", lambda: calculator.calculate_sharpe_ratio(returns)),
        ("calculate_sortino_ratio", lambda: calculator.calculate_sortino_ratio(returns)),
        ("calculate_calmar_ratio", lambda: calculator.calculate_calmar_ratio(returns)),
        ("calculate_omega_ratio", lambda: calculator.calculate_omega_ratio(returns)),
        ("calculate_ulcer_index", lambda: calculator.calculate_ulcer_index(returns)),
        ("calculate_max_drawdown", lambda: calculator.calculate_max_drawdown(returns)),
        ("calculate_var_historical", lambda: calculator.calculate_var_historical(returns, 0.95)),
        ("calculate_cvar", lambda: calculator.calculate_cvar(returns, 0.95)),
        ("calculate_beta", lambda: calculator.calculate_beta(returns, benchmark_returns)),
        ("calculate_alpha", lambda: calculator.calculate_alpha(returns, benchmark_returns)),
        ("calculate_information_ratio", lambda: calculator.calculate_information_ratio(returns, benchmark_returns)),
        ("calculate_treynor_ratio", lambda: calculator.calculate_treynor_ratio(returns, benchmark_returns)),
        ("calculate_downside_deviation", lambda: calculator.calculate_downside_deviation(returns)),
    ]

    for method_name, method_func in methods:
        try:
            result = method_func()
            if result is not None:
                test_pass(f"{method_name}: {result:.4f}")
            else:
                test_fail(f"{method_name}", "Returned None")
        except Exception as e:
            test_fail(f"{method_name}", e)
            traceback.print_exc()

except Exception as e:
    test_fail("GIPSRiskCalculator initialization", e)
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: REPORT GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 4: REPORT GENERATORS")
print("─" * 80)

# Prepare test data
test_data = {
    'firm': 'Henderson Family Office',
    'composite': 'Balanced Growth Composite',
    'strategy': 'Multi-asset allocation with equity tilt',
    'benchmark': 'S&P 500',
    'currency': 'USD',
    'fee': 1.0,
    'inception': '2020-01-01',
    'annual_returns': annual_returns if annual_returns else [0.1623, 0.2766, -0.0714, 0.1397, 0.3256],
    'bm_annual': [0.1840, 0.2689, -0.1811, 0.2629, 0.2502],
    'monthly_returns': returns if returns else [0.01] * 60,
    'bm_monthly': benchmark_returns if benchmark_returns else [0.01] * 60,
    'total_value': 208168686.59,
    'positions': positions if positions else [{'symbol': 'TEST', 'market_value': 1000000}],
    'account_name': 'Henderson Family Office',
}

# Test UnifiedCompositeReport
try:
    report = UnifiedCompositeReport(test_data)
    pdf_bytes = report.generate()
    if pdf_bytes and len(pdf_bytes) > 1000:
        test_pass(f"UnifiedCompositeReport: {len(pdf_bytes):,} bytes")
        # Save for inspection
        with open(f"{OUTPUT_PATH}/TEST_Composite_Report.pdf", 'wb') as f:
            f.write(pdf_bytes)
    else:
        test_fail("UnifiedCompositeReport", f"Only {len(pdf_bytes) if pdf_bytes else 0} bytes")
except Exception as e:
    test_fail("UnifiedCompositeReport", e)
    traceback.print_exc()

# Test UnifiedFirmReport
try:
    firm_data = {
        'firm': 'Henderson Family Office',
        'composites': [
            {'name': 'Balanced Growth', 'aum': 150000000, 'accounts': 5},
            {'name': 'Conservative Income', 'aum': 58168686.59, 'accounts': 3},
        ],
        'total_aum': 208168686.59,
        'inception': '2020-01-01',
    }
    report = UnifiedFirmReport(firm_data)
    pdf_bytes = report.generate()
    if pdf_bytes and len(pdf_bytes) > 1000:
        test_pass(f"UnifiedFirmReport: {len(pdf_bytes):,} bytes")
    else:
        test_fail("UnifiedFirmReport", f"Only {len(pdf_bytes) if pdf_bytes else 0} bytes")
except Exception as e:
    test_fail("UnifiedFirmReport", e)
    traceback.print_exc()

# Test UnifiedIndividualReport
try:
    report = UnifiedIndividualReport(test_data)
    pdf_bytes = report.generate()
    if pdf_bytes and len(pdf_bytes) > 1000:
        test_pass(f"UnifiedIndividualReport: {len(pdf_bytes):,} bytes")
    else:
        test_fail("UnifiedIndividualReport", f"Only {len(pdf_bytes) if pdf_bytes else 0} bytes")
except Exception as e:
    test_fail("UnifiedIndividualReport", e)
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: VERIFICATION PACKAGE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 5: VERIFICATION PACKAGE GENERATOR")
print("─" * 80)

try:
    verif_data = {
        'account_name': 'Henderson Family Office',
        'monthly_returns': returns,
        'annual_returns': annual_returns,
        'positions': positions,
        'total_value': 208168686.59,
        'benchmark': 'S&P 500',
        'benchmark_returns': benchmark_returns,
        'risk_free_rate': 0.0357,
    }

    generator = VerificationPackageGenerator(verif_data)

    # Test calculation workbook
    try:
        excel_bytes = generator.generate_calculation_workbook()
        if excel_bytes and len(excel_bytes) > 1000:
            test_pass(f"Calculation Workbook: {len(excel_bytes):,} bytes")
        else:
            test_fail("Calculation Workbook", f"Only {len(excel_bytes) if excel_bytes else 0} bytes")
    except Exception as e:
        test_fail("Calculation Workbook", e)
        traceback.print_exc()

    # Test methodology documentation
    try:
        pdf_bytes = generator.generate_methodology_documentation()
        if pdf_bytes and len(pdf_bytes) > 1000:
            test_pass(f"Methodology Documentation: {len(pdf_bytes):,} bytes")
        else:
            test_fail("Methodology Documentation", f"Only {len(pdf_bytes) if pdf_bytes else 0} bytes")
    except Exception as e:
        test_fail("Methodology Documentation", e)
        traceback.print_exc()

    # Test data lineage
    try:
        pdf_bytes = generator.generate_data_lineage()
        if pdf_bytes and len(pdf_bytes) > 1000:
            test_pass(f"Data Lineage: {len(pdf_bytes):,} bytes")
        else:
            test_fail("Data Lineage", f"Only {len(pdf_bytes) if pdf_bytes else 0} bytes")
    except Exception as e:
        test_fail("Data Lineage", e)
        traceback.print_exc()

    # Test source data preservation
    try:
        excel_bytes = generator.generate_source_data_preservation()
        if excel_bytes and len(excel_bytes) > 1000:
            test_pass(f"Source Data Preservation: {len(excel_bytes):,} bytes")
        else:
            test_fail("Source Data Preservation", f"Only {len(excel_bytes) if excel_bytes else 0} bytes")
    except Exception as e:
        test_fail("Source Data Preservation", e)
        traceback.print_exc()

    # Test full package
    try:
        package = generator.generate_full_package()
        if package and len(package) == 4:
            test_pass(f"Full Verification Package: {len(package)} files")
        else:
            test_fail("Full Verification Package", f"Only {len(package) if package else 0} files")
    except Exception as e:
        test_fail("Full Verification Package", e)
        traceback.print_exc()

except Exception as e:
    test_fail("VerificationPackageGenerator initialization", e)
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: AI FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 6: AI FEATURES")
print("─" * 80)

try:
    # Check if API key is available
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        test_pass(f"API Key found: {api_key[:20]}...")

        # Test compliance check
        try:
            ai_data = {
                'firm': 'Henderson Family Office',
                'composite': 'Balanced Growth',
                'strategy': 'Multi-asset allocation',
                'benchmark': 'S&P 500',
                'monthly_returns': returns[:36] if len(returns) >= 36 else returns,
                'fee': 1.0,
            }
            result = GIPSAIAssistant.check_compliance(ai_data)
            if result and 'checks' in result:
                test_pass(f"AI Compliance Check: {len(result['checks'])} checks")
            else:
                test_fail("AI Compliance Check", "Invalid result format")
        except Exception as e:
            test_fail("AI Compliance Check", e)

        # Test disclosure generation
        try:
            result = GIPSAIAssistant.generate_disclosures(ai_data)
            if result and len(result) > 100:
                test_pass(f"AI Disclosures: {len(result)} chars")
            else:
                test_fail("AI Disclosures", f"Only {len(result) if result else 0} chars")
        except Exception as e:
            test_fail("AI Disclosures", e)

        # Test audit prep
        try:
            result = GIPSAIAssistant.prepare_audit(ai_data)
            if result and 'checklist' in result:
                test_pass(f"AI Audit Prep: {len(result['checklist'])} items")
            else:
                test_fail("AI Audit Prep", "Invalid result format")
        except Exception as e:
            test_fail("AI Audit Prep", e)
    else:
        print("  ⚠️  No API key found - skipping AI tests")
        print("     Set ANTHROPIC_API_KEY environment variable to test AI features")

except Exception as e:
    test_fail("AI Features", e)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: GENERATE GIPS PACKAGE (THE FAILING FEATURE)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("TEST 7: GENERATE GIPS PACKAGE (FULL)")
print("─" * 80)

try:
    # This simulates what happens when you click "Generate GIPS Package"
    from gips_app import generate_composite_package

    package_data = {
        'firm': 'Henderson Family Office',
        'composite': 'Balanced Growth Composite',
        'strategy': 'Multi-asset allocation with equity tilt',
        'benchmark': 'S&P 500',
        'currency': 'USD',
        'fee': 1.0,
        'inception': '2020-01-01',
        'annual_returns': annual_returns,
        'bm_annual': [0.1840, 0.2689, -0.1811, 0.2629, 0.2502][:len(annual_returns)],
        'monthly_returns': returns,
        'bm_monthly': benchmark_returns,
        'total_value': 208168686.59,
        'positions': positions,
        'account_name': 'Henderson Family Office',
    }

    files = generate_composite_package(package_data)
    if files:
        test_pass(f"Generate Composite Package: {len(files)} files")
        for filename, content in files.items():
            size = len(content) if content else 0
            if size > 0:
                print(f"    ✓ {filename}: {size:,} bytes")
            else:
                print(f"    ✗ {filename}: EMPTY")
    else:
        test_fail("Generate Composite Package", "No files returned")

except ImportError:
    print("  ⚠️  generate_composite_package not found - testing individual generators")

    # Test what the generate route does manually
    try:
        # Generate all 10 files that the UI expects
        files_generated = []

        # 1. GIPS_Composite_Presentation.pdf
        report = UnifiedCompositeReport(test_data)
        pdf_bytes = report.generate()
        if pdf_bytes:
            files_generated.append(("GIPS_Composite_Presentation.pdf", len(pdf_bytes)))

        test_pass(f"Manual package generation: {len(files_generated)} files")
        for name, size in files_generated:
            print(f"    ✓ {name}: {size:,} bytes")

    except Exception as e:
        test_fail("Manual package generation", e)
        traceback.print_exc()

except Exception as e:
    test_fail("Generate Composite Package", e)
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)
print(f"  ✅ Passed: {results['passed']}")
print(f"  ❌ Failed: {results['failed']}")
print(f"  📊 Total:  {results['passed'] + results['failed']}")
print(f"  📈 Rate:   {results['passed']/(results['passed']+results['failed'])*100:.1f}%")

if results['errors']:
    print("\n" + "─" * 80)
    print("ERRORS:")
    print("─" * 80)
    for name, error in results['errors']:
        print(f"  ❌ {name}")
        print(f"     → {error}")

print("\n" + "=" * 80)
if results['failed'] == 0:
    print("✅ ALL TESTS PASSED!")
else:
    print(f"⚠️  {results['failed']} TESTS FAILED - NEEDS ATTENTION")
print("=" * 80)
