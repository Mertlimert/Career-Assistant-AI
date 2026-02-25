"""
Mobile Notification Tool.
Sends notifications via Telegram Bot API.
"""
import httpx
import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)


class NotificationTool:
    def __init__(self):
        self.settings = get_settings()
        t = (self.settings.telegram_bot_token or "").strip()
        c = (self.settings.telegram_chat_id or "").strip()
        self._enabled = bool(t and c and not t.startswith("your-") and not c.startswith("your-"))
        self._base_url = f"https://api.telegram.org/bot{t}"
        self._chat_id = c
        if not self._enabled:
            logger.warning("Telegram not configured. Notifications will be logged only.")

    def _send_telegram(self, text: str) -> Optional[int]:
        """Send message, return message_id or None."""
        if not self._enabled:
            return None
        payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"}
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(f"{self._base_url}/sendMessage", json=payload)
                r.raise_for_status()
                return r.json().get("result", {}).get("message_id")
        except Exception as e:
            logger.exception("Telegram send failed: %s", e)
            return None

    def notify_new_employer_message(self, employer_message: str, sender: str = "İşveren") -> Optional[int]:
        text = f"📌 <b>Yeni İşveren Mesajı</b>\n\nGönderen: {sender}\n\nMesaj: {employer_message[:500]}"
        logger.info("Notification [new_message]: %s", employer_message[:80])
        return self._send_telegram(text)

    def notify_response_sent(self, response_preview: str, employer_preview: str) -> Optional[int]:
        text = (
            f"✅ <b>Yanıt Gönderildi</b>\n\n"
            f"İşveren: {employer_preview[:200]}\n\n"
            f"Gönderilen yanıt: {response_preview[:300]}"
        )
        logger.info("Notification [response_sent]")
        return self._send_telegram(text)

    def notify_unknown_question(self, reason: str, employer_message: str) -> Optional[int]:
        text = (
            f"⚠️ <b>İnsan Müdahalesi Gerekli</b>\n\n"
            f"Sebep: {reason}\n\n"
            f"İşveren mesajı:\n{employer_message[:400]}\n\n"
            f"💬 Bu mesaja REPLY ile cevabınızı yazın, "
            f"bot profesyonel hale getirip gönderecek."
        )
        logger.info("Notification [escalation]: %s", reason)
        return self._send_telegram(text)
