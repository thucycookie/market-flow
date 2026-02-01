#!/bin/bash
# Custom DCF Analysis Comparison Script
# Modify the TICKERS array below to analyze different stocks

# =============================================================================
# CONFIGURATION - Modify this array to change which stocks to analyze
# =============================================================================
TICKERS='["HOOD", "IREN", "AMZN", "NVDA", "TSM", "NFLX", "MU", "AAPL", "MSFT", "GOOGL", "META", "AVGO"]'
# =============================================================================

cd "$(dirname "$0")"
source venv/bin/activate

python -c "
import sys
sys.path.insert(0, 'src')
from dotenv import load_dotenv
load_dotenv()

from market_flow.agents.financial_tools import _run_custom_dcf_with_params
import json

tickers = $TICKERS
results = {}

print('Running Custom DCF Analysis...')
print('=' * 60)

for t in tickers:
    try:
        print(f'Fetching {t}...', end=' ', flush=True)
        results[t] = _run_custom_dcf_with_params(t)
        print('OK')
    except Exception as e:
        print(f'ERROR - {e}')
        results[t] = {'error': str(e)}

# Calculate upside for each
for t in tickers:
    if 'error' not in results[t]:
        price = results[t].get('price', 0)
        intrinsic = results[t].get('equityValuePerShare', 0)
        if price and price > 0:
            results[t]['upside'] = ((intrinsic - price) / price) * 100
        else:
            results[t]['upside'] = None

print()
col_width = max(16, 140 // len(tickers))
total_width = 24 + col_width * len(tickers)
print('=' * total_width)
print('CUSTOM DCF ANALYSIS - SIDE BY SIDE COMPARISON'.center(total_width))
print('=' * total_width)

def fmt(v, is_large=False):
    if v is None:
        return 'N/A'
    if is_large:
        if abs(v) >= 1e12:
            return f'\${v/1e12:.2f}T'
        elif abs(v) >= 1e9:
            return f'\${v/1e9:.1f}B'
        elif abs(v) >= 1e6:
            return f'\${v/1e6:.0f}M'
        else:
            return f'\${v:,.0f}'
    return f'{v:.2f}'

# Print header
print()
print(f'{\"Metric\":<24}', end='')
for t in tickers:
    print(f'{t:>{col_width}}', end='')
print()
print('-' * total_width)

# Valuation
print('VALUATION')
metrics = [
    ('price', 'Current Price', True),
    ('equityValuePerShare', 'Intrinsic Value', True),
    ('upside', 'Upside/Downside %', False),
    ('wacc', 'WACC', False),
    ('costOfEquity', 'Cost of Equity', False),
    ('beta', 'Beta', False),
]

for key, label, is_money in metrics:
    print(f'{label:<24}', end='')
    for t in tickers:
        if 'error' in results[t]:
            print(f'{\"ERROR\":>{col_width}}', end='')
        else:
            val = results[t].get(key)
            if key in ['wacc', 'costOfEquity', 'upside']:
                if val is not None:
                    if key == 'upside':
                        print(f'{val:>+{col_width-1}.1f}%', end='')
                    else:
                        print(f'{val:>{col_width-1}.2f}%', end='')
                else:
                    print(f'{\"N/A\":>{col_width}}', end='')
            elif is_money:
                print(f'\${val:>{col_width-1}.2f}', end='')
            else:
                print(f'{fmt(val):>{col_width}}', end='')
    print()

print()
print('CASH FLOWS & ENTERPRISE VALUE')
metrics2 = [
    ('ufcf', 'Unlevered FCF'),
    ('terminalValue', 'Terminal Value'),
    ('enterpriseValue', 'Enterprise Value'),
    ('equityValue', 'Equity Value'),
    ('netDebt', 'Net Debt'),
]

for key, label in metrics2:
    print(f'{label:<24}', end='')
    for t in tickers:
        if 'error' in results[t]:
            print(f'{\"ERROR\":>{col_width}}', end='')
        else:
            val = results[t].get(key)
            print(f'{fmt(val, is_large=True):>{col_width}}', end='')
    print()

print()
print('GROWTH & MARGINS')
metrics3 = [
    ('revenuePercentage', 'Revenue Growth %'),
    ('ebitdaPercentage', 'EBITDA Margin %'),
    ('ebitPercentage', 'EBIT Margin %'),
    ('longTermGrowthRate', 'Terminal Growth %'),
]

for key, label in metrics3:
    print(f'{label:<24}', end='')
    for t in tickers:
        if 'error' in results[t]:
            print(f'{\"ERROR\":>{col_width}}', end='')
        else:
            val = results[t].get(key)
            if val is not None:
                print(f'{val:>{col_width-1}.2f}%', end='')
            else:
                print(f'{\"N/A\":>{col_width}}', end='')
    print()

print()
print('=' * total_width)
print()
print('INVESTMENT SUMMARY')
print('-' * total_width)
print(f'{\"Ticker\":<10}{\"Price\":>12}{\"Intrinsic\":>14}{\"Upside\":>14}{\"Recommendation\":>18}{\"WACC\":>10}{\"Rev Growth\":>12}')
print('-' * total_width)

for t in tickers:
    if 'error' in results[t]:
        print(f'{t:<10}{\"ERROR\":>12}')
        continue
    price = results[t].get('price', 0)
    intrinsic = results[t].get('equityValuePerShare', 0)
    upside = results[t].get('upside', 0)
    wacc = results[t].get('wacc', 0)
    rev_growth = results[t].get('revenuePercentage', 0)

    if upside is None or upside < -50:
        rec = 'AVOID'
    elif upside > 50:
        rec = 'STRONG BUY'
    elif upside > 20:
        rec = 'BUY'
    elif upside > 0:
        rec = 'HOLD'
    elif upside > -20:
        rec = 'HOLD'
    else:
        rec = 'SELL'

    print(f'{t:<10}\${price:>10.2f}\${intrinsic:>12.2f}{upside:>+13.1f}%{rec:>18}{wacc:>9.2f}%{rev_growth:>11.2f}%')

print('=' * total_width)
print()
"
