"""
Document Store Module

Handles fetching Google Docs and uploading them to Gemini File Search Stores.
"""

import os
import re
import tempfile
from pathlib import Path

from google import genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes required for Google Docs API
GOOGLE_DOCS_SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


def _get_google_docs_credentials(credentials_path: str = "credentials.json") -> Credentials:
    """
    Get or refresh Google OAuth credentials for Docs API access.

    Args:
        credentials_path: Path to the OAuth client credentials JSON file.

    Returns:
        Valid Google OAuth credentials.
    """
    creds = None
    token_path = Path(credentials_path).parent / "token.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_DOCS_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_path}. "
                    "Download OAuth client credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, GOOGLE_DOCS_SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def extract_doc_id(url: str) -> str:
    """
    Extract the document ID from a Google Docs URL.

    Args:
        url: Google Docs URL (e.g., https://docs.google.com/document/d/ABC123/edit)

    Returns:
        The document ID.

    Raises:
        ValueError: If the URL format is not recognized.
    """
    patterns = [
        r"/document/d/([a-zA-Z0-9_-]+)",  # Standard Docs URL
        r"/open\?id=([a-zA-Z0-9_-]+)",     # Open URL format
        r"^([a-zA-Z0-9_-]+)$",              # Just the ID itself
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract document ID from URL: {url}")


def fetch_google_doc_content(
    doc_url: str,
    credentials_path: str = "credentials.json"
) -> tuple[str, str]:
    """
    Fetch the content of a Google Doc as plain text.

    Args:
        doc_url: Google Docs URL or document ID.
        credentials_path: Path to OAuth credentials file.

    Returns:
        Tuple of (document_title, document_content).
    """
    doc_id = extract_doc_id(doc_url)
    creds = _get_google_docs_credentials(credentials_path)

    service = build("docs", "v1", credentials=creds)
    document = service.documents().get(documentId=doc_id).execute()

    title = document.get("title", "Untitled")
    content_parts = []

    for element in document.get("body", {}).get("content", []):
        if "paragraph" in element:
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    content_parts.append(para_element["textRun"].get("content", ""))

    return title, "".join(content_parts)


def create_store(
    name: str,
    api_key: str | None = None
) -> str:
    """
    Create a new File Search Store.

    Args:
        name: Name for the store.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.

    Returns:
        The full store name (e.g., 'fileSearchStores/store-id').
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)

    store = client.file_search_stores.create(
        display_name=name
    )

    return store.name


def upload_google_docs(
    store_name: str,
    doc_urls: list[str],
    api_key: str | None = None,
    credentials_path: str = "credentials.json"
) -> list[str]:
    """
    Fetch Google Docs and upload them to a File Search Store.

    Args:
        store_name: The File Search Store name.
        doc_urls: List of Google Docs URLs.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.
        credentials_path: Path to Google OAuth credentials.

    Returns:
        List of uploaded document names.
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)
    uploaded_docs = []

    for url in doc_urls:
        title, content = fetch_google_doc_content(url, credentials_path)

        # Write content to a temporary file for upload
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            prefix=f"{title[:20]}_"
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Upload file to Gemini Files API
            uploaded_file = client.files.upload(file=tmp_path)

            # Import the file into the File Search Store
            client.file_search_stores.documents.create(
                parent=store_name,
                file=uploaded_file.name,
                display_name=title
            )

            uploaded_docs.append(title)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    return uploaded_docs


def upload_files(
    store_name: str,
    file_paths: list[str],
    api_key: str | None = None
) -> list[str]:
    """
    Upload local files to a File Search Store.

    Args:
        store_name: The File Search Store name.
        file_paths: List of local file paths.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.

    Returns:
        List of uploaded document names.
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)
    uploaded_docs = []

    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Upload file to Gemini Files API
        uploaded_file = client.files.upload(file=str(path))

        # Import the file into the File Search Store
        client.file_search_stores.documents.create(
            parent=store_name,
            file=uploaded_file.name,
            display_name=path.stem
        )

        uploaded_docs.append(path.stem)

    return uploaded_docs


def delete_store(
    store_name: str,
    api_key: str | None = None
) -> None:
    """
    Delete a File Search Store.

    Args:
        store_name: The File Search Store name to delete.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)
    client.file_search_stores.delete(name=store_name)


def list_stores(api_key: str | None = None) -> list[dict]:
    """
    List all File Search Stores.

    Args:
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.

    Returns:
        List of store information dictionaries.
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)
    stores = client.file_search_stores.list()

    return [
        {"name": store.name, "display_name": store.display_name}
        for store in stores
    ]
