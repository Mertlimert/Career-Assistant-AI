"""
FastAPI backend for Career Assistant AI Agent.
"""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_loop import AgentLoop
from tools.telegram_listener import TelegramReplyListener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_loop: AgentLoop | None = None
telegram_listener: TelegramReplyListener | None = None

GENEL_HATA_MESAJI = "Yanıt üretilirken hata oluştu. Lütfen tekrar deneyin."


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_loop, telegram_listener
    agent_loop = AgentLoop()
    telegram_listener = TelegramReplyListener()
    telegram_listener.start()
    yield
    if telegram_listener:
        telegram_listener.stop()
    agent_loop = None


app = FastAPI(
    title="Career Assistant AI Agent",
    description="AI agent that responds to employers on your behalf with evaluator and notifications.",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
def genel_hata_yakala(request: Request, exc: Exception):
    """Islenmeyen hatalarda 500 ve sabit mesaj. HTTPException oldugu gibi birakilir."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Yakalanan hata: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": GENEL_HATA_MESAJI},
    )


class EmployerMessageRequest(BaseModel):
    message: str
    sender: str = "İşveren"


class ProcessResponse(BaseModel):
    response: str
    human_intervention: bool
    evaluation_log: list
    unknown_result: dict | None = None
    max_revisions_reached: bool | None = None


# Optional: serve demo frontend at /
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    """Redirect to demo page."""
    from fastapi.responses import FileResponse
    p = Path(__file__).parent / "static" / "index.html"
    if p.exists():
        return FileResponse(p)
    return {"message": "Career Assistant API. POST /process with {message, sender}. Docs: /docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "career-assistant-agent"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


@app.post("/process")
def process_message(req: EmployerMessageRequest):
    """Receive employer message, run agent loop, return final response."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if agent_loop is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    from config import get_settings
    if not (get_settings().gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY .env dosyasinda tanimli degil. .env dosyasina ekleyip sunucuyu yeniden baslatin.",
        )
    try:
        result = agent_loop.process(employer_message=req.message, sender=req.sender)
    except Exception as e:
        logger.exception("Process error: %s", e)
        err_msg = str(e).lower()
        if "401" in err_msg or "authentication" in err_msg or "unauthorized" in err_msg or "user not found" in err_msg:
            raise HTTPException(status_code=503, detail="API anahtarı geçersiz veya süresi dolmuş. .env dosyasındaki GEMINI_API_KEY değerini kontrol edin.")
        if "api" in err_msg and ("hata" in err_msg or "error" in err_msg or "fail" in err_msg):
            raise HTTPException(status_code=503, detail=f"LLM API hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sistem hatası: {e}")

    try:
        # Yaniti JSON-guvenli dict yapip JSONResponse ile dondur
        unknown = result.get("unknown_result")
        if unknown is not None:
            try:
                c = float(unknown.get("confidence", 0.0) or 0.0)
                if c != c:
                    c = 0.0
            except (TypeError, ValueError):
                c = 0.0
            unknown = {
                "is_unknown_or_unsafe": bool(unknown.get("is_unknown_or_unsafe", False)),
                "confidence": c,
                "reason": str(unknown.get("reason", "") or ""),
                "category": str(unknown.get("category", "other") or "other"),
            }
        ev_log = result.get("evaluation_log") or []
        ev_log_safe = []
        for item in ev_log:
            if not isinstance(item, dict):
                continue
            ts = item.get("total_score")
            if isinstance(ts, (int, float)) and ts == ts:
                ts_clean = ts
            else:
                ts_clean = 0
            ev_log_safe.append({
                "attempt": int(item.get("attempt", 0)) if item.get("attempt") is not None else 0,
                "total_score": ts_clean,
                "scores": item.get("scores") if isinstance(item.get("scores"), dict) else {},
                "feedback": str(item.get("feedback", "") or ""),
                "approved": bool(item.get("approved", False)),
            })
        body = {
            "response": str(result.get("response", "") or ""),
            "human_intervention": bool(result.get("human_intervention", False)),
            "escalation_id": result.get("escalation_id"),
            "evaluation_log": ev_log_safe,
            "unknown_result": unknown,
            "max_revisions_reached": bool(result.get("max_revisions_reached", False)),
        }
        return JSONResponse(content=body)
    except Exception as e:
        logger.exception("Response build error: %s", e)
        return JSONResponse(status_code=500, content={"detail": GENEL_HATA_MESAJI})


@app.get("/escalation/{esc_id}")
def poll_escalation(esc_id: str):
    """Frontend polls this to check if human has replied via Telegram."""
    from tools.escalation_store import get_escalation
    data = get_escalation(esc_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return {
        "status": data["status"],
        "professional_response": data.get("professional_response"),
        "original_reply": data.get("original_reply"),
        "employer_message": data.get("employer_message"),
    }


@app.get("/profile")
def get_profile():
    """Return current profile context (for demo/documentation)."""
    try:
        import json
        import os
        path = os.path.join(os.path.dirname(__file__), "data", "profile.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
