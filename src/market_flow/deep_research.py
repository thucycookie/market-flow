"""
Deep Research Module

Executes Gemini Deep Research and outputs results as PDF or Google Doc.
"""

import asyncio
import os
import time
import tempfile
from pathlib import Path
from typing import Callable

from google import genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Deep Research agent identifier
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"

# Google Docs scopes for creating output documents
GOOGLE_DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file"
]


def _get_google_docs_credentials(credentials_path: str = "credentials.json") -> Credentials:
    """Get or refresh Google OAuth credentials for Docs API access."""
    creds = None
    token_path = Path(credentials_path).parent / "token_docs_write.json"

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


def _generate_pdf(content: str, output_path: str) -> str:
    """
    Generate a PDF from markdown/text content using fpdf2 (pure Python).

    Args:
        content: The text/markdown content.
        output_path: Path for the output PDF.

    Returns:
        The path to the generated PDF.
    """
    from fpdf import FPDF
    import re

    def sanitize_text(text):
        """Replace Unicode characters with ASCII equivalents."""
        replacements = {
            '\u2022': '-',   # bullet
            '\u2019': "'",   # right single quote
            '\u2018': "'",   # left single quote
            '\u201c': '"',   # left double quote
            '\u201d': '"',   # right double quote
            '\u2014': '--',  # em dash
            '\u2013': '-',   # en dash
            '\u2026': '...', # ellipsis
            '\u00a0': ' ',   # non-breaking space
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        # Remove any remaining non-latin1 characters
        return text.encode('latin-1', errors='replace').decode('latin-1')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)  # Set default font

    # Process content line by line
    lines = content.split('\n')

    for line in lines:
        line = line.rstrip()

        # Skip empty lines but add spacing
        if not line:
            pdf.ln(4)
            continue

        # Headers
        if line.startswith('### '):
            pdf.set_font('Helvetica', 'B', 12)
            pdf.ln(6)
            pdf.multi_cell(0, 6, sanitize_text(line[4:]), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)
        elif line.startswith('## '):
            pdf.set_font('Helvetica', 'B', 14)
            pdf.ln(8)
            pdf.multi_cell(0, 7, sanitize_text(line[3:]), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(3)
        elif line.startswith('# '):
            pdf.set_font('Helvetica', 'B', 18)
            pdf.ln(10)
            pdf.multi_cell(0, 9, sanitize_text(line[2:]), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(4)
        # Bullet points
        elif line.startswith('* ') or line.startswith('- '):
            pdf.set_font('Helvetica', '', 10)
            # Remove markdown formatting from text
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', line[2:])
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            pdf.multi_cell(0, 5, sanitize_text(f"  - {text}"), new_x='LMARGIN', new_y='NEXT')
        # Horizontal rule
        elif line.startswith('---'):
            pdf.ln(4)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
        # Table rows (basic support)
        elif line.startswith('|'):
            pdf.set_font('Courier', '', 8)
            # Clean up table formatting
            text = line.replace('|', ' | ').strip()
            pdf.multi_cell(0, 4, sanitize_text(text), new_x='LMARGIN', new_y='NEXT')
        # Regular text
        else:
            pdf.set_font('Helvetica', '', 10)
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 (\2)', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = re.sub(r'\[cite: [\d, ]+\]', '', text)  # Remove citations
            pdf.multi_cell(0, 5, sanitize_text(text), new_x='LMARGIN', new_y='NEXT')

    pdf.output(output_path)
    return output_path


def _create_google_doc(
    title: str,
    content: str,
    credentials_path: str = "credentials.json"
) -> str:
    """
    Create a Google Doc with the given content.

    Args:
        title: Document title.
        content: Text content to insert.
        credentials_path: Path to OAuth credentials.

    Returns:
        URL to the created Google Doc.
    """
    creds = _get_google_docs_credentials(credentials_path)

    # Create the document
    docs_service = build("docs", "v1", credentials=creds)
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc.get("documentId")

    # Insert content
    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": content
            }
        }
    ]

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"


def research(
    prompt: str,
    file_store_names: list[str] | None = None,
    output_format: str = "pdf",
    output_path: str | None = None,
    api_key: str | None = None,
    credentials_path: str = "credentials.json",
    poll_interval: int = 10,
    on_status: Callable[[str], None] | None = None
) -> str:
    """
    Execute Gemini Deep Research and generate output.

    Args:
        prompt: The research prompt/question.
        file_store_names: Optional list of File Search Store names for context.
        output_format: Output format - "pdf" or "gdoc".
        output_path: Path for PDF output (ignored for gdoc). Auto-generated if None.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.
        credentials_path: Path to Google OAuth credentials (for gdoc output).
        poll_interval: Seconds between status checks.
        on_status: Optional callback for status updates.

    Returns:
        Path to PDF file or URL to Google Doc.

    Raises:
        ValueError: If invalid output_format or missing API key.
        RuntimeError: If research fails or times out.
    """
    if output_format not in ("pdf", "gdoc"):
        raise ValueError(f"Invalid output_format: {output_format}. Use 'pdf' or 'gdoc'.")

    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)

    # Build tools configuration
    tools = None
    if file_store_names:
        tools = [
            {
                "type": "file_search",
                "file_search_store_names": file_store_names
            }
        ]

    # Start the research task
    if on_status:
        on_status("Starting Deep Research...")

    interaction = client.interactions.create(
        input=prompt,
        agent=DEEP_RESEARCH_AGENT,
        background=True,
        tools=tools
    )

    # Poll for completion
    while True:
        interaction = client.interactions.get(interaction.id)
        status = interaction.status

        if on_status:
            on_status(f"Status: {status}")

        if status == "completed":
            break
        elif status in ("failed", "cancelled"):
            error_msg = getattr(interaction, "error", "Unknown error")
            raise RuntimeError(f"Research {status}: {error_msg}")

        time.sleep(poll_interval)

    # Extract the research output
    if not interaction.outputs:
        raise RuntimeError("Research completed but no output was generated.")

    research_output = interaction.outputs[-1].text

    if on_status:
        on_status("Research complete. Generating output...")

    # Generate output in requested format
    if output_format == "pdf":
        if output_path is None:
            # Generate a filename from the prompt
            safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:50])
            output_path = f"{safe_name}_research.pdf"

        return _generate_pdf(research_output, output_path)

    else:  # gdoc
        # Create a title from the prompt
        title = f"Research: {prompt[:100]}"
        return _create_google_doc(title, research_output, credentials_path)


def research_stream(
    prompt: str,
    file_store_names: list[str] | None = None,
    api_key: str | None = None,
    on_chunk: Callable[[str], None] | None = None
) -> str:
    """
    Execute Gemini Deep Research with streaming output.

    Args:
        prompt: The research prompt/question.
        file_store_names: Optional list of File Search Store names for context.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.
        on_chunk: Optional callback for each text chunk.

    Returns:
        The complete research output as text.
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)

    # Build tools configuration
    tools = None
    if file_store_names:
        tools = [
            {
                "type": "file_search",
                "file_search_store_names": file_store_names
            }
        ]

    # Start streaming research
    stream = client.interactions.create(
        input=prompt,
        agent=DEEP_RESEARCH_AGENT,
        background=True,
        stream=True,
        tools=tools
    )

    full_output = []

    for chunk in stream:
        if hasattr(chunk, "event_type") and chunk.event_type == "content.delta":
            text = chunk.delta.text
            full_output.append(text)
            if on_chunk:
                on_chunk(text)

    return "".join(full_output)


async def research_async(
    prompt: str,
    file_store_names: list[str] | None = None,
    output_format: str = "pdf",
    output_path: str | None = None,
    api_key: str | None = None,
    credentials_path: str = "credentials.json",
    poll_interval: int = 10,
    on_status: Callable[[str], None] | None = None
) -> str:
    """
    Async version of research(). Execute Gemini Deep Research and generate output.

    This is useful when you want to run multiple research tasks concurrently
    or integrate with async web frameworks.

    Args:
        prompt: The research prompt/question.
        file_store_names: Optional list of File Search Store names for context.
        output_format: Output format - "pdf" or "gdoc".
        output_path: Path for PDF output (ignored for gdoc). Auto-generated if None.
        api_key: Google AI API key. If None, uses GOOGLE_API_KEY env var.
        credentials_path: Path to Google OAuth credentials (for gdoc output).
        poll_interval: Seconds between status checks.
        on_status: Optional callback for status updates.

    Returns:
        Path to PDF file or URL to Google Doc.

    Raises:
        ValueError: If invalid output_format or missing API key.
        RuntimeError: If research fails or times out.

    Example:
        ```python
        import asyncio
        from market_flow import research_async

        async def main():
            # Run multiple research tasks concurrently
            results = await asyncio.gather(
                research_async("Research topic A"),
                research_async("Research topic B"),
                research_async("Research topic C"),
            )
            for result in results:
                print(f"Output: {result}")

        asyncio.run(main())
        ```
    """
    if output_format not in ("pdf", "gdoc"):
        raise ValueError(f"Invalid output_format: {output_format}. Use 'pdf' or 'gdoc'.")

    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key required. Set GOOGLE_API_KEY or pass api_key parameter.")

    client = genai.Client(api_key=api_key)

    # Build tools configuration
    tools = None
    if file_store_names:
        tools = [
            {
                "type": "file_search",
                "file_search_store_names": file_store_names
            }
        ]

    # Start the research task
    if on_status:
        on_status("Starting Deep Research...")

    interaction = client.interactions.create(
        input=prompt,
        agent=DEEP_RESEARCH_AGENT,
        background=True,
        tools=tools
    )

    # Poll for completion asynchronously
    while True:
        interaction = client.interactions.get(interaction.id)
        status = interaction.status

        if on_status:
            on_status(f"Status: {status}")

        if status == "completed":
            break
        elif status in ("failed", "cancelled"):
            error_msg = getattr(interaction, "error", "Unknown error")
            raise RuntimeError(f"Research {status}: {error_msg}")

        await asyncio.sleep(poll_interval)

    # Extract the research output
    if not interaction.outputs:
        raise RuntimeError("Research completed but no output was generated.")

    research_output = interaction.outputs[-1].text

    if on_status:
        on_status("Research complete. Generating output...")

    # Generate output in requested format
    if output_format == "pdf":
        if output_path is None:
            safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:50])
            output_path = f"{safe_name}_research.pdf"

        return _generate_pdf(research_output, output_path)

    else:  # gdoc
        title = f"Research: {prompt[:100]}"
        return _create_google_doc(title, research_output, credentials_path)
