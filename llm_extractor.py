
import json
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)
MODEL = "gemini-3.8-flash"


def extract_clause(clause_text, clause_type):
    """Extract one requested answer from a contract clause."""

    prompt = f"""
You are a contract information extraction assistant.

Task:
Extract the answer for the requested clause category from the
provided contract text.

Clause category: {clause_type}

Contract text:
{clause_text}

Rules:
- Use only information supported by the supplied text.
- If the answer is not present, use an empty string for answer
  and status "not_found".
- Copy evidence exactly from the supplied text.
- Do not provide legal advice.
- Return JSON only, with these keys:
  clause_type, answer, evidence, status.
"""

    start = time.perf_counter()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "clause_type": {"type": "STRING"},
                    "answer": {"type": "STRING"},
                    "evidence": {"type": "STRING"},
                    "status": {
                        "type": "STRING",
                        "enum": ["found", "not_found"],
                    },
                },
                "required": [
                    "clause_type",
                    "answer",
                    "evidence",
                    "status",
                ],
            },
        },
    )

    latency_seconds = time.perf_counter() - start
    result = json.loads(response.text)

    # Basic evidence validation: the quoted evidence must occur
    # verbatim in the input text.
    evidence = result.get("evidence", "")
    result["evidence_valid"] = (
        bool(evidence) and evidence in clause_text
    )

    result["latency_seconds"] = round(latency_seconds, 3)
    return result


if __name__ == "__main__":
    sample_clause = (
        "This Agreement is accepted by Company in the State of Nevada "
        "and shall be governed by and construed in accordance with "
        "the laws thereof, which laws shall prevail in the event of "
        "any conflict."
    )

    output = extract_clause(sample_clause, "Governing Law")
    print(json.dumps(output, indent=2))
