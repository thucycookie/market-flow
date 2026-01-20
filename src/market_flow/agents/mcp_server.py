"""
MCP Server for Financial Modeling Tools

Creates an in-process MCP server that bundles all financial modeling tools
for use with the Claude Agent SDK.
"""

from claude_agent_sdk import create_sdk_mcp_server

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
    # Collections
    ALL_FINANCIAL_TOOLS,
)


def create_financial_modeling_server():
    """
    Create the MCP server with all financial modeling tools.

    Returns:
        McpSdkServerConfig: Configuration object for ClaudeAgentOptions.mcp_servers

    Example:
        >>> from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        >>> server = create_financial_modeling_server()
        >>> options = ClaudeAgentOptions(
        ...     mcp_servers={"finance": server},
        ...     allowed_tools=[
        ...         "mcp__finance__fetch_company_profile",
        ...         "mcp__finance__run_dcf_model",
        ...     ]
        ... )
    """
    return create_sdk_mcp_server(
        name="financial_modeling",
        version="1.0.0",
        tools=ALL_FINANCIAL_TOOLS,
    )


# Tool name constants for easy reference in allowed_tools
# Format: mcp__{server_name}__{tool_name}
TOOL_NAMES = {
    # Market Data
    "fetch_company_profile": "mcp__financial_modeling__fetch_company_profile",
    "fetch_income_statement": "mcp__financial_modeling__fetch_income_statement",
    "fetch_balance_sheet": "mcp__financial_modeling__fetch_balance_sheet",
    "fetch_cash_flow": "mcp__financial_modeling__fetch_cash_flow",
    "fetch_financial_ratios": "mcp__financial_modeling__fetch_financial_ratios",
    "fetch_key_metrics": "mcp__financial_modeling__fetch_key_metrics",
    "fetch_earnings_history": "mcp__financial_modeling__fetch_earnings_history",
    "fetch_stock_quote": "mcp__financial_modeling__fetch_stock_quote",
    "fetch_fmp_dcf": "mcp__financial_modeling__fetch_fmp_dcf",
    "fetch_analyst_estimates": "mcp__financial_modeling__fetch_analyst_estimates",
    # DCF Model
    "calculate_wacc": "mcp__financial_modeling__calculate_wacc",
    "project_free_cash_flows": "mcp__financial_modeling__project_free_cash_flows",
    "calculate_terminal_value": "mcp__financial_modeling__calculate_terminal_value",
    "calculate_intrinsic_value": "mcp__financial_modeling__calculate_intrinsic_value",
    "run_dcf_model": "mcp__financial_modeling__run_dcf_model",
}

# List of all tool names for convenience
ALL_TOOL_NAMES = list(TOOL_NAMES.values())
