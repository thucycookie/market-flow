"""
Discounted Cash Flow (DCF) Model

This module provides DCF valuation calculations for company analysis.
"""

from dataclasses import dataclass, field
from typing import Any

from ..market_data.fmp_client import (
    get_company_profile,
    get_income_statement,
    get_cash_flow,
    get_balance_sheet,
    get_key_metrics,
    get_quote,
    get_ratios_ttm,
)


@dataclass
class DCFResult:
    """Container for DCF model results."""

    ticker: str
    company_name: str
    current_price: float
    intrinsic_value: float
    upside_percentage: float

    # WACC components
    wacc: float
    cost_of_equity: float
    cost_of_debt: float
    tax_rate: float
    debt_weight: float
    equity_weight: float

    # Projections
    projection_years: int
    revenue_growth_rate: float
    terminal_growth_rate: float
    projected_fcfs: list[float]
    terminal_value: float
    enterprise_value: float

    # Per share
    shares_outstanding: float
    net_debt: float

    # Supporting data
    historical_fcf: list[dict] = field(default_factory=list)
    assumptions: dict = field(default_factory=dict)
    sensitivity_matrix: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "current_price": self.current_price,
            "intrinsic_value": round(self.intrinsic_value, 2),
            "upside_percentage": round(self.upside_percentage, 1),
            "wacc": round(self.wacc, 4),
            "cost_of_equity": round(self.cost_of_equity, 4),
            "cost_of_debt": round(self.cost_of_debt, 4),
            "tax_rate": round(self.tax_rate, 4),
            "debt_weight": round(self.debt_weight, 4),
            "equity_weight": round(self.equity_weight, 4),
            "projection_years": self.projection_years,
            "revenue_growth_rate": round(self.revenue_growth_rate, 4),
            "terminal_growth_rate": round(self.terminal_growth_rate, 4),
            "projected_fcfs": [round(fcf, 0) for fcf in self.projected_fcfs],
            "terminal_value": round(self.terminal_value, 0),
            "enterprise_value": round(self.enterprise_value, 0),
            "shares_outstanding": round(self.shares_outstanding, 0),
            "net_debt": round(self.net_debt, 0),
            "historical_fcf": self.historical_fcf,
            "assumptions": self.assumptions,
            "sensitivity_matrix": self.sensitivity_matrix,
        }


def calculate_wacc(
    beta: float,
    risk_free_rate: float = 0.045,
    market_premium: float = 0.055,
    debt_ratio: float | None = None,
    cost_of_debt: float = 0.06,
    tax_rate: float = 0.21,
    ticker: str | None = None,
) -> dict:
    """
    Calculate Weighted Average Cost of Capital.

    Args:
        beta: Company's beta (systematic risk)
        risk_free_rate: Risk-free rate (default: 4.5% - 10yr Treasury)
        market_premium: Equity risk premium (default: 5.5%)
        debt_ratio: Debt / (Debt + Equity) - if None and ticker provided,
                    auto-fetches from TTM ratios
        cost_of_debt: Pre-tax cost of debt
        tax_rate: Corporate tax rate (default: 21%)
        ticker: Optional stock ticker to auto-fetch debt ratio from TTM ratios

    Returns:
        dict with WACC components and final WACC
    """
    # Auto-fetch debt ratio from TTM ratios if ticker provided and debt_ratio not specified
    if debt_ratio is None:
        if ticker:
            try:
                ttm_ratios = get_ratios_ttm(ticker)
                # Use debtToCapitalRatioTTM = D/(D+E) for proper WACC weights
                debt_ratio = ttm_ratios.get("debtToCapitalRatioTTM", 0.3)
                if debt_ratio is None:
                    debt_ratio = 0.3
            except Exception:
                debt_ratio = 0.3  # Fallback if API fails
        else:
            debt_ratio = 0.3  # Default if no ticker provided

    # Cost of Equity using CAPM
    cost_of_equity = risk_free_rate + beta * market_premium

    # Equity weight
    equity_ratio = 1 - debt_ratio

    # After-tax cost of debt
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)

    # WACC calculation
    wacc = (equity_ratio * cost_of_equity) + (debt_ratio * after_tax_cost_of_debt)

    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "tax_rate": tax_rate,
        "debt_weight": debt_ratio,
        "equity_weight": equity_ratio,
        "beta": beta,
        "risk_free_rate": risk_free_rate,
        "market_premium": market_premium,
    }


def project_free_cash_flows(
    base_fcf: float,
    growth_rates: list[float] | float,
    years: int = 5,
) -> list[float]:
    """
    Project future free cash flows.

    Args:
        base_fcf: Most recent free cash flow
        growth_rates: Either a single rate or list of rates per year
        years: Number of years to project

    Returns:
        List of projected FCFs for each year
    """
    if isinstance(growth_rates, (int, float)):
        growth_rates = [growth_rates] * years

    if len(growth_rates) < years:
        # Extend with last rate if not enough provided
        growth_rates = list(growth_rates) + [growth_rates[-1]] * (
            years - len(growth_rates)
        )

    projected = []
    current_fcf = base_fcf

    for i in range(years):
        current_fcf = current_fcf * (1 + growth_rates[i])
        projected.append(current_fcf)

    return projected


def calculate_terminal_value(
    final_fcf: float,
    perpetual_growth: float = 0.025,
    wacc: float = 0.10,
) -> float:
    """
    Calculate terminal value using Gordon Growth Model.

    Args:
        final_fcf: Free cash flow in the final projection year
        perpetual_growth: Long-term growth rate (default: 2.5%)
        wacc: Weighted average cost of capital

    Returns:
        Terminal value
    """
    if wacc <= perpetual_growth:
        raise ValueError(
            f"WACC ({wacc:.2%}) must be greater than perpetual growth rate ({perpetual_growth:.2%})"
        )

    return (final_fcf * (1 + perpetual_growth)) / (wacc - perpetual_growth)


def calculate_intrinsic_value(
    projected_fcfs: list[float],
    terminal_value: float,
    wacc: float,
    shares_outstanding: float,
    net_debt: float = 0,
) -> dict:
    """
    Calculate intrinsic value per share.

    Args:
        projected_fcfs: List of projected free cash flows
        terminal_value: Terminal value at end of projection period
        wacc: Weighted average cost of capital
        shares_outstanding: Number of shares outstanding
        net_debt: Net debt (Total Debt - Cash)

    Returns:
        dict with enterprise value, equity value, and per-share value
    """
    # Discount projected FCFs
    pv_fcfs = []
    for i, fcf in enumerate(projected_fcfs):
        discount_factor = (1 + wacc) ** (i + 1)
        pv_fcfs.append(fcf / discount_factor)

    # Discount terminal value
    final_year = len(projected_fcfs)
    pv_terminal = terminal_value / ((1 + wacc) ** final_year)

    # Enterprise value
    enterprise_value = sum(pv_fcfs) + pv_terminal

    # Equity value (subtract net debt)
    equity_value = enterprise_value - net_debt

    # Per share value
    intrinsic_value_per_share = equity_value / shares_outstanding

    return {
        "pv_fcfs": pv_fcfs,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_value_per_share": intrinsic_value_per_share,
    }


def _calculate_historical_growth(values: list[float]) -> float:
    """Calculate CAGR from a list of values (oldest to newest)."""
    if len(values) < 2 or values[0] <= 0:
        return 0.05  # Default 5% if can't calculate

    years = len(values) - 1
    ending = values[-1]
    beginning = values[0]

    if beginning <= 0 or ending <= 0:
        return 0.05

    return (ending / beginning) ** (1 / years) - 1


def build_dcf_model(
    ticker: str,
    projection_years: int = 5,
    terminal_growth_rate: float = 0.025,
    risk_free_rate: float = 0.045,
    market_premium: float = 0.055,
    custom_growth_rate: float | None = None,
) -> DCFResult:
    """
    Build a complete DCF model for a company.

    This is the main function that orchestrates data fetching and calculations.

    Args:
        ticker: Stock ticker symbol
        projection_years: Number of years to project (default: 5)
        terminal_growth_rate: Long-term growth rate (default: 2.5%)
        risk_free_rate: Risk-free rate for WACC (default: 4.5%)
        market_premium: Equity risk premium (default: 5.5%)
        custom_growth_rate: Override calculated growth rate if provided

    Returns:
        DCFResult with complete model data
    """
    ticker = ticker.upper()

    # Fetch data from FMP
    profile = get_company_profile(ticker)
    income_statements = get_income_statement(ticker, period="annual", limit=5)
    cash_flows = get_cash_flow(ticker, period="annual", limit=5)
    balance_sheets = get_balance_sheet(ticker, period="annual", limit=5)
    quote = get_quote(ticker)

    # Extract key values
    company_name = profile.get("companyName", ticker)
    beta = profile.get("beta", 1.0) or 1.0
    current_price = quote.get("price", 0)
    # Calculate shares outstanding from market cap if not directly available
    shares_outstanding = quote.get("sharesOutstanding", 0)
    if not shares_outstanding and current_price > 0:
        market_cap = quote.get("marketCap", 0) or profile.get("marketCap", 0)
        shares_outstanding = market_cap / current_price if market_cap else 0

    # Get most recent balance sheet data
    latest_bs = balance_sheets[0] if balance_sheets else {}
    total_debt = latest_bs.get("totalDebt", 0) or 0
    cash = latest_bs.get("cashAndCashEquivalents", 0) or 0
    net_debt = total_debt - cash

    # Estimate cost of debt from interest expense
    latest_income = income_statements[0] if income_statements else {}
    interest_expense = abs(latest_income.get("interestExpense", 0) or 0)
    cost_of_debt = (interest_expense / total_debt) if total_debt > 0 else 0.06
    cost_of_debt = max(0.03, min(cost_of_debt, 0.15))  # Bound between 3% and 15%

    # Get tax rate
    income_before_tax = latest_income.get("incomeBeforeTax", 0) or 1
    income_tax = latest_income.get("incomeTaxExpense", 0) or 0
    tax_rate = (income_tax / income_before_tax) if income_before_tax > 0 else 0.21
    tax_rate = max(0, min(tax_rate, 0.4))  # Bound between 0% and 40%

    # Calculate WACC (auto-fetches debt ratio from TTM ratios via ticker)
    wacc_result = calculate_wacc(
        beta=beta,
        risk_free_rate=risk_free_rate,
        market_premium=market_premium,
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        ticker=ticker,
    )

    # Get historical FCF
    historical_fcf = []
    for cf in reversed(cash_flows):  # Oldest to newest
        fcf = cf.get("freeCashFlow", 0)
        if fcf:
            historical_fcf.append(
                {
                    "year": cf.get("calendarYear", ""),
                    "fcf": fcf,
                }
            )

    # Calculate growth rate from historical data or use custom
    fcf_values = [h["fcf"] for h in historical_fcf if h["fcf"] > 0]
    if custom_growth_rate is not None:
        growth_rate = custom_growth_rate
    elif len(fcf_values) >= 2:
        growth_rate = _calculate_historical_growth(fcf_values)
        # Cap growth rate at reasonable bounds
        growth_rate = max(-0.10, min(growth_rate, 0.30))
    else:
        growth_rate = 0.08  # Default 8%

    # Get base FCF (most recent)
    base_fcf = cash_flows[0].get("freeCashFlow", 0) if cash_flows else 0
    if base_fcf <= 0:
        # If FCF is negative, use operating cash flow minus average capex
        base_fcf = cash_flows[0].get("operatingCashFlow", 0) or 0
        capex = abs(cash_flows[0].get("capitalExpenditure", 0) or 0)
        base_fcf = base_fcf - capex

    # Project FCFs
    projected_fcfs = project_free_cash_flows(
        base_fcf=base_fcf,
        growth_rates=growth_rate,
        years=projection_years,
    )

    # Calculate terminal value
    terminal_value = calculate_terminal_value(
        final_fcf=projected_fcfs[-1],
        perpetual_growth=terminal_growth_rate,
        wacc=wacc_result["wacc"],
    )

    # Calculate intrinsic value
    valuation = calculate_intrinsic_value(
        projected_fcfs=projected_fcfs,
        terminal_value=terminal_value,
        wacc=wacc_result["wacc"],
        shares_outstanding=shares_outstanding,
        net_debt=net_debt,
    )

    intrinsic_value = valuation["intrinsic_value_per_share"]
    upside = ((intrinsic_value - current_price) / current_price * 100) if current_price > 0 else 0

    # Build sensitivity matrix
    wacc_range = [wacc_result["wacc"] - 0.02, wacc_result["wacc"], wacc_result["wacc"] + 0.02]
    growth_range = [terminal_growth_rate - 0.01, terminal_growth_rate, terminal_growth_rate + 0.01]

    sensitivity_matrix = {}
    for w in wacc_range:
        w_key = f"{w:.1%}"
        sensitivity_matrix[w_key] = {}
        for g in growth_range:
            tv = calculate_terminal_value(projected_fcfs[-1], g, w)
            val = calculate_intrinsic_value(
                projected_fcfs, tv, w, shares_outstanding, net_debt
            )
            sensitivity_matrix[w_key][f"{g:.1%}"] = round(
                val["intrinsic_value_per_share"], 2
            )

    # Build assumptions dict
    assumptions = {
        "base_fcf": base_fcf,
        "revenue_growth_rate": growth_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "risk_free_rate": risk_free_rate,
        "market_premium": market_premium,
        "beta": beta,
        "projection_years": projection_years,
    }

    return DCFResult(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        intrinsic_value=intrinsic_value,
        upside_percentage=upside,
        wacc=wacc_result["wacc"],
        cost_of_equity=wacc_result["cost_of_equity"],
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        debt_weight=wacc_result["debt_weight"],
        equity_weight=wacc_result["equity_weight"],
        projection_years=projection_years,
        revenue_growth_rate=growth_rate,
        terminal_growth_rate=terminal_growth_rate,
        projected_fcfs=projected_fcfs,
        terminal_value=terminal_value,
        enterprise_value=valuation["enterprise_value"],
        shares_outstanding=shares_outstanding,
        net_debt=net_debt,
        historical_fcf=historical_fcf,
        assumptions=assumptions,
        sensitivity_matrix=sensitivity_matrix,
    )


# =============================================================================
# Custom DCF Parameter Calculation Helpers
# =============================================================================

# Damodaran Equity Risk Premiums by Country (source: NYU Stern, 2024)
# https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html
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

# Long-term GDP growth estimates by country/region
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


def calculate_revenue_growth_pct(
    income_statements: list[dict],
    periods: int | None = None,
) -> float:
    """
    Calculate revenue growth percentage using CAGR from historical income statements.

    Args:
        income_statements: List of income statements (newest first)
        periods: Number of periods to use (default: all available)

    Returns:
        Revenue growth rate as percentage (e.g., 10.5 for 10.5%)
    """
    # Limit periods if specified
    statements = income_statements[:periods] if periods else income_statements

    # FMP API returns newest first, but CAGR needs oldest-to-newest
    # CAGR = (Ending/Beginning)^(1/years) - 1
    # So we reverse to get: revenues[0]=oldest (beginning), revenues[-1]=newest (ending)
    revenues = [stmt.get("revenue", 0) for stmt in reversed(statements)]
    revenues = [r for r in revenues if r and r > 0]  # Filter out zeros/nulls

    if len(revenues) < 2:
        return 5.0  # Default 5% if insufficient data

    years = len(revenues) - 1
    cagr = (revenues[-1] / revenues[0]) ** (1 / years) - 1
    return round(cagr * 100, 2)


def calculate_capital_expenditure_pct(
    cash_flows: list[dict],
    income_statements: list[dict],
    periods: int = 5,
) -> float:
    """
    Calculate capital expenditure as percentage of revenue.

    Uses average of recent periods to smooth out cyclical CapEx.

    Args:
        cash_flows: List of cash flow statements (newest first)
        income_statements: List of income statements (newest first)
        periods: Number of periods to average (default: 5)

    Returns:
        CapEx as percentage of revenue (e.g., 5.2 for 5.2%)
    """
    capex_pcts = []

    for i in range(min(periods, len(cash_flows), len(income_statements))):
        capex = abs(cash_flows[i].get("capitalExpenditure", 0) or 0)
        revenue = income_statements[i].get("revenue", 0) or 0

        if revenue > 0:
            capex_pcts.append(capex / revenue)

    if not capex_pcts:
        return 5.0  # Default 5% CapEx/Revenue

    avg_pct = sum(capex_pcts) / len(capex_pcts)
    return round(avg_pct * 100, 2)


def calculate_operating_cash_flow_pct(
    cash_flows: list[dict],
    income_statements: list[dict],
    periods: int = 5,
) -> float:
    """
    Calculate operating cash flow as percentage of revenue.

    Args:
        cash_flows: List of cash flow statements (newest first)
        income_statements: List of income statements (newest first)
        periods: Number of periods to average (default: 5)

    Returns:
        OCF as percentage of revenue (e.g., 25.0 for 25%)
    """
    ocf_pcts = []

    for i in range(min(periods, len(cash_flows), len(income_statements))):
        ocf = cash_flows[i].get("operatingCashFlow", 0) or 0
        revenue = income_statements[i].get("revenue", 0) or 0

        if revenue > 0:
            ocf_pcts.append(ocf / revenue)

    if not ocf_pcts:
        return 15.0  # Default 15% OCF/Revenue

    avg_pct = sum(ocf_pcts) / len(ocf_pcts)
    return round(avg_pct * 100, 2)


def calculate_market_risk_premium(country: str = "United States") -> float:
    """
    Get equity risk premium for a country from Damodaran's estimates.

    Data source: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html

    Args:
        country: Country name (e.g., "United States", "Taiwan", "Germany")

    Returns:
        Equity risk premium as percentage (e.g., 4.46 for US)
    """
    # Try exact match first
    if country in COUNTRY_EQUITY_RISK_PREMIUMS:
        return COUNTRY_EQUITY_RISK_PREMIUMS[country]

    # Try case-insensitive match
    country_lower = country.lower()
    for key, value in COUNTRY_EQUITY_RISK_PREMIUMS.items():
        if key.lower() == country_lower:
            return value

    # Default to US if country not found
    return COUNTRY_EQUITY_RISK_PREMIUMS["United States"]


def calculate_long_term_growth_rate(country: str = "United States") -> float:
    """
    Get long-term growth rate estimate for terminal value calculation.

    Uses long-term GDP growth estimates as a proxy for terminal growth.
    Terminal growth should not exceed long-term GDP growth.

    Args:
        country: Country name (e.g., "United States", "Taiwan")

    Returns:
        Long-term growth rate as percentage (e.g., 2.5 for 2.5%)

    Note:
        Common range: 2-3% for mature developed market companies.
        Higher (4-5%) for emerging markets.
    """
    # Try exact match first
    if country in COUNTRY_GDP_GROWTH:
        return COUNTRY_GDP_GROWTH[country]

    # Try case-insensitive match
    country_lower = country.lower()
    for key, value in COUNTRY_GDP_GROWTH.items():
        if key.lower() == country_lower:
            return value

    # Default to US
    return COUNTRY_GDP_GROWTH["United States"]


def calculate_ebitda_pct(
    income_statements: list[dict],
    periods: int = 5,
) -> float:
    """
    Calculate EBITDA margin as percentage of revenue.

    Args:
        income_statements: List of income statements (newest first)
        periods: Number of periods to average (default: 5)

    Returns:
        EBITDA margin as percentage (e.g., 25.0 for 25%)
    """
    margins = []
    for i in range(min(periods, len(income_statements))):
        ebitda = income_statements[i].get("ebitda", 0) or 0
        revenue = income_statements[i].get("revenue", 0) or 0
        if revenue > 0:
            margins.append(ebitda / revenue)

    if not margins:
        return 15.0  # Default 15%
    return round(sum(margins) / len(margins) * 100, 2)


def _calculate_effective_tax_rate(income_statements: list[dict]) -> float:
    """Calculate effective tax rate from income statements."""
    latest = income_statements[0] if income_statements else {}
    income_before_tax = latest.get("incomeBeforeTax", 0) or 1
    tax_expense = latest.get("incomeTaxExpense", 0) or 0

    if income_before_tax <= 0:
        return 0.21  # Default US corporate rate

    rate = tax_expense / income_before_tax
    return round(max(0, min(rate, 0.4)), 4)  # Bound 0-40%


def calculate_all_dcf_parameters(
    ticker: str,
    periods: int = 5,
    country: str = "United States",
) -> dict:
    """
    Calculate all DCF input parameters from historical data.

    Fetches financial data and computes recommended values for
    all Custom DCF Advanced API parameters.

    Args:
        ticker: Stock ticker symbol
        periods: Number of historical periods to fetch and use for calculations
        country: Country for equity risk premium lookup

    Returns:
        dict with all calculated parameters ready for get_custom_dcf()
    """
    profile = get_company_profile(ticker)
    income_stmts = get_income_statement(ticker, period="annual", limit=periods)
    cash_flows = get_cash_flow(ticker, period="annual", limit=periods)

    # Calculate all parameters with consistent periods
    return {
        "revenue_growth_pct": calculate_revenue_growth_pct(income_stmts, periods=periods),
        "ebitda_pct": calculate_ebitda_pct(income_stmts, periods=periods),
        "capital_expenditure_pct": calculate_capital_expenditure_pct(cash_flows, income_stmts, periods=periods),
        "operating_cash_flow_pct": calculate_operating_cash_flow_pct(cash_flows, income_stmts, periods=periods),
        "market_risk_premium": calculate_market_risk_premium(country=country),
        "long_term_growth_rate": calculate_long_term_growth_rate(country=country),
        "beta": profile.get("beta", 1.0),
        "tax_rate": _calculate_effective_tax_rate(income_stmts),
    }
