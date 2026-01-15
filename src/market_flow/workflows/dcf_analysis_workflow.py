"""
DCF Analysis Workflow

Orchestrates the complete DCF analysis pipeline:
1. Fetch financial data from FMP
2. Build DCF model
3. Analyze with Claude
4. Generate report and upload to Google Drive
"""

from datetime import datetime
from typing import Callable

from ..market_data.fmp_client import (
    get_company_profile,
    get_income_statement,
    get_earnings_history,
)
from ..models.dcf_model import build_dcf_model, DCFResult
from ..agents.dcf_analyst_agent import analyze_dcf
from ..drive_uploader import upload_to_drive
from ..deep_research import _create_google_doc


def _format_dcf_report(
    ticker: str,
    dcf_result: DCFResult,
    claude_analysis: str,
    profile: dict,
    income_statements: list[dict],
    earnings_history: list[dict],
) -> str:
    """
    Format the complete DCF analysis report for Google Docs.

    Args:
        ticker: Stock ticker symbol
        dcf_result: DCF model results
        claude_analysis: Analysis from Claude
        profile: Company profile from FMP
        income_statements: Historical income statements
        earnings_history: Quarterly earnings data

    Returns:
        Formatted markdown content for the report
    """
    today = datetime.now().strftime("%B %d, %Y")

    # Format historical financials table
    financials_table = "| Year | Revenue | Net Income | EPS |\n"
    financials_table += "|------|---------|------------|-----|\n"
    for stmt in income_statements[:5]:
        year = stmt.get("calendarYear", "N/A")
        revenue = stmt.get("revenue", 0)
        net_income = stmt.get("netIncome", 0)
        eps = stmt.get("epsdiluted", 0)
        financials_table += f"| {year} | ${revenue/1e9:.2f}B | ${net_income/1e9:.2f}B | ${eps:.2f} |\n"

    # Format projected FCF table
    projected_table = "| Year | Projected FCF |\n"
    projected_table += "|------|---------------|\n"
    for i, fcf in enumerate(dcf_result.projected_fcfs):
        projected_table += f"| Year {i+1} | ${fcf/1e6:.1f}M |\n"

    # Format sensitivity matrix
    sensitivity_table = "| WACC \\ Growth |"
    growth_rates = list(list(dcf_result.sensitivity_matrix.values())[0].keys())
    sensitivity_table += " | ".join(growth_rates) + " |\n"
    sensitivity_table += "|" + "---|" * (len(growth_rates) + 1) + "\n"

    for wacc_key, growth_dict in dcf_result.sensitivity_matrix.items():
        row = f"| {wacc_key} |"
        row += " | ".join(f"${v:.2f}" for v in growth_dict.values())
        sensitivity_table += row + " |\n"

    # Format recent earnings
    earnings_table = "| Date | EPS | EPS Est. | Surprise |\n"
    earnings_table += "|------|-----|----------|----------|\n"
    for earn in earnings_history[:8]:
        date = earn.get("date", "N/A")
        eps = earn.get("eps", 0) or 0
        eps_est = earn.get("epsEstimated", 0) or 0
        surprise = ((eps - eps_est) / eps_est * 100) if eps_est else 0
        surprise_str = f"{surprise:+.1f}%" if eps_est else "N/A"
        earnings_table += f"| {date} | ${eps:.2f} | ${eps_est:.2f} | {surprise_str} |\n"

    # Valuation verdict
    if dcf_result.upside_percentage > 20:
        verdict = "UNDERVALUED"
        verdict_color = "significant upside potential"
    elif dcf_result.upside_percentage > 5:
        verdict = "SLIGHTLY UNDERVALUED"
        verdict_color = "modest upside potential"
    elif dcf_result.upside_percentage > -5:
        verdict = "FAIRLY VALUED"
        verdict_color = "trading near intrinsic value"
    elif dcf_result.upside_percentage > -20:
        verdict = "SLIGHTLY OVERVALUED"
        verdict_color = "limited upside potential"
    else:
        verdict = "OVERVALUED"
        verdict_color = "significant downside risk"

    report = f"""# DCF Valuation Analysis: {dcf_result.company_name} ({ticker})

**Report Date:** {today}

---

## Executive Summary

**{dcf_result.company_name}** is currently trading at **${dcf_result.current_price:.2f}** per share. Based on our Discounted Cash Flow analysis, we estimate an intrinsic value of **${dcf_result.intrinsic_value:.2f}** per share, representing a **{dcf_result.upside_percentage:+.1f}%** potential return.

**Valuation Verdict: {verdict}** - The stock appears to have {verdict_color}.

---

## Company Overview

| Metric | Value |
|--------|-------|
| **Company** | {profile.get('companyName', ticker)} |
| **Ticker** | {ticker} |
| **Industry** | {profile.get('industry', 'N/A')} |
| **Sector** | {profile.get('sector', 'N/A')} |
| **Market Cap** | ${profile.get('mktCap', 0)/1e9:.2f}B |
| **Beta** | {profile.get('beta', 'N/A')} |

**Business Description:**
{profile.get('description', 'N/A')[:800]}

---

## Historical Financial Performance

{financials_table}

---

## DCF Model Details

### Key Assumptions

| Assumption | Value |
|------------|-------|
| **WACC** | {dcf_result.wacc:.2%} |
| **Cost of Equity** | {dcf_result.cost_of_equity:.2%} |
| **Cost of Debt (after-tax)** | {dcf_result.cost_of_debt * (1 - dcf_result.tax_rate):.2%} |
| **Debt/Capital** | {dcf_result.debt_weight:.1%} |
| **Tax Rate** | {dcf_result.tax_rate:.1%} |
| **FCF Growth Rate** | {dcf_result.revenue_growth_rate:.1%} |
| **Terminal Growth Rate** | {dcf_result.terminal_growth_rate:.1%} |
| **Projection Period** | {dcf_result.projection_years} years |

### Projected Free Cash Flows

{projected_table}

### Valuation Summary

| Component | Value |
|-----------|-------|
| **Terminal Value** | ${dcf_result.terminal_value/1e9:.2f}B |
| **Enterprise Value** | ${dcf_result.enterprise_value/1e9:.2f}B |
| **Net Debt** | ${dcf_result.net_debt/1e9:.2f}B |
| **Equity Value** | ${(dcf_result.enterprise_value - dcf_result.net_debt)/1e9:.2f}B |
| **Shares Outstanding** | {dcf_result.shares_outstanding/1e6:.1f}M |
| **Intrinsic Value/Share** | ${dcf_result.intrinsic_value:.2f} |

---

## Sensitivity Analysis

The table below shows how the intrinsic value changes with different WACC and terminal growth rate assumptions:

{sensitivity_table}

---

## Recent Earnings History

{earnings_table}

---

## AI-Powered Analysis

{claude_analysis}

---

## Disclaimer

This analysis is for informational purposes only and does not constitute investment advice. The DCF model relies on numerous assumptions that may not reflect actual future performance. Past performance is not indicative of future results. Always conduct your own due diligence before making investment decisions.

---

*Generated by Market Flow DCF Analysis Workflow*
"""

    return report


def run_dcf_analysis(
    ticker: str,
    drive_folder_id: str | None = None,
    projection_years: int = 5,
    terminal_growth_rate: float = 0.025,
    credentials_path: str = "credentials.json",
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """
    Run the complete DCF analysis workflow.

    This workflow:
    1. Fetches financial data from Financial Modeling Prep
    2. Builds a DCF valuation model
    3. Uses Claude to analyze the model and provide insights
    4. Generates a formatted report
    5. Uploads to Google Drive as a Google Doc

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "HOOD")
        drive_folder_id: Google Drive folder ID to upload to (None = root)
        projection_years: Number of years to project (default: 5)
        terminal_growth_rate: Long-term growth rate (default: 2.5%)
        credentials_path: Path to Google OAuth credentials
        on_status: Optional callback for status updates

    Returns:
        dict with:
            - ticker: Stock ticker
            - intrinsic_value: Calculated intrinsic value per share
            - current_price: Current stock price
            - upside_percentage: Potential upside/downside
            - google_doc_url: URL to the generated Google Doc
            - dcf_result: Full DCFResult object
    """
    ticker = ticker.upper()

    def _status(msg: str):
        if on_status:
            on_status(msg)

    _status(f"Starting DCF analysis for {ticker}...")

    # Step 1: Fetch company data
    _status("Fetching company profile...")
    profile = get_company_profile(ticker)

    _status("Fetching income statements...")
    income_statements = get_income_statement(ticker, period="annual", limit=5)

    _status("Fetching earnings history...")
    earnings_history = get_earnings_history(ticker, limit=20)

    # Step 2: Build DCF model
    _status("Building DCF model...")
    dcf_result = build_dcf_model(
        ticker=ticker,
        projection_years=projection_years,
        terminal_growth_rate=terminal_growth_rate,
    )
    _status(f"DCF complete: Intrinsic value = ${dcf_result.intrinsic_value:.2f}")

    # Step 3: Claude analysis
    _status("Running AI analysis with Claude...")
    claude_analysis = analyze_dcf(
        dcf_result=dcf_result,
        company_context={"profile": profile},
    )
    _status("AI analysis complete")

    # Step 4: Generate report
    _status("Generating report...")
    report_content = _format_dcf_report(
        ticker=ticker,
        dcf_result=dcf_result,
        claude_analysis=claude_analysis,
        profile=profile,
        income_statements=income_statements,
        earnings_history=earnings_history,
    )

    # Step 5: Upload to Google Drive
    _status("Creating Google Doc...")
    doc_title = f"DCF Analysis - {dcf_result.company_name} ({ticker})"
    doc_url = _create_google_doc(
        title=doc_title,
        content=report_content,
        credentials_path=credentials_path,
    )
    _status(f"Google Doc created: {doc_url}")

    return {
        "ticker": ticker,
        "company_name": dcf_result.company_name,
        "intrinsic_value": dcf_result.intrinsic_value,
        "current_price": dcf_result.current_price,
        "upside_percentage": dcf_result.upside_percentage,
        "google_doc_url": doc_url,
        "dcf_result": dcf_result,
    }
