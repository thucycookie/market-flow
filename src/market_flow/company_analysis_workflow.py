"""
Company Analysis Workflow

This module orchestrates a multi-stage deep research workflow for comprehensive
company analysis combining industry trends and financial modeling.

Workflow:
1. Industry Analysis - Analyzes the industry context for the company
2. Financial Modeling - Builds forecasts using DCF, LBO, and Driver-Based models
3. Synthesis - Combines insights from (1) and (2) to identify contradictions,
   construct narratives, and surface uncovered signals
"""

import asyncio
from pathlib import Path
from typing import Callable

from .deep_research import research_async
from .drive_uploader import upload_to_drive
from .document_store import create_store, upload_files, delete_store


def _build_industry_prompt(company_name: str) -> str:
    """Build the industry analysis prompt."""
    return f"""You are a senior sector analyst. Your job is to analyze the current industry trend that company {company_name} operates in. The lens that we should consider are:

1. Macro dynamics - What are the key macroeconomic factors affecting this industry?
2. Pain points - What are the major challenges and pain points in this industry?
3. Business models - What are the prevalent business models?
4. Value chain - How does the value chain work and where does {company_name} fit?

Provide a comprehensive industry analysis with actionable insights."""


def _build_financial_prompt(company_name: str) -> str:
    """Build the financial modeling prompt."""
    return f"""You are a private equity associate with deep knowledge about {company_name}. Your job is to:

1. Pull recent earnings data and key financial metrics
2. Build forecast models using:
   - DCF (Discounted Cash Flow) Analysis
   - LBO (Leveraged Buyout) Model
   - Driver-Based Model

3. Determine the company's 3-5 years trajectory based on these models

Provide detailed financial projections with supporting assumptions and sensitivity analysis."""


def _build_synthesis_prompt(company_name: str) -> str:
    """Build the synthesis prompt that combines industry and financial analysis."""
    return f"""You are a senior investment analyst synthesizing research on {company_name}. Based on the industry analysis document and the financial forecast document provided:

a) Identify where in the financial data does it contradict with the overall industry trend? Highlight specific metrics or projections that don't align with industry dynamics.

b) How can we use the financial forecast data to construct a cohesive industry narrative? Connect the company's projected performance to broader industry movements.

c) Is there anything in the industry trend that is not covered by the financial modeling that can be a significant signal in determining the company's financial health? Identify blind spots and potential risks or opportunities not captured in the models.

Provide a comprehensive synthesis with clear recommendations for investment decision-making."""


async def run_company_analysis(
    company_name: str,
    output_dir: str | Path | None = None,
    drive_folder_id: str | None = None,
    api_key: str | None = None,
    credentials_path: str = "credentials.json",
    on_status: Callable[[str, str], None] | None = None,
) -> dict:
    """
    Run the complete company analysis workflow.

    This workflow executes three stages:
    1. Industry analysis (parallel with step 2)
    2. Financial modeling (parallel with step 1)
    3. Synthesis analysis (after 1 & 2 complete, with access to their outputs)

    Args:
        company_name: The name of the company to analyze (e.g., "Apple", "Tesla")
        output_dir: Directory to save PDF outputs. Defaults to current directory.
        drive_folder_id: Optional Google Drive folder ID to upload files to.
                        If None, uploads to Drive root.
        api_key: Google AI API key. Defaults to GOOGLE_API_KEY env var.
        credentials_path: Path to OAuth credentials JSON for Google APIs.
        on_status: Optional callback for status updates. Receives (stage, status).

    Returns:
        dict with keys:
            - industry_analysis: Path to industry analysis PDF
            - financial_modeling: Path to financial modeling PDF
            - synthesis: Path to synthesis PDF
            - industry_drive_url: Google Drive URL for industry analysis
            - financial_drive_url: Google Drive URL for financial modeling
            - synthesis_drive_url: Google Drive URL for synthesis (if uploaded)

    Raises:
        ValueError: If company_name is empty
        RuntimeError: If any research stage fails
    """
    if not company_name or not company_name.strip():
        raise ValueError("company_name is required")

    company_name = company_name.strip()
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    def _status(stage: str, status: str):
        if on_status:
            on_status(stage, status)

    # Define output paths
    industry_path = output_dir / f"{company_name.lower().replace(' ', '_')}_industry_analysis.pdf"
    financial_path = output_dir / f"{company_name.lower().replace(' ', '_')}_financial_modeling.pdf"
    synthesis_path = output_dir / f"{company_name.lower().replace(' ', '_')}_synthesis.pdf"

    results = {}

    # Stage 1 & 2: Run industry analysis and financial modeling in parallel
    _status("parallel_research", "Starting industry analysis and financial modeling...")

    async def run_industry_analysis():
        _status("industry", "Starting industry analysis...")
        result = await research_async(
            prompt=_build_industry_prompt(company_name),
            output_format="pdf",
            output_path=str(industry_path),
            api_key=api_key,
            credentials_path=credentials_path,
            on_status=lambda s: _status("industry", s),
        )
        _status("industry", "Industry analysis complete")
        return result

    async def run_financial_modeling():
        _status("financial", "Starting financial modeling...")
        result = await research_async(
            prompt=_build_financial_prompt(company_name),
            output_format="pdf",
            output_path=str(financial_path),
            api_key=api_key,
            credentials_path=credentials_path,
            on_status=lambda s: _status("financial", s),
        )
        _status("financial", "Financial modeling complete")
        return result

    # Execute both research tasks concurrently
    industry_result, financial_result = await asyncio.gather(
        run_industry_analysis(),
        run_financial_modeling(),
    )

    results["industry_analysis"] = industry_result
    results["financial_modeling"] = financial_result

    # Upload results to Google Drive for the synthesis stage
    _status("upload", "Uploading research outputs to Google Drive...")

    industry_drive = upload_to_drive(
        file_path=industry_result,
        folder_id=drive_folder_id,
        convert_to_doc=True,  # Convert PDF to Google Doc for better text extraction
        delete_local=False,
        file_name=f"{company_name} - Industry Analysis",
    )
    results["industry_drive_url"] = industry_drive["url"]
    _status("upload", f"Industry analysis uploaded: {industry_drive['url']}")

    financial_drive = upload_to_drive(
        file_path=financial_result,
        folder_id=drive_folder_id,
        convert_to_doc=True,
        delete_local=False,
        file_name=f"{company_name} - Financial Modeling",
    )
    results["financial_drive_url"] = financial_drive["url"]
    _status("upload", f"Financial modeling uploaded: {financial_drive['url']}")

    # Stage 3: Run synthesis analysis with context from uploaded files
    _status("synthesis", "Creating file store for synthesis...")

    # Create a file store and upload the PDFs for context
    store_name = create_store(
        name=f"{company_name} Analysis Context",
        api_key=api_key,
    )

    try:
        # Upload the PDF files to the store
        upload_files(
            store_name=store_name,
            file_paths=[industry_result, financial_result],
            api_key=api_key,
        )
        _status("synthesis", "Files uploaded to context store")

        # Run synthesis research with file context
        _status("synthesis", "Starting synthesis analysis...")
        synthesis_result = await research_async(
            prompt=_build_synthesis_prompt(company_name),
            file_store_names=[store_name],
            output_format="pdf",
            output_path=str(synthesis_path),
            api_key=api_key,
            credentials_path=credentials_path,
            on_status=lambda s: _status("synthesis", s),
        )
        _status("synthesis", "Synthesis analysis complete")
        results["synthesis"] = synthesis_result

        # Optionally upload synthesis to Drive as well
        synthesis_drive = upload_to_drive(
            file_path=synthesis_result,
            folder_id=drive_folder_id,
            convert_to_doc=True,
            delete_local=False,
            file_name=f"{company_name} - Synthesis Analysis",
        )
        results["synthesis_drive_url"] = synthesis_drive["url"]
        _status("upload", f"Synthesis uploaded: {synthesis_drive['url']}")

    finally:
        # Clean up the file store
        _status("cleanup", "Cleaning up file store...")
        delete_store(store_name, api_key=api_key)

    _status("complete", "Workflow complete!")
    return results


def run_company_analysis_sync(
    company_name: str,
    output_dir: str | Path | None = None,
    drive_folder_id: str | None = None,
    api_key: str | None = None,
    credentials_path: str = "credentials.json",
    on_status: Callable[[str, str], None] | None = None,
) -> dict:
    """
    Synchronous wrapper for run_company_analysis.

    See run_company_analysis for full documentation.
    """
    return asyncio.run(
        run_company_analysis(
            company_name=company_name,
            output_dir=output_dir,
            drive_folder_id=drive_folder_id,
            api_key=api_key,
            credentials_path=credentials_path,
            on_status=on_status,
        )
    )
