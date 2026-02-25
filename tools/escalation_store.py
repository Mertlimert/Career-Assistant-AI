"""
Shared in-memory store for escalation tracking.
Used by: agent_loop (create), telegram_listener (resolve), main.py (poll endpoint).

States: pending -> resolved
"""
import uuid
import time
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def create_escalation(employer_message: str, reason: str, category: str) -> str:
    """Create a pending escalation, return its ID."""
    esc_id = uuid.uuid4().hex[:12]
    _store[esc_id] = {
        "status": "pending",
        "employer_message": employer_message,
        "reason": reason,
        "category": category,
        "created_at": time.time(),
        "telegram_msg_id": None,
        "professional_response": None,
        "original_reply": None,
        "resolved_at": None,
    }
    return esc_id


def link_telegram_msg(esc_id: str, telegram_msg_id: int):
    """Link a Telegram message_id to an escalation."""
    if esc_id in _store:
        _store[esc_id]["telegram_msg_id"] = telegram_msg_id


def resolve_escalation(esc_id: str, professional_response: str, original_reply: str):
    """Mark escalation as resolved with the professional response."""
    if esc_id in _store:
        _store[esc_id]["status"] = "resolved"
        _store[esc_id]["professional_response"] = professional_response
        _store[esc_id]["original_reply"] = original_reply
        _store[esc_id]["resolved_at"] = time.time()


def get_escalation(esc_id: str) -> dict[str, Any] | None:
    return _store.get(esc_id)


def find_by_telegram_msg_id(telegram_msg_id: int) -> tuple[str, dict] | None:
    """Find escalation by its linked Telegram message_id."""
    for esc_id, data in _store.items():
        if data.get("telegram_msg_id") == telegram_msg_id:
            return esc_id, data
    return None
