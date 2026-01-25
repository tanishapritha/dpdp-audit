import os
import json
import pdfplumber
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PDF_PATH = "dpdp-act.pdf"

CLAUSES_OUT = "compliance/dpdp/dpdp_2023_clauses.json"
REQUIREMENTS_OUT = "compliance/dpdp/dpdp_2023_requirements.json"

MODEL = "openai/gpt-4o-mini"  # Cost-effective model for large legal text


# -------------------------
# STEP 1: Extract PDF Text
# -------------------------
def extract_pdf_text(pdf_path: str) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append(f"\n--- PAGE {i+1} ---\n{text}")
    return "\n".join(pages)


# -------------------------
# STEP 2: Call OpenRouter
# -------------------------
def call_llm(prompt: str) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a legal text structuring engine. "
                    "You must strictly follow instructions and output valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "response_format": {"type": "json_object"},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=300)
    if response.status_code != 200:
        print(f"Error Details: {response.text}")
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    # Strip markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


# -------------------------
# STEP 3: Build Prompt
# -------------------------
def build_prompt(dpdp_text: str) -> str:
    return f"""
You are an expert legal engineer.

Convert the Digital Personal Data Protection Act, 2023 text below into TWO JSON outputs.

RULES (MANDATORY):
- Use ONLY the provided text.
- Do NOT invent obligations.
- Do NOT summarize law.
- Clauses must be verbatim.
- Requirements must be obligations only.
- Output VALID JSON ONLY.

OUTPUT FORMAT (single JSON object):

{{
  "clauses": [
    {{
      "clause_id": "DPDP_S6_1",
      "section_ref": "Section 6",
      "subsection_ref": "1",
      "title": "Consent Requirement",
      "text": "Exact text from the Act",
      "page_hint": "PAGE 7"
    }}
  ],
  "requirements": {{
    "framework": {{
      "name": "DPDP",
      "version": "2023",
      "effective_date": "2023-08-11"
    }},
    "requirements": [
      {{
        "requirement_id": "DPDP_6_1",
        "section_ref": "Section 6(1)",
        "title": "Valid Consent Before Processing",
        "requirement_text": "The Data Fiduciary must obtain free, specific, informed, unconditional and unambiguous consent before processing personal data.",
        "risk_level": "HIGH"
      }}
    ]
  }}
}}

IMPORTANT:
- Include ALL sections and subsections as clauses.
- Include ONLY legal obligations as requirements.
- If unsure, omit.

DPDP ACT TEXT:
{dpdp_text}
"""


# -------------------------
# STEP 4: Run Pipeline
# -------------------------
def main():
    print("Extracting DPDP Act text...")
    dpdp_text = extract_pdf_text(PDF_PATH)

    print("Calling LLM to structure law...")
    prompt = build_prompt(dpdp_text)
    raw_output = call_llm(prompt)

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"Raw Output: {raw_output}")
        raise RuntimeError("LLM did not return valid JSON. Review output manually.")

    os.makedirs("compliance/dpdp", exist_ok=True)

    with open(CLAUSES_OUT, "w", encoding="utf-8") as f:
        json.dump(data["clauses"], f, indent=2, ensure_ascii=False)

    with open(REQUIREMENTS_OUT, "w", encoding="utf-8") as f:
        json.dump(data["requirements"], f, indent=2, ensure_ascii=False)

    print("Done.")
    print(f"Clauses written to {CLAUSES_OUT}")
    print(f"Requirements written to {REQUIREMENTS_OUT}")
    print("REVIEW BOTH FILES MANUALLY BEFORE DB SEEDING")


if __name__ == "__main__":
    main()
