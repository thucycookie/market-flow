"""
Financial Models Module

This module contains financial modeling calculations:
- DCF (Discounted Cash Flow) - for mature, FCF-positive companies
- CBCV (Customer-Based Corporate Valuation) - for high-growth, customer-centric companies
"""

from .dcf_model import (
    calculate_wacc,
    project_free_cash_flows,
    calculate_terminal_value,
    calculate_intrinsic_value,
    build_dcf_model,
    DCFResult,
)

from .cbcv_model import (
    calculate_clv,
    calculate_cac,
    calculate_existing_customer_equity,
    calculate_future_customer_equity,
    build_cbcv_model,
    get_churn_rate_benchmark,
    get_industry_for_ticker,
    CBCVResult,
    INDUSTRY_CHURN_RATES,
    TICKER_INDUSTRY_MAP,
)

__all__ = [
    # DCF Model
    "calculate_wacc",
    "project_free_cash_flows",
    "calculate_terminal_value",
    "calculate_intrinsic_value",
    "build_dcf_model",
    "DCFResult",
    # CBCV Model
    "calculate_clv",
    "calculate_cac",
    "calculate_existing_customer_equity",
    "calculate_future_customer_equity",
    "build_cbcv_model",
    "get_churn_rate_benchmark",
    "get_industry_for_ticker",
    "CBCVResult",
    "INDUSTRY_CHURN_RATES",
    "TICKER_INDUSTRY_MAP",
]
