"""
Market Data Module

This module contains clients for fetching financial data from various sources.
"""

from .fmp_client import (
    get_company_profile,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_financial_ratios,
    get_key_metrics,
    get_earnings_history,
)

__all__ = [
    "get_company_profile",
    "get_income_statement",
    "get_balance_sheet",
    "get_cash_flow",
    "get_financial_ratios",
    "get_key_metrics",
    "get_earnings_history",
]
