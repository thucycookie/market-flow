"""
Agents Workflow

Orchestrates the BossAgent and FinancialModelingAgent in a feedback loop.
The modeling agent analyzes a ticker, boss agent reviews, and refinement
continues until approved or MAX_ITERATIONS is reached.

Once approved or max iterations reached, the workflow generates a PDF report and uploads it to Google Drive.
"""

import os
import tempfile
from datetime import datetime
from typing import Callable

from ..agents import FinancialModelingAgent, BossAgent
from ..deep_research import _generate_pdf
from ..drive_uploader import upload_to_drive as drive_upload

# Google Drive folder IDs for traceability uploads
MODELING_AGENT_FOLDER_ID = "1hw8m16wtxB4kTuoLil2y2jBhiOTvkxVQ"
BOSS_AGENT_FOLDER_ID = "1EW4zT647OMevTW8Si3EBMptSOHtI_WOI"


def _upload_analysis_to_drive(
    content: str,
    ticker: str,
    folder_id: str,
    label: str = "analysis",
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """
    Generate PDF from content and upload to Google Drive, then delete local file.

    Args:
        content: The analysis text to upload
        ticker: Stock ticker for naming
        folder_id: Google Drive folder ID
        label: Label for the file (e.g., "initial_analysis", "refinement_1")
        on_status: Optional status callback

    Returns:
        dict with 'url' key containing the Google Drive URL
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{ticker.upper()}_{label}_{timestamp}.pdf"
    pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)

    _generate_pdf(content, pdf_path)

    if on_status:
        on_status(f"Uploading {label.replace('_', ' ')} to Drive...")

    drive_result = drive_upload(
        file_path=pdf_path,
        folder_id=folder_id,
        convert_to_doc=True,
        delete_local=True,  # Clean up local PDF after upload
        file_name=f"{ticker.upper()} {label.replace('_', ' ').title()} - {timestamp}"
    )

    return {"url": drive_result["url"]}


async def run_agents_workflow(
    ticker: str,
    folder_id: str | None = None,
    upload_to_drive: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """
    Run the complete agents workflow with feedback loop.

    This workflow:
    1. Uses FinancialModelingAgent to analyze a ticker
    2. BossAgent reviews the output and provides feedback
    3. If not approved, modeling agent refines based on feedback
    4. Loop continues until approved or MAX_ITERATIONS reached
    5. Generate PDF and upload to Google Drive (if upload_to_drive=True)

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
        folder_id: Google Drive folder ID to upload to. If None, uploads to root.
        upload_to_drive: Whether to upload the final report to Google Drive (default: True)
        on_status: Optional callback for status updates

    Returns:
        dict with:
            - ticker: Stock ticker
            - final_analysis: The approved or final analysis text
            - approved: Whether the boss approved the final analysis
            - iterations: Number of review iterations performed
            - review_history: List of review results from each iteration
            - drive_url: URL to the Google Drive file (if uploaded)
            - pdf_path: None (local files are deleted after upload)
            - analysis_urls: List of intermediate analysis uploads for traceability

    Example:
        >>> import asyncio
        >>> async def main():
        ...     result = await run_agents_workflow("AAPL")
        ...     print(f"Approved: {result['approved']}")
        ...     print(f"Drive URL: {result['drive_url']}")
        >>> asyncio.run(main())
    """
    def _status(msg: str):
        if on_status:
            on_status(msg)

    modeling_agent = FinancialModelingAgent()
    boss_agent = BossAgent()

    # Step 1: Initial analysis
    _status(f"Running initial analysis for {ticker}...")
    result = await modeling_agent.analyze(ticker)
    current_analysis = result["analysis"]

    # Upload initial analysis for traceability
    analysis_urls = []
    initial_upload = _upload_analysis_to_drive(
        content=current_analysis,
        ticker=ticker,
        folder_id=MODELING_AGENT_FOLDER_ID,
        label="initial_analysis",
        on_status=_status,
    )
    analysis_urls.append({"iteration": 0, "type": "initial", "url": initial_upload["url"]})

    review_history = []
    iteration = 0

    # Step 2-3: Review and refine loop
    while iteration < BossAgent.MAX_ITERATIONS:
        iteration += 1
        _status(f"Boss reviewing analysis (iteration {iteration}/{BossAgent.MAX_ITERATIONS})...")

        # Review current analysis
        review = await boss_agent._review_analyst_report(
            current_analysis,
            "financial_modeling"
        )
        review_history.append(review)

        if review["approved"]:
            _status(f"Analysis approved on iteration {iteration}!")
            break

        # Check if we can refine (not at max iterations)
        if iteration >= BossAgent.MAX_ITERATIONS:
            _status(f"Max iterations reached. Returning final analysis.")
            break

        # Refine based on feedback
        _status(f"Refining analysis based on feedback...")
        refined = await modeling_agent.refine(
            ticker,
            review["feedback"],
            current_analysis
        )
        current_analysis = refined["analysis"]

        # Upload refinement for traceability
        refinement_upload = _upload_analysis_to_drive(
            content=current_analysis,
            ticker=ticker,
            folder_id=MODELING_AGENT_FOLDER_ID,
            label=f"refinement_iteration_{iteration}",
            on_status=_status,
        )
        analysis_urls.append({"iteration": iteration, "type": "refinement", "url": refinement_upload["url"]})

    # Build result dict
    workflow_result = {
        "ticker": ticker.upper(),
        "final_analysis": current_analysis,
        "approved": review_history[-1]["approved"] if review_history else False,
        "iterations": iteration,
        "review_history": review_history,
        "drive_url": None,
        "pdf_path": None,
        "analysis_urls": analysis_urls,
    }

    # Generate PDF and upload (either approved or max iterations reached)
    if upload_to_drive:
        status_prefix = "approved" if workflow_result["approved"] else "max iterations reached"
        _status(f"Generating PDF report ({status_prefix})...")

        # Generate PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{ticker.upper()}_analysis_{timestamp}.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)

        _generate_pdf(current_analysis, pdf_path)

        _status("Uploading to Google Drive...")

        # Upload to Drive
        drive_result = drive_upload(
            file_path=pdf_path,
            folder_id=folder_id,
            convert_to_doc=True,
            delete_local=True,  # Clean up local PDF after upload
            file_name=f"{ticker.upper()} Financial Analysis - {timestamp}"
        )

        workflow_result["drive_url"] = drive_result["url"]
        _status(f"Report uploaded: {drive_result['url']}")

    return workflow_result


def run_agents_workflow_sync(
    ticker: str,
    folder_id: str | None = None,
    upload_to_drive: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """
    Synchronous wrapper for run_agents_workflow.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
        folder_id: Google Drive folder ID to upload to. If None, uploads to root.
        upload_to_drive: Whether to upload the final report to Google Drive (default: True)
        on_status: Optional callback for status updates

    Returns:
        Same as run_agents_workflow

    Example:
        >>> result = run_agents_workflow_sync("AAPL")
        >>> print(f"Approved: {result['approved']}")
    """
    import asyncio
    return asyncio.run(run_agents_workflow(ticker, folder_id, upload_to_drive, on_status))
