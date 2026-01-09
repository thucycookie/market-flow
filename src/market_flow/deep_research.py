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
    Generate a PDF from markdown/text content.

    Args:
        content: The text/markdown content.
        output_path: Path for the output PDF.

    Returns:
        The path to the generated PDF.
    """
    from weasyprint import HTML, CSS

    # Convert markdown-style content to basic HTML
    html_content = _markdown_to_html(content)

    # Basic styling
    css = CSS(string="""
        @page {
            margin: 1in;
            size: letter;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        h1 { font-size: 24pt; margin-top: 0; color: #1a1a1a; }
        h2 { font-size: 18pt; margin-top: 24pt; color: #2a2a2a; }
        h3 { font-size: 14pt; margin-top: 18pt; color: #3a3a3a; }
        p { margin: 12pt 0; }
        ul, ol { margin: 12pt 0; padding-left: 24pt; }
        li { margin: 6pt 0; }
        blockquote {
            border-left: 3px solid #ccc;
            margin: 12pt 0;
            padding-left: 12pt;
            color: #666;
        }
        code {
            background: #f4f4f4;
            padding: 2pt 4pt;
            border-radius: 3pt;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 10pt;
        }
        pre {
            background: #f4f4f4;
            padding: 12pt;
            border-radius: 4pt;
            overflow-x: auto;
        }
        a { color: #0066cc; }
        hr { border: none; border-top: 1px solid #ddd; margin: 24pt 0; }
    """)

    HTML(string=html_content).write_pdf(output_path, stylesheets=[css])
    return output_path


def _markdown_to_html(content: str) -> str:
    """Convert basic markdown to HTML."""
    import re

    html = content

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Code blocks
    html = re.sub(r'```[\w]*\n(.*?)\n```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)

    # Unordered lists (basic)
    lines = html.split('\n')
    in_list = False
    result = []
    for line in lines:
        if re.match(r'^[-*] ', line):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{line[2:]}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    html = '\n'.join(result)

    # Paragraphs (wrap remaining text blocks)
    paragraphs = html.split('\n\n')
    processed = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            p = f'<p>{p}</p>'
        processed.append(p)
    html = '\n'.join(processed)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>{html}</body>
</html>"""


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
