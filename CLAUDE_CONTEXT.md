# Claude Context - Market Flow

This file provides context for Claude Code sessions working on this project.

## Project Overview

**Market Flow** is a Python module that executes Gemini Deep Research with Google Docs context and outputs results as PDF or Google Doc.

## Architecture

```
market-flow/
├── src/market_flow/
│   ├── __init__.py           # Package exports
│   ├── document_store.py     # Module 1: Google Docs → File Search Store
│   ├── deep_research.py      # Module 2: Gemini Deep Research + PDF output
│   └── drive_uploader.py     # Module 3: Upload files to Google Drive
├── examples/
│   └── basic_usage.py
├── venv/                     # Virtual environment (Python 3.13)
├── .env                      # Contains GOOGLE_API_KEY (not committed)
└── .env.example
```

## Modules

### 1. `document_store.py`
Fetches Google Docs and uploads to Gemini File Search Stores for RAG context.

**Key functions:**
- `create_store(name)` - Create a File Search Store
- `upload_google_docs(store_name, doc_urls)` - Fetch & upload Google Docs
- `delete_store(store_name)` - Clean up store

### 2. `deep_research.py`
Executes Gemini Deep Research via the Interactions API.

**Key functions:**
- `research(prompt, file_store_names=None, output_format="pdf")` - Sync research
- `research_async(...)` - Async version for concurrent research
- `research_stream(...)` - Streaming output

**Technical notes:**
- Uses `google-genai` SDK (not deprecated `google-generativeai`)
- Agent: `deep-research-pro-preview-12-2025`
- Requires `background=True` for async execution
- PDF generation uses `fpdf2` (pure Python, no system dependencies)

### 3. `drive_uploader.py`
Uploads files to Google Drive with optional conversion to Google Docs.

**Key functions:**
- `upload_to_drive(file_path, folder_id, convert_to_doc=True, delete_local=False)`
- `list_files_in_folder(folder_id)`
- `delete_from_drive(file_id)`

**Authentication:**
- Uses Application Default Credentials (ADC)
- Local: `gcloud auth application-default login`
- Google Cloud: Automatic via attached service account

## Dependencies

Key packages (see `requirements.txt`):
- `google-genai` - Gemini API (Interactions API for Deep Research)
- `google-api-python-client` - Google Docs/Drive APIs
- `fpdf2` - PDF generation (pure Python)
- `python-dotenv` - Environment variable management

## Environment Setup

```bash
cd market-flow
source venv/bin/activate
export GOOGLE_API_KEY="your-key"  # Or use .env file
```

For Drive uploads:
```bash
gcloud auth application-default login
```

## API Keys & Auth

| Service | Auth Method |
|---------|-------------|
| Gemini API | `GOOGLE_API_KEY` env var |
| Google Drive | Application Default Credentials |
| Google Docs (read) | OAuth (credentials.json) |

## Design Decisions

1. **Separated modules** - document_store, deep_research, and drive_uploader are independent for reusability

2. **fpdf2 over weasyprint** - Pure Python, no system dependencies (pango, cairo)

3. **ADC for Drive** - Works locally and on Google Cloud without code changes

4. **Async support** - `research_async()` enables concurrent research tasks

## Next Steps / TODOs

- [ ] Test `upload_to_drive()` with actual Google Drive folder
- [ ] Add integration tests
- [ ] Consider adding progress callbacks for long uploads
- [ ] Document Google Cloud deployment setup

## Common Commands

```bash
# Activate environment
source venv/bin/activate

# Run research
python -c "from market_flow import research; result = research('your prompt', output_format='pdf')"

# Upload to Drive
python -c "from market_flow import upload_to_drive; upload_to_drive('file.pdf', 'FOLDER_ID')"
```

## Git Workflow

- `main` - Stable branch
- `feature/*` - Feature branches, PR to main
- Commits include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>`
