"""
Telegram Reply Listener.
Polls Telegram for replies to escalation messages.
When the human replies:
1. Takes the raw human reply
2. Uses LLM to make it professional
3. Sends the professional version back on Telegram
4. Updates escalation store so the web UI picks it up
"""
import threading
import time
import logging
import httpx
from config import get_settings
from tools.escalation_store import find_by_telegram_msg_id, resolve_escalation

logger = logging.getLogger(__name__)

PROFESSIONALIZE_PROMPT = """Sen bir kariyer asistanısın. Aday, bir işverenin sorusuna kendi cevabını yazdı.
Senin görevin bu cevabı profesyonel, nazik ve iş dünyasına uygun bir dille yeniden yazmak.

KURALLAR:
- Anlamı değiştirme, sadece tonu ve ifadeyi profesyonelleştir
- Kısa ve öz tut
- Türkçe yaz
- Sadece profesyonel yanıt metnini döndür, başka açıklama ekleme

İşverenin orijinal sorusu:
{employer_message}

Adayın ham cevabı:
{human_reply}

Profesyonel hali:"""


class TelegramReplyListener:
    def __init__(self):
        self.settings = get_settings()
        token = (self.settings.telegram_bot_token or "").strip()
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._chat_id = (self.settings.telegram_chat_id or "").strip()
        self._enabled = bool(token and self._chat_id and not token.startswith("your-"))
        self._offset = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        if not self._enabled:
            logger.warning("Telegram listener disabled (not configured)")
            return
        self._flush_old_updates()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Telegram reply listener started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Telegram reply listener stopped")

    def _flush_old_updates(self):
        """Skip all old pending updates so we only handle new ones."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self._base_url}/getUpdates", params={"offset": -1, "timeout": 0})
                results = r.json().get("result", [])
                if results:
                    self._offset = results[-1]["update_id"] + 1
                    logger.info("Flushed old updates, offset=%s", self._offset)
        except Exception:
            pass

    def _poll_loop(self):
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.warning("Telegram poll error: %s", e)
            time.sleep(2)

    def _poll_once(self):
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.get(
                    f"{self._base_url}/getUpdates",
                    params={"offset": self._offset, "timeout": 10},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            logger.warning("getUpdates failed: %s", e)
            return

        for update in data.get("result", []):
            update_id = update.get("update_id", 0)
            self._offset = max(self._offset, update_id + 1)

            msg = update.get("message", {})
            reply_to = msg.get("reply_to_message")
            if not reply_to:
                continue

            reply_to_id = reply_to.get("message_id")
            human_text = (msg.get("text") or "").strip()
            chat_id = str(msg.get("chat", {}).get("id", ""))

            if chat_id != self._chat_id or not human_text:
                continue

            match = find_by_telegram_msg_id(reply_to_id)
            if not match:
                continue

            esc_id, esc_data = match
            employer_message = esc_data["employer_message"]
            logger.info("Reply received for escalation %s: %s", esc_id, human_text[:80])
            self._handle_reply(esc_id, msg["message_id"], employer_message, human_text)

    def _handle_reply(self, esc_id: str, user_msg_id: int, employer_message: str, human_reply: str):
        from llm.gemini_client import generate_gemini

        prompt = PROFESSIONALIZE_PROMPT.format(
            employer_message=employer_message,
            human_reply=human_reply,
        )
        try:
            professional = generate_gemini(
                prompt,
                temperature=0.3,
                api_key=self.settings.gemini_api_key,
            )
        except Exception as e:
            logger.exception("Professionalize LLM failed: %s", e)
            professional = ""

        if not professional.strip():
            self._send_message(
                f"⚠️ Profesyonelleştirme başarısız.\n\nOrijinal: {human_reply}",
                reply_to=user_msg_id,
            )
            return

        resolve_escalation(esc_id, professional.strip(), human_reply)

        response_text = (
            f"✅ <b>Profesyonel Yanıt (İşverene gönderildi):</b>\n\n"
            f"{professional.strip()}\n\n"
            f"───────────\n"
            f"📝 <b>Orijinal cevabınız:</b> {human_reply}"
        )
        self._send_message(response_text, reply_to=user_msg_id)
        logger.info("Escalation %s resolved", esc_id)

    def _send_message(self, text: str, reply_to: int | None = None):
        payload: dict = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(f"{self._base_url}/sendMessage", json=payload).raise_for_status()
        except Exception as e:
            logger.exception("Telegram send failed: %s", e)
