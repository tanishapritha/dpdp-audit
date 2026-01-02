import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from app.core.config import settings

logger = logging.getLogger(__name__)

class RagasEvaluator:
    """
    Automated quality assurance service using RAGAS for evaluating RAG pipeline performance.
    """
    
    @staticmethod
    async def evaluate_compliance(results: List[Dict[str, Any]], all_clauses: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Executes a RAGAS evaluation on the generated compliance report.
        """
        # Requirements map for context alignment
        from app.services.compliance_engine import DPDP_REQUIREMENTS
        req_mapping = {r["id"]: r["description"] for r in DPDP_REQUIREMENTS}

        evaluation_data = {
            "question": [],
            "answer": [],
            "contexts": [],
        }

        for entry in results:
            req_id = entry.get("requirement_id")
            question = req_mapping.get(req_id, "Unknown Requirement")
            
            # Construct formatted 'answer' for evaluation
            answer = (
                f"Compliance Status: {entry.get('status')}. "
                f"Justification: {entry.get('reason')} "
                f"Evidence: {', '.join(entry.get('evidence', []))}"
            )
            
            # Use provided evidence as the retrieved context
            contexts = entry.get("evidence", [])
            if not contexts:
                contexts = ["No evidence retrieved from document."]

            evaluation_data["question"].append(question)
            evaluation_data["answer"].append(answer)
            evaluation_data["contexts"].append(contexts)

        if not evaluation_data["question"]:
            logger.warning("No data available for RAGAS evaluation.")
            return {"faithfulness": 0.0, "answer_relevancy": 0.0}

        try:
            # Prepare dataset for RAGAS
            ds = Dataset.from_dict(evaluation_data)
            
            # Ensure API environment is prepared (OpenRouter/OpenAI)
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
            os.environ["OPENAI_API_BASE"] = settings.OPENAI_API_BASE

            # Execute RAGAS evaluation
            evaluation_result = evaluate(
                ds,
                metrics=[faithfulness, answer_relevancy],
            )
            
            return {
                "faithfulness": float(evaluation_result.get("faithfulness", 0.0)),
                "answer_relevancy": float(evaluation_result.get("answer_relevancy", 0.0))
            }
            
        except Exception as e:
            logger.error(f"RAGAS evaluation pipeline failed: {str(e)}")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0
            }
