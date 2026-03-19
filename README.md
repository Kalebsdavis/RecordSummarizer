# RecordSummarizer

An AI-powered agent that summarizes medical records and case files using the Anthropic Claude API. It uses Claude's tool-use feature to intelligently extract structured information from documents.

## What It Does

The agent accepts a document and its type, then uses Claude to call a `summarize_document` tool that extracts relevant fields:

- **Medical records** — patient name, date of visit, diagnosis, recommended treatment, and important notes
- **Case files** — case number, parties involved, key dates, and a summary of facts

The flow is:
1. `run_agent()` sends the document to Claude along with the tool definition
2. Claude decides to invoke the `summarize_document` tool
3. The tool calls Claude again with a targeted extraction prompt
4. The structured summary is printed to the console

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python 3.13+ | Runtime |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (`anthropic`) | Claude API client |
| `python-dotenv` | Load API key from `.env` file |
| Claude `claude-opus-4-6` | AI model for summarization and tool orchestration |

## Project Structure

```
RecordSummarizer/
├── agent.py       # Main script — tool definition, agent logic, sample run
├── .env           # API key (not committed to git)
├── .gitignore     # Excludes .env
└── .venv/         # Python virtual environment
```

## Running Locally

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

1. **Clone the repo and navigate into it:**
   ```bash
   git clone <repo-url>
   cd RecordSummarizer
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install anthropic python-dotenv
   ```

4. **Create a `.env` file with your API key:**
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

### Run

```bash
python agent.py
```

This runs a built-in sample medical record through the agent and prints the extracted summary to the console.

## Extending

To process your own documents, call `run_agent()` directly:

```python
run_agent(document_text="...", document_type="medical_record")
# or
run_agent(document_text="...", document_type="case_file")
```
