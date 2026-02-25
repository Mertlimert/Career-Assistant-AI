"""
Gate Agent: Decides whether the AI should respond or escalate to the human.
Uses LLM to analyze the message against profile/escalation rules.
"""
import json
import logging
from config import get_settings
from llm.gemini_client import generate_gemini

logger = logging.getLogger(__name__)

GATE_SYSTEM_PROMPT = """Sen bir karar mekanizmasısın. İşveren mesajını analiz edip şu kararı vereceksin:
AI asistan bu mesaja KENDİSİ cevap verebilir mi, yoksa mesaj sahibine (Mert'e) İLETİLMELİ mi?

{escalation_context}

ADAY PROFİLİ:
{profile_context}

KARAR KRİTERLERİ:
- AI CEVAP VEREBİLİR (can_respond: true): Mülakat daveti, genel tanışma, profildeki teknik yetenekler hakkında soru, müsaitlik sorma, basit iş teklifi
- SAHİBİNE İLETİLMELİ (can_respond: false): Maaş/ücret pazarlığı, sözleşme detayı, hukuki konu, profil dışı derin teknik soru, kişisel bilgi isteme, canlı test talebi, nihai iş teklifi onayı

Sadece JSON döndür:
{{"can_respond": true/false, "reason": "Kısa açıklama", "category": "safe|salary|legal|technical|personal|other"}}"""


def check_gate(
    employer_message: str,
    profile_context: str,
    escalation_context: str,
) -> dict:
    settings = get_settings()
    system = GATE_SYSTEM_PROMPT.format(
        escalation_context=escalation_context,
        profile_context=profile_context,
    )
    prompt = f"İşveren mesajı:\n{employer_message}\n\nKararın (JSON):"

    try:
        raw = generate_gemini(
            prompt,
            system_instruction=system,
            temperature=0.1,
            api_key=settings.gemini_api_key,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        return {
            "can_respond": bool(result.get("can_respond", True)),
            "reason": str(result.get("reason", "")),
            "category": str(result.get("category", "safe")),
        }
    except Exception as e:
        logger.warning("Gate agent failed, defaulting to AI response: %s", e)
        return {"can_respond": True, "reason": "Gate analiz hatası, varsayılan izin", "category": "safe"}
