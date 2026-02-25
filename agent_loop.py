"""
Agent Loop: orchestrates Gate, Career Agent, Evaluator, Notification tools.
Flow:
1. Employer message arrives -> Telegram notification
2. KEYWORD CHECK (fast, no API) -> obvious risks caught instantly
3. LLM GATE CHECK -> AI decides: "Can I answer this or should I forward to human?"
4. If human needed: create escalation, notify Telegram, frontend polls for resolution
5. If AI can handle: Career Agent -> Evaluator -> revise if needed -> send
"""
import logging
import re
from typing import Any
from config import get_settings
from agents.career_agent import CareerAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.gate_agent import check_gate
from tools.notification_tool import NotificationTool
from tools.escalation_store import create_escalation, link_telegram_msg

logger = logging.getLogger(__name__)

RISK_PATTERNS = [
    (r"maa[sş]", "salary"),
    (r"[üu]cret", "salary"),
    (r"br[üu]t", "salary"),
    (r"salary", "salary"),
    (r"s[öo]zle[sş]me", "legal"),
    (r"contract\b", "legal"),
    (r"hukuk", "legal"),
    (r"avukat", "legal"),
    (r"non[\s-]?compete", "legal"),
    (r"non[\s-]?disclosure", "legal"),
    (r"fikri m[üu]lkiyet", "legal"),
    (r"tazminat", "legal"),
    (r"(?<!\w)nda(?!\w)", "legal"),
]


def keyword_risk_check(message: str) -> dict[str, Any] | None:
    msg = (message or "").strip().lower()
    for pattern, category in RISK_PATTERNS:
        if re.search(pattern, msg):
            return {
                "is_unknown_or_unsafe": True,
                "confidence": 0.95,
                "reason": f"Anahtar kelime tespiti ({category})",
                "category": category,
                "source": "keyword",
            }
    return None


HUMAN_HANDOFF_RESPONSE = (
    "Mesajınız için teşekkür ederim. Bu konu, benim asistan olarak yetki alanımın "
    "dışında kalıyor ve Mert'in kendisinin doğrudan yanıtlaması gereken detaylar "
    "içeriyor. Konuyu kendisine iletiyorum; en kısa sürede size dönüş yapacaktır."
)


class AgentLoop:
    def __init__(self):
        self.settings = get_settings()
        self.career_agent = CareerAgent()
        self.evaluator = EvaluatorAgent()
        self.notification = NotificationTool()

    def _escalate(self, employer_message: str, reason: str, category: str, source: str) -> dict[str, Any]:
        esc_id = create_escalation(employer_message, reason, category)
        logger.info("Escalation created: %s (%s)", esc_id, reason)

        unknown_result = {
            "is_unknown_or_unsafe": True,
            "confidence": 0.95,
            "reason": reason,
            "category": category,
            "source": source,
        }
        try:
            msg_id = self.notification.notify_unknown_question(reason, employer_message)
            if msg_id:
                link_telegram_msg(esc_id, msg_id)
        except Exception:
            pass

        return {
            "response": HUMAN_HANDOFF_RESPONSE,
            "human_intervention": True,
            "escalation_id": esc_id,
            "evaluation_log": [],
            "unknown_result": unknown_result,
        }

    def process(self, employer_message: str, sender: str = "İşveren") -> dict[str, Any]:
        evaluation_log: list[dict] = []

        try:
            self.notification.notify_new_employer_message(employer_message, sender)
        except Exception:
            pass

        kw_result = keyword_risk_check(employer_message)
        if kw_result:
            logger.info("Keyword risk detected: %s", kw_result["reason"])
            return self._escalate(
                employer_message,
                reason=kw_result["reason"],
                category=kw_result["category"],
                source="keyword",
            )

        try:
            gate_result = check_gate(
                employer_message,
                profile_context=self.career_agent._profile_context,
                escalation_context=self.career_agent._escalation_context,
            )
            if not gate_result["can_respond"]:
                logger.info("LLM gate escalated: %s", gate_result["reason"])
                return self._escalate(
                    employer_message,
                    reason=gate_result["reason"],
                    category=gate_result["category"],
                    source="llm_gate",
                )
        except Exception as e:
            logger.warning("Gate check failed, proceeding with AI: %s", e)

        safe_result = {
            "is_unknown_or_unsafe": False,
            "confidence": 1.0,
            "reason": "",
            "category": "safe",
            "source": "passed",
        }

        feedback_for_revision = None
        response_text = ""
        for attempt in range(1, self.settings.max_revision_attempts + 1):
            try:
                response_text = self.career_agent.generate_response(
                    employer_message, evaluator_feedback=feedback_for_revision
                )
            except Exception as e:
                logger.exception("Career Agent LLM hatası: %s", e)
                raise RuntimeError(f"AI yanıt üretemedi (LLM API hatası): {e}") from e

            if not (response_text or "").strip():
                raise RuntimeError("AI boş yanıt üretti. API anahtarınızı kontrol edin.")

            try:
                eval_result = self.evaluator.evaluate(employer_message, response_text)
            except Exception as e:
                logger.exception("Evaluator LLM hatası: %s", e)
                raise RuntimeError(f"Değerlendirici çalışamadı (LLM API hatası): {e}") from e

            evaluation_log.append({
                "attempt": attempt,
                "total_score": eval_result.get("total_score"),
                "scores": eval_result.get("scores"),
                "feedback": eval_result.get("feedback"),
                "approved": eval_result.get("approved"),
            })
            if eval_result.get("approved"):
                try:
                    self.notification.notify_response_sent(response_text[:200], employer_message[:200])
                except Exception:
                    pass
                return {
                    "response": response_text,
                    "human_intervention": False,
                    "escalation_id": None,
                    "evaluation_log": evaluation_log,
                    "unknown_result": safe_result,
                }
            feedback_for_revision = eval_result.get("feedback", "Yanıtı daha profesyonel ve net yap.")

        return {
            "response": response_text,
            "human_intervention": False,
            "escalation_id": None,
            "evaluation_log": evaluation_log,
            "unknown_result": safe_result,
            "max_revisions_reached": True,
        }
