import os
import tempfile
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(override=True)

from agent import run_agent
from pdf_agent import run_pdf_agent, extract_pdf_text
from errors import RecordSummarizerError

# Maps pdf_agent labels → agent labels
_TYPE_MAP = {
    "billing": "billing_record",
    "medical": "medical_record",
    "case_file": "case_file",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(RecordSummarizerError)
def handle_app_error(exc):
    return jsonify({"error": str(exc)}), exc.status_code


@app.errorhandler(413)
def handle_too_large(exc):
    return jsonify({"error": "File too large — maximum upload size is 20 MB."}), 413


@app.errorhandler(Exception)
def handle_unexpected(exc):
    return jsonify({"error": "An unexpected error occurred."}), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    """GET /health — Liveness check. Returns 200 when the server is running."""
    return jsonify({"status": "ok"})


@app.route("/summarize", methods=["POST"])
def summarize():
    """POST /summarize — Accepts JSON {document_text, document_type} and returns a structured summary.
    document_type must be one of: medical_record, billing_record, case_file."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON."}), 400

    document_text = body.get("document_text", "").strip()
    document_type = body.get("document_type", "").strip()

    if not document_text:
        return jsonify({"error": "'document_text' is required."}), 400
    if not document_type:
        return jsonify({"error": "'document_type' is required."}), 400

    summary = run_agent(document_text, document_type)
    return jsonify({"summary": summary})


@app.route("/pdf/extract", methods=["POST"])
def pdf_extract():
    """POST /pdf/extract — Accepts a PDF upload (multipart, max 20 MB) and returns the extracted text.
    Deduplicates repeated pages. Does not classify or summarize."""
    if "file" not in request.files:
        return jsonify({"error": "Multipart field 'file' is required."}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Uploaded file must have a .pdf extension."}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            f.save(tmp)

        document_text = extract_pdf_text(tmp_path)
        return jsonify({"document_text": document_text})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/pdf/process", methods=["POST"])
def pdf_process():
    """POST /pdf/process — Full pipeline: accepts a PDF upload, classifies the document type, and returns a summary.
    Combines /pdf/extract + classification + /summarize in one call."""
    if "file" not in request.files:
        return jsonify({"error": "Multipart field 'file' is required."}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Uploaded file must have a .pdf extension."}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            f.save(tmp)

        result = run_pdf_agent(tmp_path)
        agent_type = _TYPE_MAP.get(result["document_type"], result["document_type"])
        summary = run_agent(result["document_text"], agent_type)

        return jsonify({
            "document_type": result["document_type"],
            "summary": summary,
        })
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
