import anthropic
import json
import os
from dotenv import load_dotenv

from errors import (
    ConfigurationError,
    UnsupportedDocumentTypeError,
    DocumentTooShortError,
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

SUPPORTED_TYPES = {"medical_record", "billing_record", "case_file"}
MIN_TEXT_LENGTH = 50

tools = [
    {
        "name": "summarize_document",
        "description": "Summarizes a medical record, billing record, or case file and extracts key information",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The full text of the document to summarize"
                },
                "document_type": {
                    "type": "string",
                    "description": "The type of document: 'medical_record', 'billing_record', or 'case_file'"
                }
            },
            "required": ["document_text", "document_type"]
        }
    }
]


def summarize_document(document_text: str, document_type: str) -> str:
    """Extract structured fields from document_text. Raises on bad input or API failure."""
    if document_type not in SUPPORTED_TYPES:
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type: '{document_type}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_TYPES))}."
        )
    if len(document_text.strip()) < MIN_TEXT_LENGTH:
        raise DocumentTooShortError(
            f"Document text is too short to summarize (minimum {MIN_TEXT_LENGTH} characters)."
        )

    if document_type == "medical_record":
        prompt = f"""Extract the following from this medical record:
        - Patient name
        - Date of visit
        - Diagnosis
        - Recommended treatment
        - Any important notes

        Medical Record:
        {document_text}"""
    elif document_type == "billing_record":
        prompt = f"""Extract all billing line items from this billing record. For each line item, extract the following fields if present:
        - Date of service
        - CPT code
        - CPT description
        - Plaintiff charge

        Return the results as a list of line items. If a field is not present for a given line item, omit it.

        Billing Record:
        {document_text}"""
    else:
        prompt = f"""Extract the following from this case file:
        - Case number
        - Parties involved
        - Key dates
        - Summary of facts

        Case File:
        {document_text}"""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.AuthenticationError as e:
        raise ClaudeAuthError(f"Invalid Anthropic API key: {e}") from e
    except anthropic.RateLimitError as e:
        raise ClaudeRateLimitError(f"Anthropic rate limit exceeded. Try again later.") from e
    except anthropic.APITimeoutError as e:
        raise ClaudeTimeoutError(f"Request to Anthropic timed out.") from e
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Anthropic API error: {e}") from e

    if not response.content:
        raise ClaudeEmptyResponseError("Claude returned an empty response.")

    return response.content[0].text


def run_agent(document_text: str, document_type: str) -> str:
    """Orchestrate tool-use flow. Returns the summary string. Raises on failure."""
    messages = [
        {
            "role": "user",
            "content": f"Please summarize this {document_type}: {document_text}"
        }
    ]

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
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

    for block in response.content:
        if block.type == "tool_use":
            return summarize_document(
                block.input["document_text"],
                block.input["document_type"]
            )

    # Fallback: Claude didn't invoke the tool — summarize directly
    return summarize_document(document_text, document_type)


if __name__ == "__main__":
    sample_record = """
Patient: Jane Doe
Date: March 15 2026
Doctor: Dr. Robert Smith
Diagnosis: The patient presents with chronic lower back pain
stemming from a workplace injury sustained in January 2026.
MRI results show a herniated disc at L4-L5.
Treatment: Physical therapy recommended twice weekly for 8 weeks.
Follow up in 6 weeks. Patient cleared for sedentary work only.
Notes: Patient reports pain level of 7 out of 10.
Prescribed ibuprofen 600mg as needed.
"""
    print(f"\nProcessing medical_record...")
    result = run_agent(sample_record, "medical_record")
    print("\n--- SUMMARY ---")
    print(result)
