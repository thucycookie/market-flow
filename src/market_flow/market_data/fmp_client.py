"""
Financial Modeling Prep (FMP) Client

Wrapper around the FMP API for fetching financial data.
Uses the stable API endpoints (not legacy v3).
"""

import os
from typing import Literal

import requests


FMP_BASE_URL = "https://financialmodelingprep.com/stable"


def _get_api_key() -> str:
    """Get the FMP API key from environment."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        raise ValueError(
            "FMP_API_KEY environment variable is required. "
            "Get your API key from https://financialmodelingprep.com/"
        )
    return api_key


def _make_request(endpoint: str, params: dict | None = None) -> dict | list:
    """Make a request to the FMP stable API."""
    api_key = _get_api_key()

    params = params or {}
    params["apikey"] = api_key

    url = f"{FMP_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict) and "Error Message" in data:
        raise ValueError(f"FMP API Error: {data['Error Message']}")

    return data


def get_company_profile(ticker: str) -> dict:
    """
    Get company profile information.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "HOOD")

    Returns:
        dict with company info including:
        - companyName, symbol, exchange, industry, sector
        - marketCap, price, beta
        - description, ceo, fullTimeEmployees
        - website, country, city
    """
    data = _make_request("profile", params={"symbol": ticker.upper()})
    if not data:
        raise ValueError(f"No profile found for ticker: {ticker}")
    return data[0] if isinstance(data, list) else data


def get_income_statement(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get income statement data.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of income statements with:
        - revenue, costOfRevenue, grossProfit
        - operatingIncome, netIncome, ebitda
        - eps, epsdiluted
        - date, period, calendarYear
    """
    data = _make_request(
        "income-statement",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_balance_sheet(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get balance sheet data.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of balance sheets with:
        - totalAssets, totalLiabilities, totalStockholdersEquity
        - totalDebt, netDebt, cashAndCashEquivalents
        - totalCurrentAssets, totalCurrentLiabilities
        - date, period, calendarYear
    """
    data = _make_request(
        "balance-sheet-statement",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_cash_flow(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get cash flow statement data.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of cash flow statements with:
        - operatingCashFlow, capitalExpenditure, freeCashFlow
        - netCashUsedForInvestingActivites
        - netCashUsedProvidedByFinancingActivities
        - netChangeInCash
        - date, period, calendarYear
    """
    data = _make_request(
        "cash-flow-statement",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_financial_ratios(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get financial ratios.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of ratio data with:
        - currentRatio, quickRatio
        - debtRatio, debtEquityRatio
        - returnOnEquity, returnOnAssets
        - grossProfitMargin, operatingProfitMargin, netProfitMargin
        - priceEarningsRatio, priceToBookRatio
        - date, period
    """
    data = _make_request(
        "ratios",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_ratios_ttm(ticker: str) -> dict:
    """
    Get trailing twelve months (TTM) financial ratios.

    Unlike get_financial_ratios() which returns historical periods,
    this returns the most recent TTM ratios for real-time analysis.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSM")

    Returns:
        dict with TTM ratios including:
        - debtToAssetsRatioTTM, debtToEquityRatioTTM, debtToCapitalRatioTTM (leverage)
        - currentRatioTTM, quickRatioTTM, cashRatioTTM (liquidity)
        - grossProfitMarginTTM, netProfitMarginTTM, operatingProfitMarginTTM
        - priceToEarningsRatioTTM, priceToBookRatioTTM, priceToSalesRatioTTM
        - dividendYieldTTM, dividendPayoutRatioTTM
        - assetTurnoverTTM, inventoryTurnoverTTM, receivablesTurnoverTTM
        - effectiveTaxRateTTM, financialLeverageRatioTTM
    """
    data = _make_request("ratios-ttm", params={"symbol": ticker.upper()})
    if not data:
        raise ValueError(f"No TTM ratios found for ticker: {ticker}")
    return data[0] if isinstance(data, list) else data


def get_key_metrics(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get key financial metrics including valuation metrics.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of key metrics with:
        - revenuePerShare, netIncomePerShare, freeCashFlowPerShare
        - marketCap, enterpriseValue
        - peRatio, pbRatio, evToSales, evToEBITDA
        - roic, roe, roa
        - date, period
    """
    data = _make_request(
        "key-metrics",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_earnings_history(ticker: str, limit: int = 20) -> list[dict]:
    """
    Get historical earnings data.

    Args:
        ticker: Stock ticker symbol
        limit: Number of earnings reports to retrieve

    Returns:
        List of earnings data with:
        - date, symbol
        - eps, epsEstimated
        - revenue, revenueEstimated
        - epsSurprise, epsSurprisePercent (calculated if available)
    """
    data = _make_request(
        "earnings",
        params={"symbol": ticker.upper(), "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_quote(ticker: str) -> dict:
    """
    Get real-time stock quote.

    Args:
        ticker: Stock ticker symbol

    Returns:
        dict with:
        - price, changesPercentage, change
        - volume, avgVolume
        - marketCap, pe, eps
        - yearHigh, yearLow
        - sharesOutstanding
    """
    data = _make_request("quote", params={"symbol": ticker.upper()})
    if not data:
        raise ValueError(f"No quote found for ticker: {ticker}")
    return data[0] if isinstance(data, list) else data


def get_dcf(ticker: str) -> dict:
    """
    Get FMP's DCF valuation for a company.

    Args:
        ticker: Stock ticker symbol

    Returns:
        dict with:
        - symbol, date
        - dcf (intrinsic value per share)
        - Stock Price
    """
    data = _make_request("discounted-cash-flow", params={"symbol": ticker.upper()})
    if not data:
        raise ValueError(f"No DCF data found for ticker: {ticker}")
    return data[0] if isinstance(data, list) else data


def get_analyst_estimates(
    ticker: str,
    period: Literal["annual", "quarter"] = "annual",
    limit: int = 5,
) -> list[dict]:
    """
    Get analyst estimates for future earnings.

    Args:
        ticker: Stock ticker symbol
        period: "annual" or "quarter"
        limit: Number of periods to retrieve

    Returns:
        List of estimates with:
        - estimatedRevenueAvg, estimatedRevenueHigh, estimatedRevenueLow
        - estimatedEpsAvg, estimatedEpsHigh, estimatedEpsLow
        - numberAnalystsEstimatedRevenue, numberAnalystEstimatedEps
        - date
    """
    data = _make_request(
        "analyst-estimates",
        params={"symbol": ticker.upper(), "period": period, "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def get_custom_dcf(
    ticker: str,
    revenue_growth_pct: float | None = None,
    ebitda_pct: float | None = None,
    depreciation_and_amortization_pct: float | None = None,
    cash_and_short_term_investments_pct: float | None = None,
    receivables_pct: float | None = None,
    inventories_pct: float | None = None,
    payable_pct: float | None = None,
    ebit_pct: float | None = None,
    capital_expenditure_pct: float | None = None,
    operating_cash_flow_pct: float | None = None,
    sg_and_a_pct: float | None = None,
    tax_rate: float | None = None,
    long_term_growth_rate: float | None = None,
    cost_of_debt: float | None = None,
    cost_of_equity: float | None = None,
    market_risk_premium: float | None = None,
    beta: float | None = None,
    risk_free_rate: float | None = None,
) -> dict:
    """
    Get custom DCF valuation with fine-tuned assumptions.

    Uses FMP's Custom DCF Advanced API to calculate intrinsic value
    with user-specified parameters. Any parameter not provided uses
    FMP's default calculations.

    Args:
        ticker: Stock ticker symbol
        revenue_growth_pct: Annual revenue growth rate (e.g., 10.0 for 10%)
        ebitda_pct: EBITDA margin as % of revenue
        depreciation_and_amortization_pct: D&A as % of revenue
        cash_and_short_term_investments_pct: Cash as % of revenue
        receivables_pct: AR as % of revenue
        inventories_pct: Inventory as % of revenue
        payable_pct: AP as % of revenue
        ebit_pct: EBIT margin as % of revenue
        capital_expenditure_pct: CapEx as % of revenue
        operating_cash_flow_pct: OCF as % of revenue
        sg_and_a_pct: SG&A as % of revenue
        tax_rate: Corporate tax rate (e.g., 0.21 for 21%)
        long_term_growth_rate: Terminal growth rate (e.g., 2.5 for 2.5%)
        cost_of_debt: Interest rate on debt %
        cost_of_equity: Required return on equity %
        market_risk_premium: Market risk premium %
        beta: Stock beta coefficient
        risk_free_rate: Risk-free rate %

    Returns:
        dict with DCF valuation results including:
        - equity_value, equity_value_per_share
        - free_cash_flow, terminal_value
        - enterprise_value, wacc
    """
    params = {"symbol": ticker.upper()}

    # Map Python snake_case to FMP camelCase parameters
    param_mapping = {
        "revenueGrowthPct": revenue_growth_pct,
        "ebitdaPct": ebitda_pct,
        "depreciationAndAmortizationPct": depreciation_and_amortization_pct,
        "cashAndShortTermInvestmentsPct": cash_and_short_term_investments_pct,
        "receivablesPct": receivables_pct,
        "inventoriesPct": inventories_pct,
        "payablePct": payable_pct,
        "ebitPct": ebit_pct,
        "capitalExpenditurePct": capital_expenditure_pct,
        "operatingCashFlowPct": operating_cash_flow_pct,
        "sellingGeneralAndAdministrativeExpensesPct": sg_and_a_pct,
        "taxRate": tax_rate,
        "longTermGrowthRate": long_term_growth_rate,
        "costOfDebt": cost_of_debt,
        "costOfEquity": cost_of_equity,
        "marketRiskPremium": market_risk_premium,
        "beta": beta,
        "riskFreeRate": risk_free_rate,
    }

    # Only include parameters that are not None
    for key, value in param_mapping.items():
        if value is not None:
            params[key] = value

    data = _make_request("custom-discounted-cash-flow", params=params)
    if not data:
        raise ValueError(f"No custom DCF data found for ticker: {ticker}")
    return data[0] if isinstance(data, list) else data
