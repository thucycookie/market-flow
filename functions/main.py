"""
Cloud Function: Daily DCF Analysis Pipeline

Fetches custom DCF data from FMP API for configured tickers
with auto-calculated parameters from historical data,
and writes results to Firestore.
"""

import os
from datetime import datetime, timezone

import requests
from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn, scheduler_fn
from firebase_functions.options import set_global_options

set_global_options(max_instances=3, region="us-east1")

app = initialize_app()

# =============================================================================
# Configuration
# =============================================================================
TICKERS = [
    "HOOD", "IREN", "AMZN", "NVDA", "TSM",
    "NFLX", "MU", "AAPL", "MSFT", "GOOGL", "META", "AVGO",
]

FMP_BASE_URL = "https://financialmodelingprep.com/stable"

# Damodaran country equity risk premiums
COUNTRY_EQUITY_RISK_PREMIUMS = {
    "United States": 4.46,
    "Canada": 4.23,
    "United Kingdom": 5.01,
    "Germany": 4.23,
    "France": 5.01,
    "Japan": 5.14,
    "China": 5.14,
    "Taiwan": 5.01,
    "Korea": 4.87,
    "India": 7.08,
    "Brazil": 7.47,
    "Australia": 4.23,
    "Singapore": 4.23,
    "Hong Kong": 5.01,
    "Netherlands": 4.23,
    "Switzerland": 4.23,
    "Sweden": 4.23,
    "Norway": 4.23,
    "Denmark": 4.23,
    "Finland": 4.59,
    "Ireland": 5.01,
    "Israel": 6.30,
    "Mexico": 6.69,
    "South Africa": 8.13,
    "Russia": 8.13,
    "Turkey": 10.06,
    "Argentina": 13.94,
    "Indonesia": 6.69,
    "Malaysia": 5.78,
    "Thailand": 6.30,
    "Philippines": 6.69,
    "Vietnam": 8.13,
}

# Long-term GDP growth estimates by country
COUNTRY_GDP_GROWTH = {
    "United States": 2.5,
    "Canada": 2.0,
    "United Kingdom": 1.5,
    "Germany": 1.5,
    "France": 1.5,
    "Japan": 1.0,
    "China": 4.0,
    "Taiwan": 2.5,
    "Korea": 2.5,
    "India": 5.0,
    "Brazil": 2.5,
    "Australia": 2.5,
    "Singapore": 2.5,
    "Hong Kong": 2.5,
    "Netherlands": 1.5,
    "Switzerland": 1.5,
    "Sweden": 2.0,
    "Norway": 2.0,
    "Denmark": 2.0,
    "Finland": 1.5,
    "Ireland": 2.5,
    "Israel": 3.0,
    "Mexico": 2.5,
    "Indonesia": 4.5,
    "Malaysia": 4.0,
    "Thailand": 3.5,
    "Philippines": 5.0,
    "Vietnam": 5.5,
    "Developed": 2.0,
    "Emerging": 4.5,
}


# =============================================================================
# FMP API helpers
# =============================================================================

def _fmp_request(endpoint: str, params: dict | None = None) -> dict | list:
    """Make a request to the FMP stable API."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        raise ValueError("FMP_API_KEY environment variable is required")

    params = params or {}
    params["apikey"] = api_key

    url = f"{FMP_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    if isinstance(data, dict) and "Error Message" in data:
        raise ValueError(f"FMP API Error: {data['Error Message']}")
    return data


def _get_company_profile(ticker: str) -> dict:
    data = _fmp_request("profile", params={"symbol": ticker.upper()})
    if not data:
        raise ValueError(f"No profile for {ticker}")
    return data[0] if isinstance(data, list) else data


def _get_income_statements(ticker: str, limit: int = 5) -> list[dict]:
    data = _fmp_request(
        "income-statement",
        params={"symbol": ticker.upper(), "period": "annual", "limit": limit},
    )
    return data if isinstance(data, list) else [data]


def _get_cash_flows(ticker: str, limit: int = 5) -> list[dict]:
    data = _fmp_request(
        "cash-flow-statement",
        params={"symbol": ticker.upper(), "period": "annual", "limit": limit},
    )
    return data if isinstance(data, list) else [data]


# =============================================================================
# DCF parameter calculations
# =============================================================================

def _calculate_revenue_growth_pct(income_stmts: list[dict], periods: int = 5) -> float:
    """5-year revenue CAGR as percentage (e.g. 24.78 for 24.78%)."""
    stmts = income_stmts[:periods]
    revenues = [s.get("revenue", 0) for s in reversed(stmts)]
    revenues = [r for r in revenues if r and r > 0]
    if len(revenues) < 2:
        return 5.0
    years = len(revenues) - 1
    cagr = (revenues[-1] / revenues[0]) ** (1 / years) - 1
    return round(cagr * 100, 2)


def _calculate_capex_pct(cash_flows: list[dict], income_stmts: list[dict], periods: int = 5) -> float:
    """Average CapEx/Revenue as percentage (e.g. 5.2 for 5.2%)."""
    pcts = []
    for i in range(min(periods, len(cash_flows), len(income_stmts))):
        capex = abs(cash_flows[i].get("capitalExpenditure", 0) or 0)
        revenue = income_stmts[i].get("revenue", 0) or 0
        if revenue > 0:
            pcts.append(capex / revenue)
    if not pcts:
        return 5.0
    return round(sum(pcts) / len(pcts) * 100, 2)


def _calculate_ocf_pct(cash_flows: list[dict], income_stmts: list[dict], periods: int = 5) -> float:
    """Average OCF/Revenue as percentage (e.g. 25.0 for 25%)."""
    pcts = []
    for i in range(min(periods, len(cash_flows), len(income_stmts))):
        ocf = cash_flows[i].get("operatingCashFlow", 0) or 0
        revenue = income_stmts[i].get("revenue", 0) or 0
        if revenue > 0:
            pcts.append(ocf / revenue)
    if not pcts:
        return 15.0
    return round(sum(pcts) / len(pcts) * 100, 2)


def _get_market_risk_premium(country: str) -> float:
    """Damodaran equity risk premium lookup. Returns e.g. 4.46 for US."""
    if country in COUNTRY_EQUITY_RISK_PREMIUMS:
        return COUNTRY_EQUITY_RISK_PREMIUMS[country]
    country_lower = country.lower()
    for key, value in COUNTRY_EQUITY_RISK_PREMIUMS.items():
        if key.lower() == country_lower:
            return value
    return COUNTRY_EQUITY_RISK_PREMIUMS["United States"]


def _get_long_term_growth_rate(country: str) -> float:
    """GDP growth estimate lookup. Returns e.g. 2.5 for US."""
    if country in COUNTRY_GDP_GROWTH:
        return COUNTRY_GDP_GROWTH[country]
    country_lower = country.lower()
    for key, value in COUNTRY_GDP_GROWTH.items():
        if key.lower() == country_lower:
            return value
    return COUNTRY_GDP_GROWTH["United States"]


def _get_custom_dcf_with_params(ticker: str) -> dict:
    """
    Fetch custom DCF with auto-calculated parameters from historical data.

    Calculates revenue growth, CapEx %, OCF %, market risk premium, and
    long-term growth rate, then passes them to FMP's Custom DCF API.
    """
    # Fetch historical data
    profile = _get_company_profile(ticker)
    income_stmts = _get_income_statements(ticker, limit=5)
    cash_flows = _get_cash_flows(ticker, limit=5)

    country = profile.get("country", "United States") or "United States"

    # Calculate parameters (human-readable percentages)
    revenue_growth_pct = _calculate_revenue_growth_pct(income_stmts)
    capital_expenditure_pct = _calculate_capex_pct(cash_flows, income_stmts)
    operating_cash_flow_pct = _calculate_ocf_pct(cash_flows, income_stmts)
    market_risk_premium = _get_market_risk_premium(country)
    long_term_growth_rate = _get_long_term_growth_rate(country)

    # Store original values for transparency
    parameters_used = {
        "revenue_growth_pct": revenue_growth_pct,
        "capital_expenditure_pct": capital_expenditure_pct,
        "operating_cash_flow_pct": operating_cash_flow_pct,
        "market_risk_premium": market_risk_premium,
        "long_term_growth_rate": long_term_growth_rate,
        "country": country,
    }

    # FMP API format conversion:
    # - "Pct" params expect DECIMALS (0.2478 for 24.78%)
    # - marketRiskPremium, longTermGrowthRate expect ACTUAL % (4.46 for 4.46%)
    params = {
        "symbol": ticker.upper(),
        "revenueGrowthPct": revenue_growth_pct / 100,
        "capitalExpenditurePct": capital_expenditure_pct / 100,
        "operatingCashFlowPct": operating_cash_flow_pct / 100,
        "marketRiskPremium": market_risk_premium,
        "longTermGrowthRate": long_term_growth_rate,
    }

    data = _fmp_request("custom-discounted-cash-flow", params=params)
    if not data:
        raise ValueError(f"No custom DCF data for {ticker}")
    result = data[0] if isinstance(data, list) else data
    result["parameters_used"] = parameters_used
    return result


# =============================================================================
# Business logic
# =============================================================================

def _get_recommendation(upside: float | None) -> str:
    if upside is None or upside < -50:
        return "AVOID"
    if upside > 50:
        return "STRONG BUY"
    if upside > 20:
        return "BUY"
    if upside > 0:
        return "HOLD"
    if upside > -20:
        return "HOLD"
    return "SELL"


def _run_analysis(tickers: list[str]) -> dict:
    """Run DCF analysis for all tickers and return results + errors."""
    results = {}
    errors = {}

    for ticker in tickers:
        try:
            raw = _get_custom_dcf_with_params(ticker)

            price = raw.get("price", 0) or 0
            intrinsic = raw.get("equityValuePerShare", 0) or 0
            wacc = raw.get("wacc", 0) or 0
            rev_growth = raw.get("revenuePercentage", 0) or 0

            upside = (
                ((intrinsic - price) / price) * 100
                if price and price > 0
                else None
            )

            results[ticker] = {
                "ticker": ticker,
                "price": round(price, 2),
                "intrinsic": round(intrinsic, 2),
                "upside": round(upside, 2) if upside is not None else None,
                "recommendation": _get_recommendation(upside),
                "wacc": round(wacc, 4),
                "rev_growth": round(rev_growth, 4),
                "parameters_used": raw.get("parameters_used", {}),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            errors[ticker] = str(e)

    return {"results": results, "errors": errors}


def _write_to_firestore(analysis: dict) -> int:
    """Write analysis results to Firestore. Returns count of documents written."""
    db = firestore.client(database_id="market-flow")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0

    for ticker, data in analysis["results"].items():
        # Write latest (overwritten each run)
        db.collection("dcf_results").document(ticker).set(data)

        # Write daily snapshot (append-only history)
        db.collection("dcf_results").document(ticker) \
          .collection("snapshots").document(today).set(data)

        count += 1

    # Write run metadata
    db.collection("meta").document("last_run").set({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": today,
        "tickers_processed": list(analysis["results"].keys()),
        "tickers_failed": analysis["errors"],
        "total_success": len(analysis["results"]),
        "total_errors": len(analysis["errors"]),
    })

    return count


# =============================================================================
# Cloud Function entry points
# =============================================================================

@https_fn.on_request()
def run_daily_analysis(req: https_fn.Request) -> https_fn.Response:
    """HTTP-triggered function for manual runs or Cloud Scheduler."""
    analysis = _run_analysis(TICKERS)
    count = _write_to_firestore(analysis)

    return https_fn.Response(
        response=f"Wrote {count} tickers to Firestore. "
                 f"Errors: {analysis['errors'] or 'none'}",
        status=200,
    )


@scheduler_fn.on_schedule(schedule="0 11 * * 1-5", timezone="America/New_York")
def scheduled_daily_analysis(event: scheduler_fn.ScheduledEvent) -> None:
    """Scheduled function — runs weekdays at 11:00 AM ET (after market open)."""
    analysis = _run_analysis(TICKERS)
    count = _write_to_firestore(analysis)
    print(f"Scheduled run complete: {count} tickers. Errors: {analysis['errors'] or 'none'}")
