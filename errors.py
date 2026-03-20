class RecordSummarizerError(Exception):
    """Base class for all application errors."""
    status_code = 500


class ConfigurationError(RecordSummarizerError):
    """ANTHROPIC_API_KEY is missing or empty."""
    status_code = 500


class UnsupportedDocumentTypeError(RecordSummarizerError):
    """document_type is not one of the known supported types."""
    status_code = 400


class DocumentTooShortError(RecordSummarizerError):
    """document_text is present but too short to summarize meaningfully."""
    status_code = 422


class PDFNotFoundError(RecordSummarizerError):
    """The given file path does not exist."""
    status_code = 404


class PDFReadError(RecordSummarizerError):
    """pdfplumber could not open or parse the file."""
    status_code = 422


class EmptyPDFError(RecordSummarizerError):
    """PDF opened successfully but yielded no extractable text."""
    status_code = 422


class ClaudeAuthError(RecordSummarizerError):
    """Anthropic returned a 401 authentication error."""
    status_code = 500


class ClaudeRateLimitError(RecordSummarizerError):
    """Anthropic returned a 429 rate limit error."""
    status_code = 429


class ClaudeTimeoutError(RecordSummarizerError):
    """Request to Anthropic timed out."""
    status_code = 504


class ClaudeEmptyResponseError(RecordSummarizerError):
    """Claude returned a response with no usable content."""
    status_code = 502


class ClaudeAPIError(RecordSummarizerError):
    """Catch-all for unexpected Anthropic API errors."""
    status_code = 502


def error_response(exc: RecordSummarizerError):
    """Return a Flask-compatible (dict, int) tuple for any RecordSummarizerError."""
    return {"error": str(exc)}, exc.status_code
