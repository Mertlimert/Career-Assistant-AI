"""
Unknown Question Detection Tool.
Detects when the agent does not have sufficient knowledge,
question is outside expertise, or confidence is low.
Gemini API kullanir.
"""
import json
import logging
from typing import Any
from config import get_settings
from prompts.career_agent_prompts import UNKNOWN_QUESTION_DETECTOR_PROMPT
from tools.notification_tool import NotificationTool
from llm.gemini_client import generate_gemini

logger = logging.getLogger(__name__)


class UnknownQuestionTool:
    """Detect unknown/unsafe questions and trigger alert."""

    CONFIDENCE_THRESHOLD = 0.6  # below this, treat as unknown

    def __init__(self):
        self.settings = get_settings()
        self.notification = NotificationTool()

    def _get_profile_scope(self) -> str:
        """Load profile scope from static data (skills, out_of_scope)."""
        try:
            import os
            path = os.path.join(os.path.dirname(__file__), "..", "data", "profile.json")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            skills = data.get("skills", [])
            out = data.get("preferences", {}).get("out_of_scope", [])
            return f"Yetkinlikler: {', '.join(skills)}. Kapsam dışı: {', '.join(out)}"
        except Exception as e:
            logger.warning("Profile load failed: %s", e)
            return "Yazılım geliştirme, backend, API."

    def check(self, employer_message: str) -> dict[str, Any]:
        """
        Check if the message is unknown/unsafe.
        Returns dict with is_unknown_or_unsafe, confidence, reason, category.
        If unknown/unsafe, sends notification and logs.
        """
        profile_scope = self._get_profile_scope()
        prompt = UNKNOWN_QUESTION_DETECTOR_PROMPT.format(
            profile_scope=profile_scope,
            employer_message=employer_message,
        )
        try:
            text = generate_gemini(
                prompt,
                temperature=0.2,
                api_key=self.settings.gemini_api_key,
            )
            if not text:
                raise ValueError("Model bos yanit dondu")
            # Extract JSON (handle markdown code block)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
        except Exception as e:
            logger.exception("Unknown question detector failed: %s", e)
            data = {
                "is_unknown_or_unsafe": True,
                "confidence": 0.0,
                "reason": "Parser/API hatası",
                "category": "other",
            }

        is_unknown = data.get("is_unknown_or_unsafe", False)
        confidence = float(data.get("confidence", 0.0))
        if confidence < self.CONFIDENCE_THRESHOLD and not is_unknown:
            is_unknown = True
            data["reason"] = (data.get("reason") or "") + " (Düşük güven skoru)"

        if is_unknown:
            reason = data.get("reason", "Bilinmeyen/riskli soru")
            logger.warning(
                "Unknown/unsafe question detected: %s | category=%s",
                reason,
                data.get("category"),
            )
            self.notification.notify_unknown_question(reason, employer_message)

        return {
            "is_unknown_or_unsafe": bool(is_unknown),
            "confidence": float(confidence),
            "reason": str(data.get("reason", "") or ""),
            "category": str(data.get("category", "other") or "other"),
        }
