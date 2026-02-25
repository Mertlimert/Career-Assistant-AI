"""
Career Response Agent (Primary Agent).
Receives employer message, uses profile context, generates professional response.
"""
import json
import os
import logging
from config import get_settings
from prompts.career_agent_prompts import CAREER_SYSTEM_PROMPT
from llm.gemini_client import generate_gemini

logger = logging.getLogger(__name__)

_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "profile.json")


def _load_profile_raw() -> dict:
    try:
        with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Profile load failed: %s", e)
        return {}


def build_profile_context(data: dict | None = None) -> str:
    if data is None:
        data = _load_profile_raw()
    cp = data.get("candidate_profile", data)
    pi = cp.get("personal_info", {})
    tp = cp.get("technical_profile", {})
    proj = cp.get("projects_and_experience", [])
    edu = cp.get("education", {})
    prefs = pi.get("work_preferences", {})

    skills_flat = []
    for cat_skills in tp.values():
        if isinstance(cat_skills, list):
            skills_flat.extend(cat_skills)

    proj_lines = [f"  - {p.get('domain','')}: {p.get('description','')}" for p in proj]

    return "\n".join([
        f"İsim: {pi.get('name', '')}",
        f"Ünvan: {pi.get('title', '')}",
        f"E-posta: {pi.get('email', '')}",
        f"Müsaitlik: {pi.get('availability', '')}",
        f"Yetenekler: {', '.join(skills_flat)}",
        f"Projeler:\n" + "\n".join(proj_lines),
        f"Eğitim: {edu.get('degree', '')}",
        f"Tercihler: Remote={prefs.get('remote_ok','?')}, Taşınma={prefs.get('relocation','?')}, Maaş notu={prefs.get('salary_expectation_note','')}",
    ])


def build_escalation_context(data: dict | None = None) -> str:
    if data is None:
        data = _load_profile_raw()
    cfg = data.get("ai_interview_agent_config", {})
    triggers = cfg.get("escalation_triggers_to_human", [])
    oos = cfg.get("out_of_scope_topics", [])
    default_msg = cfg.get("default_handoff_message", "")

    lines = ["ESKALASYON KURALLARI (bu durumlarda sen cevap verme, sahibine ilet):"]
    for t in triggers:
        lines.append(f"  - Tetik: {t.get('trigger','')} -> Aksiyon: {t.get('action','')}")
    lines.append("\nKAPSAM DIŞI KONULAR (cevap verme):")
    for o in oos:
        lines.append(f"  - {o}")
    lines.append(f"\nVarsayılan devir mesajı: {default_msg}")
    return "\n".join(lines)


class CareerAgent:
    """Generate professional responses on behalf of the candidate."""

    def __init__(self):
        self.settings = get_settings()
        raw = _load_profile_raw()
        self._profile_context = build_profile_context(raw)
        self._escalation_context = build_escalation_context(raw)

    def generate_response(
        self,
        employer_message: str,
        evaluator_feedback: str | None = None,
    ) -> str:
        system = CAREER_SYSTEM_PROMPT.format(profile_context=self._profile_context)
        content = f"İşveren mesajı:\n{employer_message}"
        if evaluator_feedback:
            content += f"\n\nDeğerlendirici geri bildirimi (buna göre revize et): {evaluator_feedback}"
        try:
            raw = generate_gemini(
                content,
                system_instruction=system,
                temperature=0.5,
                api_key=self.settings.gemini_api_key,
            )
            return raw or ""
        except Exception as e:
            logger.exception("Career agent error: %s", e)
            return (
                "Mesajınız için teşekkür ederim. "
                "Yanıtımı kısa süre içinde ileteceğim. İyi günler dilerim."
            )
