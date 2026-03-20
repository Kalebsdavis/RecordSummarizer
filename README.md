# RecordSummarizer

An AI-powered REST API that extracts structured information from medical records, billing records, and case files. Built on the Anthropic Claude API with tool-use, exposed via Flask.

## What It Does

- Accepts plain text or a PDF upload
- Automatically classifies the document as `medical`, `billing`, or `case_file`
- Extracts structured fields relevant to that document type:
  - **Medical records** — patient name, date of visit, diagnosis, recommended treatment, notes
  - **Billing records** — all line items with date of service, CPT code, CPT description, plaintiff charge
  - **Case files** — case number, parties involved, key dates, summary of facts
- Skips duplicate pages when processing PDFs

## Technologies

| Technology | Purpose |
|---|---|
| Python 3.10+ | Runtime |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) | Claude API client |
| Claude `claude-opus-4-6` | AI model for classification and extraction |
| Flask | REST API framework |
| pdfplumber | PDF text extraction |
| waitress | Production WSGI server (Windows-compatible) |
| python-dotenv | Environment variable loading |

## Project Structure

```
RecordSummarizer/
├── errors.py         # Shared exception hierarchy (11 typed errors with HTTP status codes)
├── agent.py          # Document summarization agent (text in → summary out)
├── pdf_agent.py      # PDF extraction and classification agent
├── api.py            # Flask app — 4 REST endpoints
├── requirements.txt  # Pinned dependencies
├── .env              # API key (not committed to git)
└── .gitignore
```

## Setup

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
git clone <repo-url>
cd RecordSummarizer

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
```

## Running

**Development:**
```bash
python api.py
# Server starts at http://localhost:5000
```

**Production:**
```bash
waitress-serve --port=5000 api:app
```

## API Endpoints

### `GET /health`

Liveness check.

```bash
curl http://localhost:5000/health
```
```json
{"status": "ok"}
```

---

### `POST /summarize`

Summarize a text document.

**Request:** JSON body

| Field | Type | Required | Description |
|---|---|---|---|
| `document_text` | string | yes | Full text of the document |
| `document_type` | string | yes | `medical_record`, `billing_record`, or `case_file` |

```bash
curl -X POST http://localhost:5000/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "Patient: Jane Doe\nDate: March 15 2026\nDiagnosis: Herniated disc at L4-L5.\nTreatment: Physical therapy twice weekly for 8 weeks.",
    "document_type": "medical_record"
  }'
```
```json
{"summary": "- Patient name: Jane Doe\n- Date of visit: March 15, 2026\n..."}
```

---

### `POST /pdf/extract`

Extract text from a PDF, deduplicating repeated pages.

**Request:** `multipart/form-data` with a `file` field (`.pdf` only, max 20 MB)

```bash
curl -X POST http://localhost:5000/pdf/extract \
  -F "file=@/path/to/record.pdf"
```
```json
{"document_text": "Patient: Jane Doe\n..."}
```

---

### `POST /pdf/process`

Full pipeline: upload a PDF, classify it, and return a structured summary.

**Request:** `multipart/form-data` with a `file` field (`.pdf` only, max 20 MB)

```bash
curl -X POST http://localhost:5000/pdf/process \
  -F "file=@/path/to/record.pdf"
```
```json
{
  "document_type": "medical",
  "summary": "- Patient name: Jane Doe\n- Date of visit: March 15, 2026\n..."
}
```

---

## Error Responses

All errors return JSON with an `error` field and a standard HTTP status code:

```json
{"error": "Human-readable description of what went wrong."}
```

| Status | Meaning |
|---|---|
| `400` | Bad request — missing field, wrong content type, unsupported document type |
| `404` | File not found |
| `413` | Upload exceeds 20 MB limit |
| `422` | Unprocessable — document too short, PDF is scanned/empty, corrupted file |
| `429` | Anthropic rate limit exceeded |
| `500` | Configuration error (missing API key) or unexpected server error |
| `502` | Claude returned an unusable response |
| `504` | Request to Anthropic timed out |

## CLI Usage

Both agents can still be run directly from the command line without starting the server.

**Summarize a text document:**
```bash
python agent.py
# Runs the built-in sample medical record and prints the summary
```

**Process a PDF:**
```bash
python pdf_agent.py path/to/record.pdf
# Prints document type and first 500 characters of extracted text
```

**Use programmatically:**
```python
from agent import run_agent
from pdf_agent import run_pdf_agent

# Summarize text directly
summary = run_agent(document_text="...", document_type="billing_record")

# Process a PDF
result = run_pdf_agent("record.pdf")
# result = {"document_type": "billing", "document_text": "..."}
```
