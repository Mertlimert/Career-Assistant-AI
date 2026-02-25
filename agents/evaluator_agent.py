"""
Response Evaluator Agent (Critic/Judge).
Assesses generated response: tone, clarity, completeness, safety, relevance.
Gemini API kullanir.
"""
import json
import re
import logging
from config import get_settings
from prompts.career_agent_prompts import EVALUATOR_SYSTEM_PROMPT
from llm.gemini_client import generate_gemini

logger = logging.getLogger(__name__)


class EvaluatorAgent:
    """Evaluate response quality and safety."""

    def __init__(self):
        self.settings = get_settings()
        self.threshold = self.settings.evaluation_threshold

    def evaluate(
        self,
        employer_message: str,
        generated_response: str,
    ) -> dict:
        """
        Returns dict: scores, total_score, feedback, approved.
        """
        prompt = f"""İşveren mesajı:
{employer_message}

Üretilen yanıt:
{generated_response}

Eşik (approved için total_score >= bu olmalı): {self.threshold}"""

        try:
            system = EVALUATOR_SYSTEM_PROMPT.format(threshold=self.threshold)
        except KeyError:
            system = EVALUATOR_SYSTEM_PROMPT.replace("{threshold}", str(self.threshold))
        try:
            text = generate_gemini(
                prompt,
                system_instruction=system,
                temperature=0.2,
                api_key=self.settings.gemini_api_key,
            )
        except Exception as e:
            logger.exception("Evaluator error: %s", e)
            raise RuntimeError(f"Evaluator LLM hatası: {e}") from e

        # Parse JSON
        try:
            if "```" in text:
                text = re.sub(r"^.*?```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```.*$", "", text)
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {
                "scores": {"professional_tone": 70, "clarity": 70, "completeness": 70, "safety": 70, "relevance": 70},
                "total_score": 70,
                "feedback": "Otomatik değerlendirme yapılamadı; varsayılan skor kullanıldı.",
                "approved": True,
            }

        total = data.get("total_score", 0)
        if not isinstance(total, (int, float)):
            total = 70
        data["approved"] = total >= self.threshold
        return data
