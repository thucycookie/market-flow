"""
Company Analysis Workflow Example

This example demonstrates the full company analysis workflow that:
1. Runs industry analysis and financial modeling in parallel
2. Uploads results to Google Drive
3. Runs synthesis analysis with context from the previous research

Before running, ensure you have:
1. Set GOOGLE_API_KEY environment variable (for Gemini API)
2. Downloaded OAuth credentials from Google Cloud Console (for Google Docs)
3. Run `gcloud auth application-default login` (for Google Drive)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from market_flow import run_company_analysis_sync

# Load environment variables from .env file
load_dotenv()


def status_callback(stage: str, status: str):
    """Print status updates from the workflow."""
    print(f"[{stage}] {status}")


def example_company_analysis():
    """Run the complete company analysis workflow."""
    print("=== Company Analysis Workflow ===\n")

    # Create output directory
    output_dir = Path("./analysis_output")

    # Optional: specify a Google Drive folder ID to organize outputs
    # You can find this in the folder URL: https://drive.google.com/drive/folders/{FOLDER_ID}
    drive_folder_id = os.getenv("DRIVE_FOLDER_ID")  # Set in .env or leave as None

    results = run_company_analysis_sync(
        company_name="Apple",  # Change to any company you want to analyze
        output_dir=output_dir,
        drive_folder_id=drive_folder_id,
        on_status=status_callback,
    )

    print("\n=== Results ===")
    print(f"Industry Analysis PDF: {results['industry_analysis']}")
    print(f"Financial Modeling PDF: {results['financial_modeling']}")
    print(f"Synthesis PDF: {results['synthesis']}")
    print(f"\nGoogle Drive URLs:")
    print(f"  Industry: {results['industry_drive_url']}")
    print(f"  Financial: {results['financial_drive_url']}")
    print(f"  Synthesis: {results['synthesis_drive_url']}")


async def example_company_analysis_async():
    """Run the workflow asynchronously (useful for integration with async code)."""
    from market_flow import run_company_analysis

    print("=== Async Company Analysis Workflow ===\n")

    output_dir = Path("./analysis_output")

    results = await run_company_analysis(
        company_name="Tesla",
        output_dir=output_dir,
        on_status=status_callback,
    )

    print("\n=== Results ===")
    for key, value in results.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    # Run the synchronous example
    example_company_analysis()

    # For async example, uncomment:
    # import asyncio
    # asyncio.run(example_company_analysis_async())
