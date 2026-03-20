import anthropic
import hashlib
import os
import pdfplumber
from dotenv import load_dotenv

from errors import (
    ConfigurationError,
    PDFNotFoundError,
    PDFReadError,
    EmptyPDFError,
    ClaudeAuthError,
    ClaudeRateLimitError,
    ClaudeTimeoutError,
    ClaudeAPIError,
    ClaudeEmptyResponseError,
)

load_dotenv(override=True)

_api_key = os.getenv("ANTHROPIC_API_KEY")
if not _api_key:
    raise ConfigurationError(
        "ANTHROPIC_API_KEY is not set. Add it to your .env file."
    )

client = anthropic.Anthropic(api_key=_api_key)

VALID_TYPES = {"billing", "medical", "case_file"}
MIN_TEXT_LENGTH = 50

tools = [
    {
        "name": "classify_document",
        "description": "Classifies a document as 'billing', 'medical', or 'case_file' based on its text content",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The extracted text of the document to classify"
                }
            },
            "required": ["document_text"]
        }
    }
]


def _page_fingerprint(text: str) -> str:
    """Return an MD5 hash of normalized page text for duplicate detection."""
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from a PDF, skipping duplicate pages.
    Raises PDFNotFoundError, PDFReadError, or EmptyPDFError on failure.
    """
    if not os.path.isfile(pdf_path):
        raise PDFNotFoundError(f"File not found: '{pdf_path}'")

    seen_fingerprints = set()
    pages = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                fingerprint = _page_fingerprint(text)
                if fingerprint in seen_fingerprints:
                    continue
                seen_fingerprints.add(fingerprint)
                pages.append(text)
    except Exception as e:
        raise PDFReadError(f"Could not parse PDF '{pdf_path}': {e}") from e

    document_text = "\n\n".join(pages)

    if len(document_text.strip()) < MIN_TEXT_LENGTH:
        raise EmptyPDFError(
            "No extractable text found — the PDF may be a scanned image or is empty."
        )

    return document_text


def classify_document(document_text: str) -> str:
    """
    Use Claude to classify the document as 'billing', 'medical', or 'case_file'.
    Raises ClaudeEmptyResponseError if the result is unrecognized.
    """
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Classify this document as exactly one of: 'billing', 'medical', or 'case_file'.\n"
                        "Reply with only the label, nothing else.\n\n"
                        f"Document:\n{document_text[:4000]}"
                    )
                }
            ]
        )
    except anthropic.AuthenticationError as e:
        raise ClaudeAuthError(f"Invalid Anthropic API key: {e}") from e
    except anthropic.RateLimitError as e:
        raise ClaudeRateLimitError("Anthropic rate limit exceeded. Try again later.") from e
    except anthropic.APITimeoutError as e:
        raise ClaudeTimeoutError("Request to Anthropic timed out.") from e
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Anthropic API error: {e}") from e

    if not response.content:
        raise ClaudeEmptyResponseError("Claude returned an empty response during classification.")

    label = response.content[0].text.strip().lower()

    if "billing" in label:
        return "billing"
    elif "medical" in label:
        return "medical"
    elif "case" in label:
        return "case_file"

    raise ClaudeEmptyResponseError(
        f"Claude returned an unrecognized document type: '{label}'. "
        f"Expected one of: {', '.join(sorted(VALID_TYPES))}."
    )


def run_pdf_agent(pdf_path: str) -> dict:
    """
    Full pipeline: extract text from PDF, classify document type.
    Returns {"document_type": str, "document_text": str}.
    Raises on file errors, parse errors, or API failures.
    """
    document_text = extract_pdf_text(pdf_path)

    messages = [
        {
            "role": "user",
            "content": f"Please classify this document:\n\n{document_text[:4000]}"
        }
    ]

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            tools=tools,
            messages=messages
        )
    except anthropic.AuthenticationError as e:
        raise ClaudeAuthError(f"Invalid Anthropic API key: {e}") from e
    except anthropic.RateLimitError as e:
        raise ClaudeRateLimitError("Anthropic rate limit exceeded. Try again later.") from e
    except anthropic.APITimeoutError as e:
        raise ClaudeTimeoutError("Request to Anthropic timed out.") from e
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Anthropic API error: {e}") from e

    document_type = None
    for block in response.content:
        if block.type == "tool_use":
            document_type = classify_document(block.input["document_text"])
            break

    # Fallback: Claude didn't invoke the tool — classify directly
    if document_type is None:
        document_type = classify_document(document_text)

    return {
        "document_type": document_type,
        "document_text": document_text,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_agent.py <path_to_pdf>")
        sys.exit(1)

    result = run_pdf_agent(sys.argv[1])
    print(f"\nDocument type  : {result['document_type']}")
    print(f"Text length    : {len(result['document_text'])} characters")
    print("\n--- EXTRACTED TEXT (first 500 chars) ---")
    print(result["document_text"][:500])
