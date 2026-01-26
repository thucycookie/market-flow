"""
Customer-Based Corporate Valuation (CBCV) Model

Based on Daniel McCarthy's framework for valuing companies as portfolios of
customer relationships. Particularly useful for high-growth, cash-burning
companies where traditional DCF fails.

Company Value = Existing Customer Equity + Future Customer Equity
"""

from dataclasses import dataclass, field
from typing import Any

from market_flow.market_data.fmp_client import (
    get_balance_sheet,
    get_company_profile,
    get_income_statement,
    get_quote,
)
from market_flow.models.dcf_model import calculate_wacc


# =============================================================================
# Industry Benchmarks
# =============================================================================

INDUSTRY_CHURN_RATES: dict[str, float] = {
    "streaming": 0.05,      # 5% annual (Netflix-level retention)
    "fintech": 0.10,        # 10% annual
    "saas_b2b": 0.05,       # 5% annual
    "saas_b2c": 0.07,       # 7% annual
    "ecommerce": 0.25,      # 25% annual
    "telecom": 0.15,        # 15% annual
    "gaming": 0.20,         # 20% annual
    "insurance": 0.08,      # 8% annual
    "banking": 0.06,        # 6% annual
    "default": 0.10,        # 10% annual fallback
}

TICKER_INDUSTRY_MAP: dict[str, str] = {
    # Streaming
    "NFLX": "streaming",
    "DIS": "streaming",
    "SPOT": "streaming",
    "PARA": "streaming",
    "WBD": "streaming",
    # Fintech
    "SOFI": "fintech",
    "HOOD": "fintech",
    "SQ": "fintech",
    "PYPL": "fintech",
    "AFRM": "fintech",
    "UPST": "fintech",
    # SaaS B2B
    "CRM": "saas_b2b",
    "NOW": "saas_b2b",
    "WDAY": "saas_b2b",
    "ZM": "saas_b2b",
    "DDOG": "saas_b2b",
    "SNOW": "saas_b2b",
    # SaaS B2C
    "MTCH": "saas_b2c",
    "DUOL": "saas_b2c",
    # E-commerce
    "SHOP": "ecommerce",
    "ETSY": "ecommerce",
    "CHWY": "ecommerce",
    # Telecom
    "T": "telecom",
    "VZ": "telecom",
    "TMUS": "telecom",
    # Gaming
    "RBLX": "gaming",
    "TTWO": "gaming",
    "EA": "gaming",
    # Insurance
    "LMND": "insurance",
    "ROOT": "insurance",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CBCVResult:
    """Result of Customer-Based Corporate Valuation."""

    # Identification
    ticker: str
    company_name: str
    industry: str

    # Market data
    current_price: float
    shares_outstanding: float
    market_cap: float

    # Customer metrics (inputs)
    total_customers: int
    arpu: float                     # Annual revenue per user
    churn_rate: float               # Annual churn rate
    retention_rate: float           # 1 - churn_rate
    cac: float                      # Customer acquisition cost
    gross_margin: float

    # CLV outputs
    clv: float                      # Customer lifetime value
    ltv_cac_ratio: float            # CLV / CAC
    payback_months: float           # Months to recover CAC

    # Valuation components
    existing_customer_equity: float
    future_customer_equity: float
    total_customer_equity: float

    # Corporate value
    wacc: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    intrinsic_value_per_share: float
    upside_percentage: float

    # Projections
    projected_customers: list[int] = field(default_factory=list)
    projected_revenue: list[float] = field(default_factory=list)
    projected_acquisition: list[int] = field(default_factory=list)

    # Metadata
    assumptions: dict = field(default_factory=dict)
    sensitivity_matrix: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "industry": self.industry,
            "current_price": round(self.current_price, 2),
            "shares_outstanding": self.shares_outstanding,
            "market_cap": round(self.market_cap, 0),
            "total_customers": self.total_customers,
            "arpu": round(self.arpu, 2),
            "churn_rate": round(self.churn_rate, 4),
            "retention_rate": round(self.retention_rate, 4),
            "cac": round(self.cac, 2),
            "gross_margin": round(self.gross_margin, 4),
            "clv": round(self.clv, 2),
            "ltv_cac_ratio": round(self.ltv_cac_ratio, 2),
            "payback_months": round(self.payback_months, 1),
            "existing_customer_equity": round(self.existing_customer_equity, 0),
            "future_customer_equity": round(self.future_customer_equity, 0),
            "total_customer_equity": round(self.total_customer_equity, 0),
            "wacc": round(self.wacc, 4),
            "enterprise_value": round(self.enterprise_value, 0),
            "net_debt": round(self.net_debt, 0),
            "equity_value": round(self.equity_value, 0),
            "intrinsic_value_per_share": round(self.intrinsic_value_per_share, 2),
            "upside_percentage": round(self.upside_percentage, 1),
            "projected_customers": self.projected_customers,
            "projected_revenue": [round(r, 0) for r in self.projected_revenue],
            "projected_acquisition": self.projected_acquisition,
            "assumptions": self.assumptions,
            "sensitivity_matrix": self.sensitivity_matrix,
        }


# =============================================================================
# Helper Functions
# =============================================================================

def get_industry_for_ticker(ticker: str) -> str:
    """Get industry classification for a ticker."""
    return TICKER_INDUSTRY_MAP.get(ticker.upper(), "default")


def get_churn_rate_benchmark(ticker: str) -> float:
    """Get industry benchmark churn rate for a ticker."""
    industry = get_industry_for_ticker(ticker)
    return INDUSTRY_CHURN_RATES.get(industry, INDUSTRY_CHURN_RATES["default"])


def get_cbcv_financial_inputs(ticker: str) -> dict[str, Any]:
    """
    Fetch financial data needed for CBCV from FMP API.

    Returns:
        dict with: company_name, revenue, gross_margin, sm_expense,
                   shares_outstanding, current_price, net_debt, beta, wacc
    """
    # Fetch data from FMP
    profile = get_company_profile(ticker)
    income_stmt = get_income_statement(ticker, period="annual", limit=1)
    balance_sheet = get_balance_sheet(ticker, period="annual", limit=1)
    quote = get_quote(ticker)

    # Extract company info
    company_name = profile.get("companyName", ticker)
    beta = profile.get("beta", 1.0)
    # marketCap may be in profile or quote
    market_cap = profile.get("marketCap") or (quote.get("marketCap") if quote else 0) or 0

    # Extract income statement data
    if income_stmt:
        stmt = income_stmt[0]
        revenue = stmt.get("revenue", 0)
        gross_profit = stmt.get("grossProfit", 0)
        gross_margin = gross_profit / revenue if revenue > 0 else 0.5
        # S&M expense - try different field names
        sm_expense = (
            stmt.get("sellingAndMarketingExpenses", 0)
            or stmt.get("sellingGeneralAndAdministrativeExpenses", 0) * 0.5  # Estimate S&M as 50% of SG&A
        )
    else:
        revenue = 0
        gross_margin = 0.5
        sm_expense = 0

    # Extract balance sheet data
    if balance_sheet:
        bs = balance_sheet[0]
        total_debt = bs.get("totalDebt", 0)
        cash = bs.get("cashAndCashEquivalents", 0) + bs.get("shortTermInvestments", 0)
        net_debt = total_debt - cash
    else:
        net_debt = 0

    # Extract quote data
    current_price = quote.get("price", 0) if quote else 0
    # Calculate shares_outstanding from market_cap / price (more reliable than API field)
    if current_price > 0 and market_cap > 0:
        shares_outstanding = market_cap / current_price
    else:
        shares_outstanding = quote.get("sharesOutstanding", 0) if quote else 0

    # Calculate WACC
    wacc_result = calculate_wacc(
        beta=beta,
        ticker=ticker,
    )
    wacc = wacc_result.get("wacc", 0.10)

    return {
        "company_name": company_name,
        "revenue": revenue,
        "gross_margin": gross_margin,
        "sm_expense": sm_expense,
        "shares_outstanding": shares_outstanding,
        "current_price": current_price,
        "net_debt": net_debt,
        "market_cap": market_cap,
        "beta": beta,
        "wacc": wacc,
    }


# =============================================================================
# Core CLV Calculations
# =============================================================================

def calculate_clv(
    arpu: float,
    gross_margin: float,
    retention_rate: float,
    discount_rate: float,
) -> float:
    """
    Calculate Customer Lifetime Value using the simple CLV formula.

    For subscription/contractual businesses where customers have clear
    retention patterns.

    Formula: CLV = (ARPU × Margin) × (Retention / (1 + Discount - Retention))

    Args:
        arpu: Annual Revenue Per User
        gross_margin: Gross profit margin (0-1)
        retention_rate: Annual customer retention rate (0-1)
        discount_rate: WACC or required return (0-1)

    Returns:
        Customer Lifetime Value in dollars
    """
    if retention_rate >= 1:
        retention_rate = 0.99  # Cap at 99% to avoid division issues

    margin_contribution = arpu * gross_margin
    multiplier = retention_rate / (1 + discount_rate - retention_rate)

    return margin_contribution * multiplier


def calculate_cac(
    sales_marketing_expense: float,
    new_customers: int,
) -> float:
    """
    Calculate Customer Acquisition Cost.

    CAC = Sales & Marketing Expense / New Customers Acquired

    Args:
        sales_marketing_expense: Annual S&M spend
        new_customers: Number of new customers acquired in the period

    Returns:
        Customer Acquisition Cost per customer
    """
    if new_customers <= 0:
        return 0
    return sales_marketing_expense / new_customers


def calculate_payback_months(
    cac: float,
    arpu: float,
    gross_margin: float,
) -> float:
    """
    Calculate months to recover customer acquisition cost.

    Payback = CAC / (Monthly Margin Contribution)
            = CAC / (ARPU × Margin / 12)

    Args:
        cac: Customer Acquisition Cost
        arpu: Annual Revenue Per User
        gross_margin: Gross profit margin (0-1)

    Returns:
        Payback period in months
    """
    monthly_contribution = (arpu * gross_margin) / 12
    if monthly_contribution <= 0:
        return float("inf")
    return cac / monthly_contribution


def calculate_existing_customer_equity(
    total_customers: int,
    clv: float,
) -> float:
    """
    Calculate the value of existing customer base.

    Existing CE = Total Customers × CLV

    Args:
        total_customers: Current customer count
        clv: Customer Lifetime Value

    Returns:
        Total value of existing customers
    """
    return total_customers * clv


def calculate_future_customer_equity(
    annual_new_customers: int,
    clv: float,
    cac: float,
    discount_rate: float,
    projection_years: int = 10,
    acquisition_decay: float = 0.10,
    tam: int | None = None,
    current_customers: int = 0,
) -> tuple[float, list[int]]:
    """
    Calculate NPV of future customer acquisitions.

    Future CE = Σ (New_t × (CLV - CAC)) / (1 + r)^t

    Each year, new customer acquisition decays by acquisition_decay rate,
    representing market saturation.

    Args:
        annual_new_customers: Current annual acquisition rate
        clv: Customer Lifetime Value
        cac: Customer Acquisition Cost
        discount_rate: WACC
        projection_years: Years to project (default 10)
        acquisition_decay: Annual decrease in acquisition rate (default 10%)
        tam: Total Addressable Market cap (optional)
        current_customers: Current customer count for TAM check

    Returns:
        Tuple of (Future Customer Equity, list of projected acquisitions per year)
    """
    if clv <= cac:
        # If CLV doesn't exceed CAC, future customers destroy value
        return 0, [0] * projection_years

    value_per_new_customer = clv - cac
    total_future_equity = 0
    projected_acquisitions = []

    cumulative_customers = current_customers
    current_acquisition = annual_new_customers

    for year in range(1, projection_years + 1):
        # Check TAM constraint
        if tam and cumulative_customers >= tam:
            current_acquisition = 0

        # Calculate this year's acquisition (with decay)
        year_acquisition = int(current_acquisition * ((1 - acquisition_decay) ** (year - 1)))

        # Apply TAM cap if set
        if tam:
            year_acquisition = min(year_acquisition, tam - cumulative_customers)
            year_acquisition = max(0, year_acquisition)

        projected_acquisitions.append(year_acquisition)
        cumulative_customers += year_acquisition

        # Discount to present value
        year_value = year_acquisition * value_per_new_customer
        pv = year_value / ((1 + discount_rate) ** year)
        total_future_equity += pv

        current_acquisition = year_acquisition  # Update for decay calculation

    return total_future_equity, projected_acquisitions


def build_sensitivity_matrix(
    base_clv: float,
    arpu: float,
    gross_margin: float,
    base_retention: float,
    discount_rate: float,
) -> dict[str, dict[str, float]]:
    """
    Build sensitivity matrix showing CLV at different retention/ARPU levels.

    Returns:
        Nested dict: retention_rate -> arpu_change -> CLV
    """
    retention_variations = [-0.05, -0.025, 0, 0.025, 0.05]  # ±5%
    arpu_variations = [-0.20, -0.10, 0, 0.10, 0.20]  # ±20%

    matrix = {}

    for ret_delta in retention_variations:
        test_retention = min(0.99, max(0.5, base_retention + ret_delta))
        retention_key = f"{test_retention:.1%}"
        matrix[retention_key] = {}

        for arpu_delta in arpu_variations:
            test_arpu = arpu * (1 + arpu_delta)
            arpu_key = f"{arpu_delta:+.0%} ARPU"

            clv = calculate_clv(test_arpu, gross_margin, test_retention, discount_rate)
            matrix[retention_key][arpu_key] = round(clv, 2)

    return matrix


# =============================================================================
# Main Model Builder
# =============================================================================

def build_cbcv_model(
    ticker: str,
    total_customers: int,
    arpu: float | None = None,
    churn_rate: float | None = None,
    cac: float | None = None,
    new_customers: int | None = None,
    projection_years: int = 10,
    tam: int | None = None,
) -> CBCVResult:
    """
    Build a Customer-Based Corporate Valuation model.

    This is the main orchestrator function that:
    1. Fetches financial data from FMP
    2. Applies industry benchmarks for missing inputs
    3. Calculates CLV and customer equity
    4. Returns a complete valuation

    Args:
        ticker: Stock symbol
        total_customers: Current customer count (REQUIRED)
        arpu: Annual Revenue Per User (optional, will calculate from revenue/customers)
        churn_rate: Annual churn rate (optional, will use industry benchmark)
        cac: Customer Acquisition Cost (optional, will calculate from S&M/new_customers)
        new_customers: New customers added this year (optional, for CAC calculation)
        projection_years: Years to project future acquisitions (default 10)
        tam: Total Addressable Market cap (optional)

    Returns:
        CBCVResult with complete valuation
    """
    # Fetch financial data
    fin_data = get_cbcv_financial_inputs(ticker)

    company_name = fin_data["company_name"]
    revenue = fin_data["revenue"]
    gross_margin = fin_data["gross_margin"]
    sm_expense = fin_data["sm_expense"]
    shares_outstanding = fin_data["shares_outstanding"]
    current_price = fin_data["current_price"]
    net_debt = fin_data["net_debt"]
    market_cap = fin_data["market_cap"]
    wacc = fin_data["wacc"]

    # Get industry classification
    industry = get_industry_for_ticker(ticker)

    # Calculate or use provided ARPU
    if arpu is None:
        if total_customers > 0 and revenue > 0:
            arpu = revenue / total_customers
        else:
            raise ValueError("ARPU must be provided or calculable from revenue/customers")

    # Use provided or benchmark churn rate
    if churn_rate is None:
        churn_rate = get_churn_rate_benchmark(ticker)

    retention_rate = 1 - churn_rate

    # Calculate or estimate CAC
    if cac is None:
        if new_customers and new_customers > 0 and sm_expense > 0:
            cac = calculate_cac(sm_expense, new_customers)
        else:
            # Estimate: Assume CAC = 1 year of margin contribution (reasonable default)
            cac = arpu * gross_margin

    # Estimate new customers if not provided (for future CE projection)
    if new_customers is None:
        # Estimate: 10% of current base as annual acquisition
        new_customers = int(total_customers * 0.10)

    # Calculate CLV
    clv = calculate_clv(arpu, gross_margin, retention_rate, wacc)

    # Calculate LTV/CAC ratio
    ltv_cac_ratio = clv / cac if cac > 0 else float("inf")

    # Calculate payback period
    payback_months = calculate_payback_months(cac, arpu, gross_margin)

    # Calculate existing customer equity
    existing_ce = calculate_existing_customer_equity(total_customers, clv)

    # Calculate future customer equity
    future_ce, projected_acquisition = calculate_future_customer_equity(
        annual_new_customers=new_customers,
        clv=clv,
        cac=cac,
        discount_rate=wacc,
        projection_years=projection_years,
        acquisition_decay=0.10,
        tam=tam,
        current_customers=total_customers,
    )

    # Total customer equity = enterprise value
    total_ce = existing_ce + future_ce
    enterprise_value = total_ce

    # Equity value
    equity_value = enterprise_value - net_debt

    # Intrinsic value per share
    if shares_outstanding > 0:
        intrinsic_value = equity_value / shares_outstanding
    else:
        intrinsic_value = 0

    # Upside percentage
    if current_price > 0:
        upside = ((intrinsic_value - current_price) / current_price) * 100
    else:
        upside = 0

    # Project customers and revenue
    projected_customers = [total_customers]
    projected_revenue = [total_customers * arpu]

    for i, acq in enumerate(projected_acquisition):
        # Simple projection: existing × retention + new
        prev_customers = projected_customers[-1]
        retained = int(prev_customers * retention_rate)
        new_total = retained + acq
        projected_customers.append(new_total)
        projected_revenue.append(new_total * arpu)

    # Build sensitivity matrix
    sensitivity = build_sensitivity_matrix(clv, arpu, gross_margin, retention_rate, wacc)

    # Compile assumptions
    assumptions = {
        "arpu": arpu,
        "arpu_source": "calculated" if arpu == revenue / total_customers else "provided",
        "churn_rate": churn_rate,
        "churn_source": "industry_benchmark" if churn_rate == get_churn_rate_benchmark(ticker) else "provided",
        "retention_rate": retention_rate,
        "cac": cac,
        "cac_source": "calculated" if new_customers and sm_expense else "estimated",
        "gross_margin": gross_margin,
        "wacc": wacc,
        "projection_years": projection_years,
        "acquisition_decay": 0.10,
        "tam": tam,
    }

    return CBCVResult(
        ticker=ticker.upper(),
        company_name=company_name,
        industry=industry,
        current_price=current_price,
        shares_outstanding=shares_outstanding,
        market_cap=market_cap,
        total_customers=total_customers,
        arpu=arpu,
        churn_rate=churn_rate,
        retention_rate=retention_rate,
        cac=cac,
        gross_margin=gross_margin,
        clv=clv,
        ltv_cac_ratio=ltv_cac_ratio,
        payback_months=payback_months,
        existing_customer_equity=existing_ce,
        future_customer_equity=future_ce,
        total_customer_equity=total_ce,
        wacc=wacc,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        intrinsic_value_per_share=intrinsic_value,
        upside_percentage=upside,
        projected_customers=projected_customers,
        projected_revenue=projected_revenue,
        projected_acquisition=projected_acquisition,
        assumptions=assumptions,
        sensitivity_matrix=sensitivity,
    )
