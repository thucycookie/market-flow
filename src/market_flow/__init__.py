"""
Market Flow - Financial Analysis and Research Automation

A Python module for financial data analysis, DCF modeling, and AI-powered research
with Google Docs and Drive integration.
"""

# Core modules
from market_flow.document_store import (
    create_store,
    upload_google_docs,
    upload_files,
    delete_store,
    list_stores,
    fetch_google_doc_content,
    extract_doc_id,
)

from market_flow.deep_research import (
    research,
    research_async,
    research_stream,
)

from market_flow.drive_uploader import (
    upload_to_drive,
    list_files_in_folder,
    delete_from_drive,
)

# Market Data
from market_flow.market_data import (
    get_company_profile,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_financial_ratios,
    get_key_metrics,
    get_earnings_history,
)

# Models
from market_flow.models import (
    build_dcf_model,
    calculate_wacc,
    DCFResult,
)

# Agents
from market_flow.agents import (
    analyze_dcf,
)

# Workflows
from market_flow.workflows import (
    run_company_analysis,
    run_company_analysis_sync,
    run_dcf_analysis,
)

__version__ = "0.1.0"

__all__ = [
    # Document Store
    "create_store",
    "upload_google_docs",
    "upload_files",
    "delete_store",
    "list_stores",
    "fetch_google_doc_content",
    "extract_doc_id",
    # Deep Research
    "research",
    "research_async",
    "research_stream",
    # Drive Uploader
    "upload_to_drive",
    "list_files_in_folder",
    "delete_from_drive",
    # Market Data (FMP)
    "get_company_profile",
    "get_income_statement",
    "get_balance_sheet",
    "get_cash_flow",
    "get_financial_ratios",
    "get_key_metrics",
    "get_earnings_history",
    # Models
    "build_dcf_model",
    "calculate_wacc",
    "DCFResult",
    # Agents
    "analyze_dcf",
    # Workflows
    "run_company_analysis",
    "run_company_analysis_sync",
    "run_dcf_analysis",
]
