"""
LLM client - OpenRouter (OpenAI-compatible) veya Gemini.
API key sk-or- ile basliyorsa OpenRouter, diger durumlarda Gemini kullanir.
"""
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "google/gemini-2.0-flash-lite-001"


def generate_gemini(
    prompt: str,
    *,
    system_instruction: Optional[str] = None,
    temperature: float = 0.5,
    api_key: str = "",
    model: str = "",
) -> str:
    if not api_key:
        from config import get_settings
        api_key = (get_settings().gemini_api_key or "").strip()
    if not api_key:
        raise ValueError("API key tanimli degil (.env GEMINI_API_KEY)")

    if api_key.startswith("sk-or"):
        return _call_openrouter(prompt, system_instruction, temperature, api_key, model)
    else:
        return _call_gemini(prompt, system_instruction, temperature, api_key, model)


def _call_openrouter(
    prompt: str,
    system_instruction: Optional[str],
    temperature: float,
    api_key: str,
    model: str,
) -> str:
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=api_key)
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model or OPENROUTER_MODEL,
        messages=messages,
        temperature=temperature,
    )
    raw = response.choices[0].message.content
    return (raw or "").strip()


def _call_gemini(
    prompt: str,
    system_instruction: Optional[str],
    temperature: float,
    api_key: str,
    model: str,
) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    kwargs = {}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    gen_model = genai.GenerativeModel(model or "gemini-1.5-flash", **kwargs)
    response = gen_model.generate_content(prompt)
    try:
        text = response.text
    except Exception:
        return ""
    return (text or "").strip()
