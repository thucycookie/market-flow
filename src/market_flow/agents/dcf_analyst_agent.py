"""
DCF Analyst Agent

Uses Claude to analyze DCF model results and provide investment insights.
"""

import os
from typing import Any

import anthropic

from ..models.dcf_model import DCFResult


def _format_dcf_for_prompt(dcf_result: DCFResult) -> str:
    """Format DCF results for the Claude prompt."""
    historical_fcf_str = "\n".join(
        f"  - {h['year']}: ${h['fcf']:,.0f}"
        for h in dcf_result.historical_fcf
    )

    projected_fcf_str = "\n".join(
        f"  - Year {i+1}: ${fcf:,.0f}"
        for i, fcf in enumerate(dcf_result.projected_fcfs)
    )

    sensitivity_str = ""
    for wacc_key, growth_dict in dcf_result.sensitivity_matrix.items():
        row = f"  WACC {wacc_key}: "
        row += ", ".join(f"g={g}: ${v}" for g, v in growth_dict.items())
        sensitivity_str += row + "\n"

    return f"""
COMPANY: {dcf_result.company_name} ({dcf_result.ticker})

CURRENT VALUATION:
- Current Stock Price: ${dcf_result.current_price:.2f}
- Intrinsic Value (DCF): ${dcf_result.intrinsic_value:.2f}
- Upside/Downside: {dcf_result.upside_percentage:+.1f}%

WACC COMPONENTS:
- WACC: {dcf_result.wacc:.2%}
- Cost of Equity: {dcf_result.cost_of_equity:.2%}
- Cost of Debt (after-tax): {dcf_result.cost_of_debt * (1 - dcf_result.tax_rate):.2%}
- Debt Weight: {dcf_result.debt_weight:.1%}
- Equity Weight: {dcf_result.equity_weight:.1%}
- Tax Rate: {dcf_result.tax_rate:.1%}

GROWTH ASSUMPTIONS:
- Revenue/FCF Growth Rate: {dcf_result.revenue_growth_rate:.1%}
- Terminal Growth Rate: {dcf_result.terminal_growth_rate:.1%}
- Projection Period: {dcf_result.projection_years} years

HISTORICAL FREE CASH FLOW:
{historical_fcf_str}

PROJECTED FREE CASH FLOW:
{projected_fcf_str}

TERMINAL VALUE: ${dcf_result.terminal_value:,.0f}
ENTERPRISE VALUE: ${dcf_result.enterprise_value:,.0f}
NET DEBT: ${dcf_result.net_debt:,.0f}
SHARES OUTSTANDING: {dcf_result.shares_outstanding:,.0f}

SENSITIVITY ANALYSIS (Intrinsic Value per Share):
{sensitivity_str}
"""


def analyze_dcf(
    dcf_result: DCFResult,
    company_context: dict | None = None,
    api_key: str | None = None,
) -> str:
    """
    Use Claude to analyze DCF model results.

    Args:
        dcf_result: DCFResult from build_dcf_model()
        company_context: Optional additional context (profile, financials)
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

    Returns:
        Detailed analysis text from Claude
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Get your API key from https://console.anthropic.com/"
        )

    client = anthropic.Anthropic(api_key=api_key)

    dcf_summary = _format_dcf_for_prompt(dcf_result)

    context_str = ""
    if company_context:
        if "profile" in company_context:
            profile = company_context["profile"]
            context_str += f"""
COMPANY PROFILE:
- Industry: {profile.get('industry', 'N/A')}
- Sector: {profile.get('sector', 'N/A')}
- Market Cap: ${profile.get('mktCap', 0):,.0f}
- Beta: {profile.get('beta', 'N/A')}
- Description: {profile.get('description', 'N/A')[:500]}...
"""

    system_prompt = """You are a senior equity research analyst with expertise in DCF valuation and investment analysis. Your role is to:

1. Critically evaluate the DCF model assumptions and methodology
2. Identify strengths and weaknesses in the valuation
3. Assess key risks and opportunities
4. Provide a clear investment recommendation

Be specific and quantitative in your analysis. Reference actual numbers from the model.
Use professional financial language but remain accessible."""

    user_prompt = f"""Please analyze the following DCF valuation model and provide your investment thesis.

{dcf_summary}
{context_str}

Please structure your analysis as follows:

## Executive Summary
A 2-3 sentence overview of your investment recommendation.

## DCF Model Assessment
- Are the growth rate assumptions reasonable given historical performance?
- Is the WACC calculation appropriate for this company's risk profile?
- How sensitive is the valuation to key assumptions?

## Key Risks
Identify the top 3-5 risks that could cause the intrinsic value to be lower than calculated.

## Upside Catalysts
Identify potential catalysts that could drive the stock price toward or beyond the intrinsic value.

## Investment Recommendation
Provide a clear BUY, HOLD, or SELL recommendation with price targets and rationale.

## Model Limitations
Note any limitations or areas where additional analysis would be valuable.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        system=system_prompt,
    )

    return message.content[0].text
