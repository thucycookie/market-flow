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

from market_flow.drive_uploader import (
    upload_to_drive,
    list_files_in_folder,
    delete_from_drive,
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
]
