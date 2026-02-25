# Career Assistant AI Agent – Mimari Dokümantasyon

## 1. Sistem Özeti

Sistem, işveren mesajlarını alan, aday adına profesyonel yanıt üreten, bu yanıtı değerlendiren ve gerekirse revize eden bir agent döngüsünden oluşur. Bilinmeyen/riskli sorularda insan müdahalesi tetiklenir; yeni mesaj ve gönderilen yanıt için bildirim gönderilir.

## 2. Mimari Diyagram (Flow)

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    EMPLOYER MESSAGE                          │
                    └───────────────────────────┬─────────────────────────────────┘
                                                │
                                                ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │              NOTIFICATION TOOL (new message)                 │
                    │              → Telegram / log                               │
                    └───────────────────────────┬─────────────────────────────────┘
                                                │
                                                ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │           UNKNOWN QUESTION DETECTION TOOL                    │
                    │           (LLM: salary, legal, out-of-scope, ambiguous)    │
                    └───────────────────────────┬─────────────────────────────────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        │ is_unknown_or_unsafe?                          │
                        ▼ YES                              ▼ NO          │
        ┌───────────────────────────────┐    ┌─────────────────────────────────────┐
        │ Notify human intervention     │    │        CAREER AGENT (Primary)       │
        │ Return generic reply          │    │        Profile + prompt → response   │
        └───────────────────────────────┘    └───────────────────┬─────────────────┘
                                                                  │
                                                                  ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │              RESPONSE EVALUATOR (Critic/Judge)               │
                    │              tone, clarity, completeness, safety, relevance │
                    │              total_score, feedback, approved?               │
                    └───────────────────────────┬─────────────────────────────────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        │ approved && score >= threshold?                │
                        ▼ NO (revise)                     ▼ YES         │
        ┌───────────────────────────────┐    ┌─────────────────────────────────────┐
        │ feedback → Career Agent       │    │ Notify "response sent"               │
        │ (loop, max N attempts)        │    │ Return final response                │
        └───────────────┬───────────────┘    └─────────────────────────────────────┘
                        │
                        └──────────────────────► (back to Career Agent)
```

## 3. Bileşenler

| Bileşen | Açıklama |
|--------|----------|
| **Career Agent** | İşveren mesajı + profil (CV) context ile profesyonel yanıt üretir. Revize için evaluator feedback kullanır. |
| **Evaluator Agent** | LLM-as-Judge: professional_tone, clarity, completeness, safety, relevance puanlar; total_score ve approved kararı. |
| **Notification Tool** | Yeni mesaj, yanıt gönderildi, bilinmeyen soru için Telegram (veya log) bildirimi. |
| **Unknown Question Tool** | LLM ile mesajı sınıflandırır (salary, legal, technical, ambiguous); güven düşükse veya riskli kategorideyse bildirim + human_intervention. |
| **Agent Loop** | Tüm adımları sırayla yürüten orkestratör (agent_loop.py). |

## 4. Tool Çağrı Mekanizması

- **Doğrudan fonksiyon çağrısı:** Tools (notification, unknown_question) ve agent’lar Python sınıfları olarak implemente edildi; LangChain Agent/Tool wrapper kullanılmadı.
- **Sıra:** Agent loop içinde sabit sıra: notify → unknown check → career generate → evaluate → (revise veya send).

## 5. Prompt Tasarımı

- **Career Agent:** `prompts/career_agent_prompts.py` – Sistem prompt’unda profil context placeholder, kullanıcı mesajında işveren metni; revize turunda evaluator feedback eklenir.
- **Evaluator:** Aynı dosyada – JSON çıktı (scores, total_score, feedback, approved); eşik değeri prompt’a enjekte edilir.
- **Unknown Question:** Aynı dosyada – risk kategorileri ve profil kapsamı verilir; çıktı JSON (is_unknown_or_unsafe, confidence, reason, category).

## 6. Değerlendirme Stratejisi

- **Yöntem:** LLM-as-Judge (GPT-4o-mini).
- **Kriterler:** professional_tone, clarity, completeness, safety, relevance (her biri 0–100).
- **Onay:** total_score >= EVALUATION_THRESHOLD (varsayılan 70) → approved.
- **Revizyon:** Approved değilse feedback Career Agent’a iletilir; en fazla MAX_REVISION_ATTEMPTS (3) tekrarlanır.
- **Loglama:** Her deneme evaluation_log’a (attempt, total_score, scores, feedback, approved) yazılır.

## 7. Başarısızlık / Edge Case’ler

- **API hatası:** Career veya Evaluator hata verirse fallback kısa mesaj veya varsayılan skor kullanılır.
- **JSON parse hatası (Evaluator):** Kural tabanlı varsayılan skor (70) ve approved=true.
- **Bilinmeyen soru parser hatası:** is_unknown_or_unsafe=true, bildirim gönderilir.
- **Max revizyon aşıldı:** Son üretilen yanıt döndürülür, log’da max_revisions_reached işaretlenir.

## 8. Teknoloji Yığını

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **LLM:** Google Gemini API (gemini-1.5-flash)
- **Bildirim:** Telegram Bot API (opsiyonel; token/chat_id yoksa sadece log)
- **Profil:** Statik JSON (data/profile.json); ileride RAG ile genişletilebilir.

## 9. Çalıştırma

```bash
# .env: GEMINI_API_KEY=... (https://aistudio.google.com/apikey) (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID opsiyonel)
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Test: POST /process {"message": "...", "sender": "İşveren"}
# 3 test senaryosu: python tests/run_test_cases.py
```
