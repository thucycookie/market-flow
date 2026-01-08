# Market Flow

Execute Gemini Deep Research with Google Docs context and output results as PDF or Google Doc.

## Quick Start

```bash
cd market-flow
source venv/bin/activate

# Set your API key
export GOOGLE_API_KEY="your-key-here"

# Run a simple research query
python -c "
from market_flow import research

result = research(
    prompt='What are the latest trends in renewable energy?',
    output_format='pdf'
)
print(f'Research saved to: {result}')
"
```

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/market-flow.git
cd market-flow

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

## API Summary

### Module 1: `document_store`

Handles fetching Google Docs and uploading them to Gemini File Search Stores.

```python
from market_flow import create_store, upload_google_docs, delete_store

# Create a File Search Store
store_name = create_store("my-research-context")

# Upload Google Docs as context
upload_google_docs(store_name, [
    "https://docs.google.com/document/d/abc123/edit",
    "https://docs.google.com/document/d/def456/edit"
])

# Clean up when done
delete_store(store_name)
```

**Functions:**
- `create_store(name)` - Create a new File Search Store
- `upload_google_docs(store_name, doc_urls)` - Fetch Google Docs and upload to store
- `upload_files(store_name, file_paths)` - Upload local files to store
- `delete_store(store_name)` - Delete a File Search Store
- `list_stores()` - List all File Search Stores

### Module 2: `deep_research`

Executes Gemini Deep Research and generates output as PDF or Google Doc.

```python
from market_flow import research

# Simple research (no document context)
result = research(
    prompt="Analyze the impact of AI on healthcare",
    output_format="pdf",  # or "gdoc"
    output_path="healthcare_ai_research.pdf"
)

# Research with document context
result = research(
    prompt="Based on the provided documents, summarize key findings",
    file_store_names=[store_name],
    output_format="gdoc"
)
```

**Functions:**
- `research(prompt, file_store_names=None, output_format="pdf", ...)` - Run Deep Research
- `research_stream(prompt, file_store_names=None, on_chunk=None)` - Run with streaming output

## Configuration

### Required: Google AI API Key

Get an API key from [Google AI Studio](https://aistudio.google.com/):

```bash
export GOOGLE_API_KEY="your-api-key"
```

### Optional: Google Docs Access

To use Google Docs as context, you need OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the Google Docs API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` to the project directory

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────┐                ┌─────────────────────┐
│   document_store    │                │   deep_research     │
│                     │                │                     │
│ • Fetch Google Docs │───────────────▶│ • Execute research  │
│ • Upload to Store   │  store_name    │ • Generate PDF      │
│ • Manage stores     │                │ • Create Google Doc │
└─────────────────────┘                └─────────────────────┘
          │                                       │
          ▼                                       ▼
   Google Docs API                    Gemini Interactions API
   File Search API                         WeasyPrint
```

## License

MIT
