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
