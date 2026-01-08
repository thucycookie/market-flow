"""
Basic usage examples for Market Flow.

Before running, ensure you have:
1. Set GOOGLE_API_KEY environment variable (for Gemini API)
2. Downloaded OAuth credentials from Google Cloud Console (for Google Docs)
"""

import os
from dotenv import load_dotenv

from market_flow import (
    create_store,
    upload_google_docs,
    delete_store,
    research,
)

# Load environment variables from .env file
load_dotenv()


def example_simple_research():
    """Run Deep Research without document context."""
    print("=== Simple Research Example ===\n")

    result = research(
        prompt="What are the latest trends in renewable energy investment for 2025?",
        output_format="pdf",
        output_path="renewable_energy_research.pdf",
        on_status=lambda s: print(f"  {s}")
    )

    print(f"\nResearch saved to: {result}")


def example_research_with_docs():
    """Run Deep Research with Google Docs as context."""
    print("=== Research with Google Docs Context ===\n")

    # Create a File Search Store
    store_name = create_store("market-research-context")
    print(f"Created store: {store_name}")

    try:
        # Upload Google Docs (replace with your actual doc URLs)
        doc_urls = [
            "https://docs.google.com/document/d/YOUR_DOC_ID_1/edit",
            "https://docs.google.com/document/d/YOUR_DOC_ID_2/edit",
        ]

        uploaded = upload_google_docs(store_name, doc_urls)
        print(f"Uploaded documents: {uploaded}")

        # Run research with the documents as context
        result = research(
            prompt="Based on the provided market analysis documents, what are the key opportunities?",
            file_store_names=[store_name],
            output_format="gdoc",
            on_status=lambda s: print(f"  {s}")
        )

        print(f"\nResearch saved to: {result}")

    finally:
        # Clean up the store
        delete_store(store_name)
        print(f"Deleted store: {store_name}")


def example_research_to_gdoc():
    """Run Deep Research and output to Google Docs."""
    print("=== Research to Google Doc Example ===\n")

    result = research(
        prompt="Provide a comprehensive analysis of AI adoption in healthcare",
        output_format="gdoc",
        on_status=lambda s: print(f"  {s}")
    )

    print(f"\nGoogle Doc created: {result}")


if __name__ == "__main__":
    # Uncomment the example you want to run:

    example_simple_research()
    # example_research_with_docs()
    # example_research_to_gdoc()
