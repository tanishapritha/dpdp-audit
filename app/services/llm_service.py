import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # OpenRouter requires specific headers for better discoverability
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            default_headers={
                "HTTP-Referer": "https://compliance-engine.ai",
                "X-Title": "Company Compliance Engine",
            }
        )
        # Default to a high-performance model available on OpenRouter
        self.model = "openai/gpt-4o-mini" 

    async def verify_requirement(self, requirement_text: str, clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify a statutory requirement against a candidate set of policy clauses.
        """
        system_prompt = (
            "You are a specialized legal compliance auditor. Your objective is to verify "
            "if specific regulatory requirements from the Digital Personal Data Protection Act (DPDP), 2023 "
            "are explicitly addressed in the provided segments of a privacy policy.\n\n"
            "Constraints:\n"
            "1. Strict Adherence: Only mark as COVERED if the requirement is explicitly stated.\n"
            "2. Evidence: You must provide a verbatim quote from the text.\n"
            "3. Determinism: Return a structured JSON response only.\n"
            "4. Classification: Use COVERED, PARTIAL, or NOT_COVERED."
        )

        user_prompt = (
            f"Statutory Requirement:\n{requirement_text}\n\n"
            f"Policy Segments for Review:\n{json.dumps(clauses, indent=2)}\n\n"
            "Output Schema:\n"
            "{\n"
            "  \"status\": \"COVERED | PARTIAL | NOT_COVERED\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"evidence\": {\"page\": int, \"clause_id\": \"string\", \"quote\": \"string\"},\n"
            "  \"reason\": \"Detailed analytical justification\"\n"
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM verification failed: {str(e)}")
            return {
                "status": "NOT_COVERED",
                "confidence": 0,
                "evidence": {"page": None, "clause_id": None, "quote": None},
                "reason": f"System error during analysis: {str(e)}"
            }

    async def extract_clauses_with_llm(self, text: str) -> List[Dict[str, Any]]:
        """
        Decomposes raw policy text into structured, addressable clauses.
        """
        system_prompt = "You are an expert legal document parser."
        user_prompt = (
            "Analyze the following privacy policy text and extract individual clauses.\n"
            "Maintain the original structure and context.\n\n"
            "Text:\n"
            f"{text[:10000]}\n\n" # Truncate for safety in MVP context
            "Return JSON array of objects: {\"page\": int, \"clause_id\": string, \"text\": string}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            content = json.loads(response.choices[0].message.content)
            # Handle both list and object-wrapped list responses
            if isinstance(content, dict):
                for key in ["clauses", "data", "segments"]:
                    if key in content and isinstance(content[key], list):
                        return content[key]
            return content if isinstance(content, list) else []
        except Exception as e:
            logger.error(f"Clause extraction failed: {str(e)}")
            return []
