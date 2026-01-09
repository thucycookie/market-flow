"""
Market Flow - Gemini Deep Research with Google Docs Integration

A Python module for executing Gemini Deep Research with Google Docs context
and outputting results as PDF or Google Doc.
"""

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
]
