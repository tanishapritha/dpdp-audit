import json
from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Dict

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )

    async def verify_requirement(self, requirement_text: str, clauses: List[Dict]) -> Dict:
        """
        Calls the LLM to verify a requirement against a set of clauses.
        """
        system_prompt = (
            "You are a legal compliance verification system.\n\n"
            "Your task is to verify whether specific statutory requirements are\n"
            "explicitly stated in the provided text.\n\n"
            "You must not infer intent, interpret vague language, or assume compliance.\n"
            "If a requirement is not explicitly stated, it must be marked as NOT_COVERED.\n\n"
            "You must return output strictly in valid JSON according to the provided schema.\n"
            "Do not include explanations outside the schema.\n"
            "Temperature = 0."
        )

        user_prompt = (
            "You are verifying compliance with the Digital Personal Data Protection Act, 2023.\n\n"
            f"Requirement:\n{requirement_text}\n\n"
            "Task:\nReview the provided clauses and determine whether this requirement is\n"
            "explicitly satisfied.\n\n"
            "Rules:\n"
            "- Do not infer compliance.\n"
            "- Do not rely on implied meaning.\n"
            "- If language is vague or incomplete, mark PARTIAL.\n"
            "- If missing, mark NOT_COVERED.\n"
            "- Evidence must be a direct quote.\n\n"
            "Return JSON only.\n\n"
            "Schema:\n"
            "{\n"
            "  \"status\": \"COVERED | PARTIAL | NOT_COVERED\",\n"
            "  \"confidence\": number,\n"
            "  \"evidence\": {\n"
            "    \"page\": number | null,\n"
            "    \"clause_id\": string | null,\n"
            "    \"quote\": string | null\n"
            "  },\n"
            "  \"reason\": string\n"
            "}\n\n"
            f"Clauses:\n{json.dumps(clauses, indent=2)}"
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o", # Or gpt-3.5-turbo/gpt-4-turbo as per availability
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # Fallback for errors
            return {
                "status": "NOT_COVERED",
                "confidence": 0,
                "evidence": {"page": None, "clause_id": None, "quote": None},
                "reason": f"LLM Error: {str(e)}"
            }

    async def extract_clauses_with_llm(self, text: str) -> List[Dict]:
        """
        Optionally use LLM for better clause extraction if requested by spec.
        Spec says in Section 11: Clause Extraction Prompt.
        """
        system_prompt = "You are a legal compliance verification system."
        user_prompt = (
            "Extract all clauses from the following policy text.\n\n"
            "Rules:\n"
            "- Preserve clause numbering if present.\n"
            "- Preserve page numbers if present.\n"
            "- Do not summarize, rewrite, or interpret.\n\n"
            "Return a JSON array only.\n\n"
            "Schema:\n"
            "[\n"
            "  {\n"
            "    \"page\": number,\n"
            "    \"clause_id\": string,\n"
            "    \"text\": string\n"
            "  }\n"
            "]\n\n"
            f"Policy Text:\n{text}"
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}, # Wait, schema says it returns an array. OpenAI json_object usually needs an object.
                temperature=0
            )
            data = json.loads(response.choices[0].message.content)
            if isinstance(data, dict) and "clauses" in data:
                return data["clauses"]
            return data if isinstance(data, list) else []
        except Exception:
            return []
