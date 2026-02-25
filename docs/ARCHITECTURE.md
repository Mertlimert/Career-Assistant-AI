# Career Assistant AI Agent – Mimari Dokümantasyon

## 1. Sistem Özeti

Sistem, işveren mesajlarını alan ve aday (Mert) adına profesyonel yanıt üreten çok aşamalı bir AI agent pipeline'ıdır. Üç aşamalı güvenlik kontrolü (keyword, LLM gate, evaluator), Telegram entegrasyonu ile insan müdahalesi ve Telegram reply ile profesyonelleştirme özelliklerine sahiptir.

## 2. Mimari Diyagram

```
İşveren Mesajı (Web UI)
     │
     ▼
[main.py] ── FastAPI HTTP Endpoint (/process)
     │
     ▼
[agent_loop.py] ── Orkestratör
     │
     ├──► [1] Telegram Bildirimi: "Yeni mesaj geldi"
     │         (notification_tool.py)
     │
     ├──► [2] KEYWORD RISK CHECK (API çağrısı yok, anlık)
     │         Regex ile: maaş, sözleşme, tazminat, hukuk vb.
     │         ├── RİSKLİ → _escalate() ─► Telegram + Bekleme Yanıtı
     │         └── GÜVENLİ → Adım 3'e geç
     │
     ├──► [3] LLM GATE CHECK (gate_agent.py)
     │         AI profil+eskalasyon kurallarına bakarak karar verir:
     │         "Bu mesaja ben cevap verebilir miyim?"
     │         ├── HAYIR → _escalate() ─► Telegram + Bekleme Yanıtı
     │         └── EVET → Adım 4'e geç
     │
     ├──► [4] CAREER AGENT (career_agent.py)
     │         Profil context + sistem prompt ile LLM yanıt üretir
     │
     ├──► [5] EVALUATOR AGENT (evaluator_agent.py)
     │         5 kriter × 0-100 puan, toplam skor
     │         ├── Skor < 70 → Feedback + Revizyon (max 3 deneme)
     │         └── Skor ≥ 70 → Onay
     │
     └──► [6] Telegram: "Yanıt gönderildi" + Web UI'da sonuç

─── ESCALATION AKIŞI (Riskli Mesajlar) ───

_escalate() çağrıldığında:
  1. escalation_store'a kayıt oluştur (pending)
  2. Telegram'a uyarı mesajı gönder (message_id sakla)
  3. Web UI'da "Telegram'dan yanıt bekleniyor..." kartı göster
  4. Frontend /escalation/{id} endpoint'unu poll eder

─── TELEGRAM REPLY AKIŞI ───

telegram_listener.py (background thread):
  1. Telegram getUpdates ile reply'ları dinler
  2. Reply gelince → LLM ile profesyonelleştirir
  3. escalation_store'u "resolved" olarak günceller
  4. Telegram'a profesyonel versiyonu gönderir
  5. Frontend poll ile yakalar → UI güncellenir (yeşil kart)
```

## 3. Bileşenler

| Bileşen | Dosya | Açıklama |
|---------|-------|----------|
| **FastAPI Sunucu** | `main.py` | HTTP giriş noktası, /process, /escalation/{id}, /health endpoint'leri |
| **Agent Loop** | `agent_loop.py` | Tüm akışı yöneten orkestratör |
| **Career Agent** | `agents/career_agent.py` | Profil-bazlı profesyonel yanıt üretici |
| **Gate Agent** | `agents/gate_agent.py` | LLM ile karar mekanizması: "Cevap verebilir miyim?" |
| **Evaluator Agent** | `agents/evaluator_agent.py` | LLM-as-Judge: 5 kriter puanlama, onay/red |
| **LLM Client** | `llm/gemini_client.py` | OpenRouter veya Gemini API bağlantısı (otomatik seçim) |
| **Notification Tool** | `tools/notification_tool.py` | Telegram Bot API ile bildirim gönderici |
| **Telegram Listener** | `tools/telegram_listener.py` | Background polling, reply algılama, profesyonelleştirme |
| **Escalation Store** | `tools/escalation_store.py` | In-memory escalation takibi (pending → resolved) |
| **Profil Verisi** | `data/profile.json` | CV, yetenekler, eskalasyon kuralları |
| **Prompt Tasarımı** | `prompts/career_agent_prompts.py` | Career, Evaluator, Unknown Question system prompt'ları |
| **Web UI** | `static/index.html` | Interaktif demo arayüzü |

## 4. Tool Çağrı Mekanizması

Tüm tool'lar Python sınıfları olarak implemente edildi; LangChain Agent/Tool wrapper **kullanılmadı**. Tool invocation agent loop içinde doğrudan fonksiyon çağrısı ile yapılır:

```python
# agent_loop.py içinde sıralı çağrılar:
self.notification.notify_new_employer_message(...)  # Tool 1
keyword_risk_check(...)                              # Tool 2 (rule-based)
check_gate(...)                                      # Tool 3 (LLM)
self.career_agent.generate_response(...)             # Agent 1
self.evaluator.evaluate(...)                         # Agent 2
self.notification.notify_response_sent(...)          # Tool 1
```

## 5. Prompt Tasarımı

### Career Agent Prompt
- **System:** Profesyonel ton kuralları + profil context (isim, yetenekler, projeler, eğitim, tercihler)
- **User:** İşveren mesajı + (varsa) evaluator feedback
- **Amaç:** Profil ile uyumlu, hallüsinasyonsuz yanıt

### Gate Agent Prompt
- **System:** Eskalasyon kuralları (`profile.json`'dan) + profil context + karar kriterleri
- **User:** İşveren mesajı
- **Çıktı:** JSON `{can_respond, reason, category}`

### Evaluator Prompt
- **System:** 5 kriter tanımı + JSON çıktı formatı + eşik değeri
- **User:** İşveren mesajı + üretilen yanıt
- **Çıktı:** JSON `{scores, total_score, feedback, approved}`

### Profesyonelleştirme Prompt (Telegram Reply)
- **User:** İşveren sorusu + adayın ham cevabı
- **Amaç:** Anlamı koruyarak ton ve ifadeyi profesyonelleştir

## 6. Değerlendirme Stratejisi

- **Yöntem:** LLM-as-Judge
- **Model:** google/gemini-2.0-flash-lite-001 (OpenRouter üzerinden)
- **Kriterler:** professional_tone, clarity, completeness, safety, relevance (0-100)
- **Onay:** total_score ≥ EVALUATION_THRESHOLD (varsayılan 70)
- **Revizyon:** Onaylanmadıysa feedback Career Agent'a iletilir, max 3 deneme
- **Loglama:** Her deneme evaluation_log'a kaydedilir

## 7. İnsan Müdahalesi Pipeline (Human-in-the-Loop)

```
Riskli Mesaj Tespiti
  → escalation_store'a "pending" kayıt
  → Telegram'a uyarı (message_id kaydedilir)
  → Web UI: "Bekleniyor..." kartı + polling başlar
  → İnsan Telegram'da reply ile cevap yazar
  → Listener yakalar → LLM profesyonelleştirir
  → escalation_store "resolved" olarak güncellenir
  → Telegram'a profesyonel versiyon gönderilir
  → Web UI: Yeşil "Yanıt Gönderildi" kartı
```

## 8. Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| LLM | OpenRouter API (google/gemini-2.0-flash-lite-001) |
| Bildirim | Telegram Bot API |
| Profil | Statik JSON (data/profile.json) |
| Frontend | HTML/CSS/JavaScript (vanilla) |
| Konfigürasyon | pydantic-settings, python-dotenv |

## 9. Çalıştırma

```bash
# 1. .env dosyasını hazırla
GEMINI_API_KEY=sk-or-v1-...  # OpenRouter API key
TELEGRAM_BOT_TOKEN=...        # Telegram bot token
TELEGRAM_CHAT_ID=...          # Telegram chat ID

# 2. Bağımlılıkları kur
py -3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Sunucuyu başlat
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. Test senaryoları
py tests/run_test_cases.py
```
