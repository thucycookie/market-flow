"""
AI Agents Module

This module contains AI-powered analysis agents using Claude and other LLMs.
"""

# Modeling Agent (main agent class)
from .modeling_agent import (
    FinancialModelingAgent,
    analyze_company,
    analyze_dcf,  # Legacy backward-compatible function
    FINANCIAL_ANALYST_SYSTEM_PROMPT,
)

# Boss Agent (supervisor/reviewer)
from .boss_agent import (
    BossAgent,
    BOSS_AGENT_FINANCIAL_MODELING_PROMPT,
)

# MCP Server
from .mcp_server import (
    create_financial_modeling_server,
    TOOL_NAMES,
    ALL_TOOL_NAMES,
)

# Financial Tools
from .financial_tools import (
    # Market Data Tools
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
    # DCF Model Tools
    calculate_wacc_tool,
    project_fcf_tool,
    calculate_terminal_value_tool,
    calculate_intrinsic_value_tool,
    run_dcf_model_tool,
    # Tool collections
    MARKET_DATA_TOOLS,
    DCF_MODEL_TOOLS,
    ALL_FINANCIAL_TOOLS,
    # Anthropic API tool support
    get_anthropic_tool_schemas,
    execute_tool,
    TOOL_EXECUTORS,
)

__all__ = [
    # Modeling Agent
    "FinancialModelingAgent",
    "analyze_company",
    "analyze_dcf",
    "FINANCIAL_ANALYST_SYSTEM_PROMPT",
    # Boss Agent
    "BossAgent",
    "BOSS_AGENT_FINANCIAL_MODELING_PROMPT",
    # MCP Server
    "create_financial_modeling_server",
    "TOOL_NAMES",
    "ALL_TOOL_NAMES",
    # Market Data Tools
    "fetch_company_profile_tool",
    "fetch_income_statement_tool",
    "fetch_balance_sheet_tool",
    "fetch_cash_flow_tool",
    "fetch_financial_ratios_tool",
    "fetch_key_metrics_tool",
    "fetch_earnings_history_tool",
    "fetch_stock_quote_tool",
    "fetch_fmp_dcf_tool",
    "fetch_analyst_estimates_tool",
    # DCF Model Tools
    "calculate_wacc_tool",
    "project_fcf_tool",
    "calculate_terminal_value_tool",
    "calculate_intrinsic_value_tool",
    "run_dcf_model_tool",
    # Tool collections
    "MARKET_DATA_TOOLS",
    "DCF_MODEL_TOOLS",
    "ALL_FINANCIAL_TOOLS",
    # Anthropic API tool support
    "get_anthropic_tool_schemas",
    "execute_tool",
    "TOOL_EXECUTORS",
]
