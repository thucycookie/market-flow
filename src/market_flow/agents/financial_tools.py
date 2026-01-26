"""
Financial Modeling Tools for Claude Agent SDK

Thin @tool wrappers around existing market_data and models functions.
These wrappers convert synchronous functions to async and format outputs
for MCP protocol compatibility.
"""

import json
from typing import Any

from claude_agent_sdk import tool

from ..market_data.fmp_client import (
    get_company_profile,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_financial_ratios,
    get_key_metrics,
    get_earnings_history,
    get_quote,
    get_dcf,
    get_analyst_estimates,
    get_custom_dcf,
)
from ..models.dcf_model import (
    calculate_wacc,
    project_free_cash_flows,
    calculate_terminal_value,
    calculate_intrinsic_value,
    build_dcf_model,
    calculate_all_dcf_parameters,
)
from ..models.cbcv_model import (
    calculate_clv,
    calculate_cac,
    build_cbcv_model,
    get_churn_rate_benchmark,
    get_industry_for_ticker,
)


def _mcp_response(data: Any) -> dict:
    """Convert data to MCP-compatible response format."""
    if hasattr(data, "to_dict"):
        # Handle dataclasses with to_dict method (like DCFResult)
        content = json.dumps(data.to_dict(), indent=2)
    elif isinstance(data, (dict, list)):
        content = json.dumps(data, indent=2)
    else:
        content = str(data)

    return {
        "content": [{
            "type": "text",
            "text": content
        }]
    }


# =============================================================================
# Market Data Tools (from fmp_client.py)
# =============================================================================

@tool(
    "fetch_company_profile",
    "Get company profile including industry, sector, market cap, beta, and description",
    {"ticker": str}
)
async def fetch_company_profile_tool(args: dict) -> dict:
    """Fetch company profile from FMP."""
    result = get_company_profile(args["ticker"])
    return _mcp_response(result)


@tool(
    "fetch_income_statement",
    "Get income statements with revenue, net income, EPS, and margins",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_income_statement_tool(args: dict) -> dict:
    """Fetch income statements from FMP."""
    result = get_income_statement(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


@tool(
    "fetch_balance_sheet",
    "Get balance sheets with assets, liabilities, equity, and debt levels",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_balance_sheet_tool(args: dict) -> dict:
    """Fetch balance sheets from FMP."""
    result = get_balance_sheet(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


@tool(
    "fetch_cash_flow",
    "Get cash flow statements with operating cash flow, CapEx, and free cash flow",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_cash_flow_tool(args: dict) -> dict:
    """Fetch cash flow statements from FMP."""
    result = get_cash_flow(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


@tool(
    "fetch_financial_ratios",
    "Get financial ratios including ROE, ROA, current ratio, and profit margins",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_financial_ratios_tool(args: dict) -> dict:
    """Fetch financial ratios from FMP."""
    result = get_financial_ratios(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


@tool(
    "fetch_key_metrics",
    "Get key valuation metrics including PE ratio, EV/EBITDA, ROIC, and per-share values",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_key_metrics_tool(args: dict) -> dict:
    """Fetch key metrics from FMP."""
    result = get_key_metrics(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


@tool(
    "fetch_earnings_history",
    "Get historical earnings with actual EPS, estimates, and surprise percentages",
    {"ticker": str, "limit": int}
)
async def fetch_earnings_history_tool(args: dict) -> dict:
    """Fetch earnings history from FMP."""
    result = get_earnings_history(
        args["ticker"],
        limit=args.get("limit", 20)
    )
    return _mcp_response(result)


@tool(
    "fetch_stock_quote",
    "Get real-time stock quote with price, volume, market cap, and 52-week range",
    {"ticker": str}
)
async def fetch_stock_quote_tool(args: dict) -> dict:
    """Fetch real-time stock quote from FMP."""
    result = get_quote(args["ticker"])
    return _mcp_response(result)


@tool(
    "fetch_fmp_dcf",
    "Get FMP's pre-calculated DCF valuation for quick reference",
    {"ticker": str}
)
async def fetch_fmp_dcf_tool(args: dict) -> dict:
    """Fetch FMP's DCF valuation."""
    result = get_dcf(args["ticker"])
    return _mcp_response(result)


@tool(
    "fetch_analyst_estimates",
    "Get analyst revenue and EPS estimates for future periods",
    {"ticker": str, "period": str, "limit": int}
)
async def fetch_analyst_estimates_tool(args: dict) -> dict:
    """Fetch analyst estimates from FMP."""
    result = get_analyst_estimates(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    )
    return _mcp_response(result)


# =============================================================================
# DCF Model Tools (from dcf_model.py)
# =============================================================================

@tool(
    "calculate_wacc",
    "Calculate Weighted Average Cost of Capital using CAPM for cost of equity",
    {
        "beta": float,
        "risk_free_rate": float,
        "market_premium": float,
        "debt_ratio": float,
        "cost_of_debt": float,
        "tax_rate": float
    }
)
async def calculate_wacc_tool(args: dict) -> dict:
    """Calculate WACC with given inputs."""
    result = calculate_wacc(
        beta=args["beta"],
        risk_free_rate=args.get("risk_free_rate", 0.045),
        market_premium=args.get("market_premium", 0.055),
        debt_ratio=args.get("debt_ratio", 0.3),
        cost_of_debt=args.get("cost_of_debt", 0.06),
        tax_rate=args.get("tax_rate", 0.21),
    )
    return _mcp_response(result)


@tool(
    "project_free_cash_flows",
    "Project future free cash flows based on growth rate assumptions",
    {"base_fcf": float, "growth_rate": float, "years": int}
)
async def project_fcf_tool(args: dict) -> dict:
    """Project future free cash flows."""
    result = project_free_cash_flows(
        base_fcf=args["base_fcf"],
        growth_rates=args["growth_rate"],
        years=args.get("years", 5),
    )
    return _mcp_response({"projected_fcfs": result})


@tool(
    "calculate_terminal_value",
    "Calculate terminal value using Gordon Growth Model (perpetuity formula)",
    {"final_fcf": float, "perpetual_growth": float, "wacc": float}
)
async def calculate_terminal_value_tool(args: dict) -> dict:
    """Calculate terminal value."""
    result = calculate_terminal_value(
        final_fcf=args["final_fcf"],
        perpetual_growth=args.get("perpetual_growth", 0.025),
        wacc=args["wacc"],
    )
    return _mcp_response({"terminal_value": result})


@tool(
    "calculate_intrinsic_value",
    "Calculate intrinsic value per share by discounting projected FCFs and terminal value",
    {
        "projected_fcfs": list,
        "terminal_value": float,
        "wacc": float,
        "shares_outstanding": float,
        "net_debt": float
    }
)
async def calculate_intrinsic_value_tool(args: dict) -> dict:
    """Calculate intrinsic value per share."""
    result = calculate_intrinsic_value(
        projected_fcfs=args["projected_fcfs"],
        terminal_value=args["terminal_value"],
        wacc=args["wacc"],
        shares_outstanding=args["shares_outstanding"],
        net_debt=args.get("net_debt", 0),
    )
    return _mcp_response(result)


@tool(
    "run_dcf_model",
    "Build a complete DCF valuation model for a company - fetches data and calculates intrinsic value",
    {
        "ticker": str,
        "projection_years": int,
        "terminal_growth_rate": float,
        "risk_free_rate": float,
        "market_premium": float
    }
)
async def run_dcf_model_tool(args: dict) -> dict:
    """Run complete DCF model for a ticker."""
    result = build_dcf_model(
        ticker=args["ticker"],
        projection_years=args.get("projection_years", 5),
        terminal_growth_rate=args.get("terminal_growth_rate", 0.025),
        risk_free_rate=args.get("risk_free_rate", 0.045),
        market_premium=args.get("market_premium", 0.055),
        custom_growth_rate=args.get("custom_growth_rate"),
    )
    return _mcp_response(result)


# =============================================================================
# Aggregated Tool Lists for MCP Server Registration
# =============================================================================

MARKET_DATA_TOOLS = [
    fetch_company_profile_tool,
    fetch_income_statement_tool,
    fetch_balance_sheet_tool,
    fetch_cash_flow_tool,
    fetch_financial_ratios_tool,
    fetch_key_metrics_tool,
    fetch_earnings_history_tool,
    fetch_stock_quote_tool,
    fetch_fmp_dcf_tool,
    fetch_analyst_estimates_tool,
]

DCF_MODEL_TOOLS = [
    calculate_wacc_tool,
    project_fcf_tool,
    calculate_terminal_value_tool,
    calculate_intrinsic_value_tool,
    run_dcf_model_tool,
]

ALL_FINANCIAL_TOOLS = MARKET_DATA_TOOLS + DCF_MODEL_TOOLS


# =============================================================================
# Anthropic API Tool Schemas and Executors
# =============================================================================

def get_anthropic_tool_schemas() -> list[dict]:
    """
    Get tool definitions in Anthropic API format.

    Returns:
        List of tool schemas compatible with Anthropic's messages.create() API.
    """
    return [
        # Market Data Tools
        {
            "name": "fetch_company_profile",
            "description": "Get company profile including industry, sector, market cap, beta, and description",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, TSLA)"}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_income_statement",
            "description": "Get income statements with revenue, net income, EPS, and margins",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_balance_sheet",
            "description": "Get balance sheets with assets, liabilities, equity, and debt levels",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_cash_flow",
            "description": "Get cash flow statements with operating cash flow, CapEx, and free cash flow",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_financial_ratios",
            "description": "Get financial ratios including ROE, ROA, current ratio, and profit margins",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_key_metrics",
            "description": "Get key valuation metrics including PE ratio, EV/EBITDA, ROIC, and per-share values",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_earnings_history",
            "description": "Get historical earnings with actual EPS, estimates, and surprise percentages",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "limit": {"type": "integer", "description": "Number of quarters to fetch", "default": 20}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_stock_quote",
            "description": "Get real-time stock quote with price, volume, market cap, and 52-week range",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_fmp_dcf",
            "description": "Get FMP's pre-calculated DCF valuation for quick reference",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "fetch_analyst_estimates",
            "description": "Get analyst revenue and EPS estimates for future periods",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "Period type: 'annual' or 'quarter'", "default": "annual"},
                    "limit": {"type": "integer", "description": "Number of periods to fetch", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        # DCF Model Tools
        {
            "name": "calculate_wacc",
            "description": "Calculate Weighted Average Cost of Capital using CAPM for cost of equity",
            "input_schema": {
                "type": "object",
                "properties": {
                    "beta": {"type": "number", "description": "Company beta (systematic risk)"},
                    "risk_free_rate": {"type": "number", "description": "Risk-free rate (e.g., 0.045 for 4.5%)", "default": 0.045},
                    "market_premium": {"type": "number", "description": "Equity risk premium (e.g., 0.055 for 5.5%)", "default": 0.055},
                    "debt_ratio": {"type": "number", "description": "Debt to total capital ratio", "default": 0.3},
                    "cost_of_debt": {"type": "number", "description": "Pre-tax cost of debt", "default": 0.06},
                    "tax_rate": {"type": "number", "description": "Corporate tax rate", "default": 0.21}
                },
                "required": ["beta"]
            }
        },
        {
            "name": "project_free_cash_flows",
            "description": "Project future free cash flows based on growth rate assumptions",
            "input_schema": {
                "type": "object",
                "properties": {
                    "base_fcf": {"type": "number", "description": "Base year free cash flow"},
                    "growth_rate": {"type": "number", "description": "Annual growth rate (e.g., 0.10 for 10%)"},
                    "years": {"type": "integer", "description": "Number of years to project", "default": 5}
                },
                "required": ["base_fcf", "growth_rate"]
            }
        },
        {
            "name": "calculate_terminal_value",
            "description": "Calculate terminal value using Gordon Growth Model (perpetuity formula)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "final_fcf": {"type": "number", "description": "Final projected year FCF"},
                    "perpetual_growth": {"type": "number", "description": "Perpetual growth rate (e.g., 0.025 for 2.5%)", "default": 0.025},
                    "wacc": {"type": "number", "description": "Weighted average cost of capital"}
                },
                "required": ["final_fcf", "wacc"]
            }
        },
        {
            "name": "calculate_intrinsic_value",
            "description": "Calculate intrinsic value per share by discounting projected FCFs and terminal value",
            "input_schema": {
                "type": "object",
                "properties": {
                    "projected_fcfs": {"type": "array", "items": {"type": "number"}, "description": "List of projected FCFs"},
                    "terminal_value": {"type": "number", "description": "Terminal value"},
                    "wacc": {"type": "number", "description": "Discount rate (WACC)"},
                    "shares_outstanding": {"type": "number", "description": "Shares outstanding"},
                    "net_debt": {"type": "number", "description": "Net debt (debt minus cash)", "default": 0}
                },
                "required": ["projected_fcfs", "terminal_value", "wacc", "shares_outstanding"]
            }
        },
        {
            "name": "run_dcf_model",
            "description": "Build a complete DCF valuation model for a company - fetches data and calculates intrinsic value",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "projection_years": {"type": "integer", "description": "Years to project", "default": 5},
                    "terminal_growth_rate": {"type": "number", "description": "Terminal growth rate", "default": 0.025},
                    "risk_free_rate": {"type": "number", "description": "Risk-free rate", "default": 0.045},
                    "market_premium": {"type": "number", "description": "Market risk premium", "default": 0.055},
                    "custom_growth_rate": {"type": "number", "description": "Override calculated growth rate"}
                },
                "required": ["ticker"]
            }
        },
        # Custom DCF Tools
        {
            "name": "run_custom_dcf_model",
            "description": "Run a custom DCF valuation with fine-tuned assumptions using FMP's Custom DCF Advanced API. Calculates parameters from historical data or accepts user overrides.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "revenue_growth_pct": {"type": "number", "description": "Override revenue growth % (or auto-calculate)"},
                    "capital_expenditure_pct": {"type": "number", "description": "Override CapEx % of revenue"},
                    "operating_cash_flow_pct": {"type": "number", "description": "Override OCF % of revenue"},
                    "market_risk_premium": {"type": "number", "description": "Override market risk premium %"},
                    "long_term_growth_rate": {"type": "number", "description": "Override terminal growth rate %"},
                    "country": {"type": "string", "description": "Country for ERP/growth rate lookup", "default": "United States"},
                    "periods": {"type": "integer", "description": "Historical periods for calculations", "default": 5}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "calculate_dcf_parameters",
            "description": "Calculate recommended DCF input parameters from historical financial data including revenue growth, CapEx %, OCF %, market risk premium, and long-term growth rate",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "periods": {"type": "integer", "description": "Historical periods for calculations", "default": 5},
                    "country": {"type": "string", "description": "Country for ERP/growth rate lookup", "default": "United States"}
                },
                "required": ["ticker"]
            }
        },
        # CBCV (Customer-Based Corporate Valuation) Tools
        {
            "name": "run_cbcv_model",
            "description": "Run Customer-Based Corporate Valuation for subscription/high-growth companies. Use this instead of DCF for companies with negative FCF but growing customer bases (SOFI, HOOD, NFLX, SPOT). Requires total_customers as input.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "total_customers": {"type": "integer", "description": "Current total customer/subscriber count (REQUIRED)"},
                    "arpu": {"type": "number", "description": "Annual Revenue Per User. If not provided, calculated from revenue/customers"},
                    "churn_rate": {"type": "number", "description": "Annual churn rate (0-1). If not provided, uses industry benchmark"},
                    "cac": {"type": "number", "description": "Customer Acquisition Cost. If not provided, estimated from S&M expense"},
                    "new_customers": {"type": "integer", "description": "New customers added this year. Used for CAC calculation"},
                    "projection_years": {"type": "integer", "description": "Years to project future acquisitions", "default": 10},
                    "tam": {"type": "integer", "description": "Total Addressable Market (customer cap)"}
                },
                "required": ["ticker", "total_customers"]
            }
        },
        {
            "name": "calculate_clv",
            "description": "Calculate Customer Lifetime Value using the subscription CLV formula: CLV = (ARPU × Margin) × (Retention / (1 + WACC - Retention))",
            "input_schema": {
                "type": "object",
                "properties": {
                    "arpu": {"type": "number", "description": "Annual Revenue Per User"},
                    "gross_margin": {"type": "number", "description": "Gross profit margin (0-1, e.g., 0.85 for 85%)"},
                    "retention_rate": {"type": "number", "description": "Annual customer retention rate (0-1, e.g., 0.90 for 90%)"},
                    "discount_rate": {"type": "number", "description": "WACC or required return (0-1, e.g., 0.12 for 12%)"}
                },
                "required": ["arpu", "gross_margin", "retention_rate", "discount_rate"]
            }
        },
        {
            "name": "get_industry_churn_benchmark",
            "description": "Get industry benchmark annual churn rate for a ticker. Returns churn rate and industry classification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        },
    ]


def _serialize_result(data: Any) -> str:
    """Serialize tool execution result to JSON string."""
    if hasattr(data, "to_dict"):
        return json.dumps(data.to_dict(), indent=2)
    elif isinstance(data, (dict, list)):
        return json.dumps(data, indent=2)
    else:
        return str(data)


def _run_custom_dcf_with_params(
    ticker: str,
    revenue_growth_pct: float | None = None,
    capital_expenditure_pct: float | None = None,
    operating_cash_flow_pct: float | None = None,
    market_risk_premium: float | None = None,
    long_term_growth_rate: float | None = None,
    country: str = "United States",
    periods: int = 5,
) -> dict:
    """
    Run custom DCF with auto-calculated parameters for missing values.

    If a parameter is not provided, it will be calculated from historical data.
    Handles FMP API format conversion automatically.
    """
    # Calculate parameters if not provided
    if any(p is None for p in [revenue_growth_pct, capital_expenditure_pct,
                                operating_cash_flow_pct, market_risk_premium,
                                long_term_growth_rate]):
        calculated = calculate_all_dcf_parameters(ticker, periods=periods, country=country)

        if revenue_growth_pct is None:
            revenue_growth_pct = calculated["revenue_growth_pct"]
        if capital_expenditure_pct is None:
            capital_expenditure_pct = calculated["capital_expenditure_pct"]
        if operating_cash_flow_pct is None:
            operating_cash_flow_pct = calculated["operating_cash_flow_pct"]
        if market_risk_premium is None:
            market_risk_premium = calculated["market_risk_premium"]
        if long_term_growth_rate is None:
            long_term_growth_rate = calculated["long_term_growth_rate"]

    # Store original values for transparency in result
    original_params = {
        "revenue_growth_pct": revenue_growth_pct,
        "capital_expenditure_pct": capital_expenditure_pct,
        "operating_cash_flow_pct": operating_cash_flow_pct,
        "market_risk_premium": market_risk_premium,
        "long_term_growth_rate": long_term_growth_rate,
        "country": country,
        "periods": periods,
    }

    # ==========================================================================
    # FMP Custom DCF API Format Conversion
    # ==========================================================================
    # The FMP API expects different formats for different parameter types:
    #
    # 1. Parameters ending in "Pct" (revenueGrowthPct, capitalExpenditurePct, etc.)
    #    → Expect DECIMALS: 0.2478 for 24.78%
    #
    # 2. marketRiskPremium, longTermGrowthRate
    #    → Expect ACTUAL PERCENTAGES: 4.46 for 4.46%, 2.5 for 2.5%
    #
    # Our helper functions return human-readable percentages (24.78 for 24.78%),
    # so we convert "Pct" parameters to decimals by dividing by 100.
    # ==========================================================================

    # Convert "Pct" parameters from percentage (24.78) to decimal (0.2478)
    api_revenue_growth_pct = revenue_growth_pct / 100 if revenue_growth_pct else None
    api_capital_expenditure_pct = capital_expenditure_pct / 100 if capital_expenditure_pct else None
    api_operating_cash_flow_pct = operating_cash_flow_pct / 100 if operating_cash_flow_pct else None

    # Keep marketRiskPremium and longTermGrowthRate as-is (API expects actual %)
    api_market_risk_premium = market_risk_premium
    api_long_term_growth_rate = long_term_growth_rate

    # Call FMP Custom DCF API with converted parameters
    result = get_custom_dcf(
        ticker=ticker,
        revenue_growth_pct=api_revenue_growth_pct,
        capital_expenditure_pct=api_capital_expenditure_pct,
        operating_cash_flow_pct=api_operating_cash_flow_pct,
        market_risk_premium=api_market_risk_premium,
        long_term_growth_rate=api_long_term_growth_rate,
    )

    # Add the original parameters used to the result for transparency
    # (showing human-readable percentages, not API format)
    result["parameters_used"] = original_params

    return result


# Tool executor mapping - maps tool names to execution functions
TOOL_EXECUTORS = {
    # Market Data Tools
    "fetch_company_profile": lambda args: get_company_profile(args["ticker"]),
    "fetch_income_statement": lambda args: get_income_statement(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    "fetch_balance_sheet": lambda args: get_balance_sheet(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    "fetch_cash_flow": lambda args: get_cash_flow(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    "fetch_financial_ratios": lambda args: get_financial_ratios(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    "fetch_key_metrics": lambda args: get_key_metrics(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    "fetch_earnings_history": lambda args: get_earnings_history(
        args["ticker"],
        limit=args.get("limit", 20)
    ),
    "fetch_stock_quote": lambda args: get_quote(args["ticker"]),
    "fetch_fmp_dcf": lambda args: get_dcf(args["ticker"]),
    "fetch_analyst_estimates": lambda args: get_analyst_estimates(
        args["ticker"],
        period=args.get("period", "annual"),
        limit=args.get("limit", 5)
    ),
    # DCF Model Tools
    "calculate_wacc": lambda args: calculate_wacc(
        beta=args["beta"],
        risk_free_rate=args.get("risk_free_rate", 0.045),
        market_premium=args.get("market_premium", 0.055),
        debt_ratio=args.get("debt_ratio", 0.3),
        cost_of_debt=args.get("cost_of_debt", 0.06),
        tax_rate=args.get("tax_rate", 0.21),
    ),
    "project_free_cash_flows": lambda args: {
        "projected_fcfs": project_free_cash_flows(
            base_fcf=args["base_fcf"],
            growth_rates=args["growth_rate"],
            years=args.get("years", 5),
        )
    },
    "calculate_terminal_value": lambda args: {
        "terminal_value": calculate_terminal_value(
            final_fcf=args["final_fcf"],
            perpetual_growth=args.get("perpetual_growth", 0.025),
            wacc=args["wacc"],
        )
    },
    "calculate_intrinsic_value": lambda args: calculate_intrinsic_value(
        projected_fcfs=args["projected_fcfs"],
        terminal_value=args["terminal_value"],
        wacc=args["wacc"],
        shares_outstanding=args["shares_outstanding"],
        net_debt=args.get("net_debt", 0),
    ),
    "run_dcf_model": lambda args: build_dcf_model(
        ticker=args["ticker"],
        projection_years=args.get("projection_years", 5),
        terminal_growth_rate=args.get("terminal_growth_rate", 0.025),
        risk_free_rate=args.get("risk_free_rate", 0.045),
        market_premium=args.get("market_premium", 0.055),
        custom_growth_rate=args.get("custom_growth_rate"),
    ),
    # Custom DCF Tools
    "run_custom_dcf_model": lambda args: _run_custom_dcf_with_params(
        ticker=args["ticker"],
        revenue_growth_pct=args.get("revenue_growth_pct"),
        capital_expenditure_pct=args.get("capital_expenditure_pct"),
        operating_cash_flow_pct=args.get("operating_cash_flow_pct"),
        market_risk_premium=args.get("market_risk_premium"),
        long_term_growth_rate=args.get("long_term_growth_rate"),
        country=args.get("country", "United States"),
        periods=args.get("periods", 5),
    ),
    "calculate_dcf_parameters": lambda args: calculate_all_dcf_parameters(
        ticker=args["ticker"],
        periods=args.get("periods", 5),
        country=args.get("country", "United States"),
    ),
    # CBCV Model Tools
    "run_cbcv_model": lambda args: build_cbcv_model(
        ticker=args["ticker"],
        total_customers=args["total_customers"],
        arpu=args.get("arpu"),
        churn_rate=args.get("churn_rate"),
        cac=args.get("cac"),
        new_customers=args.get("new_customers"),
        projection_years=args.get("projection_years", 10),
        tam=args.get("tam"),
    ),
    "calculate_clv": lambda args: {
        "clv": calculate_clv(
            arpu=args["arpu"],
            gross_margin=args["gross_margin"],
            retention_rate=args["retention_rate"],
            discount_rate=args["discount_rate"],
        ),
        "inputs": {
            "arpu": args["arpu"],
            "gross_margin": args["gross_margin"],
            "retention_rate": args["retention_rate"],
            "discount_rate": args["discount_rate"],
        }
    },
    "get_industry_churn_benchmark": lambda args: {
        "ticker": args["ticker"],
        "industry": get_industry_for_ticker(args["ticker"]),
        "churn_rate": get_churn_rate_benchmark(args["ticker"]),
        "retention_rate": 1 - get_churn_rate_benchmark(args["ticker"]),
    },
}


def execute_tool(name: str, args: dict) -> str:
    """
    Execute a tool by name with given arguments.

    Args:
        name: Tool name
        args: Tool arguments

    Returns:
        JSON string of the result

    Raises:
        ValueError: If tool name is unknown
    """
    if name not in TOOL_EXECUTORS:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = TOOL_EXECUTORS[name](args)
        return _serialize_result(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
