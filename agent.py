import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

tools = [
    {
        "name": "summarize_document",
        "description": "Summarizes a medical record or case file and extracts key information",
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

def summarize_document(document_text, document_type):
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
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

def run_agent(document_text, document_type):
    print(f"\nProcessing {document_type}...")
    
    messages = [
        {
            "role": "user", 
            "content": f"Please summarize this {document_type}: {document_text}"
        }
    ]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    for block in response.content:
        if block.type == "tool_use":
            result = summarize_document(
                block.input["document_text"],
                block.input["document_type"]
            )
            print("\n--- SUMMARY ---")
            print(result)

# Test it with a fake medical record
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

run_agent(sample_record, "medical_record")