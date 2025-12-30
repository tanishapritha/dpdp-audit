from typing import List, Dict
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
import pandas as pd
import os
from app.core.config import settings

class RagasEvaluator:
    @staticmethod
    async def evaluate_compliance(results: List[Dict], all_clauses: List[Dict]) -> Dict:
        """
        Evaluates the compliance results using Ragas.
        """
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truths": [] # Optional, maybe we don't have it
        }

        # DPDP Requirements for mapping
        from app.services.compliance_engine import DPDP_REQUIREMENTS
        req_map = {r["id"]: r["description"] for r in DPDP_REQUIREMENTS}

        for res in results:
            req_id = res["requirement_id"]
            question = req_map.get(req_id, "")
            answer = f"Status: {res['status']}. Reason: {res['reason']}. Evidence: {', '.join(res['evidence'])}"
            
            # Find the actual clauses used as evidence or filtered
            # For simplicity in MVP, we might just pass the evidence as context or 
            # the subset of clauses filtered for this requirement.
            # But here we need to map back to the actual text.
            contexts = res['evidence'] if res['evidence'] else ["No evidence provided."]
            
            data["question"].append(question)
            data["answer"].append(answer)
            data["contexts"].append(contexts)
            # data["ground_truths"].append([question]) # Dummy ground truth if needed

        dataset = Dataset.from_dict(data)
        
        # Note: RAGAS needs an OpenAI API key in environment
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        os.environ["OPENAI_API_BASE"] = settings.OPENAI_API_BASE
        
        try:
            # We use a subset of metrics for MVP
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy],
            )
            return {
                "faithfulness": result.get("faithfulness", 0.0),
                "answer_relevancy": result.get("answer_relevancy", 0.0)
            }
        except Exception:
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0
            }
