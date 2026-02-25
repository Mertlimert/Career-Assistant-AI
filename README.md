# Career Assistant AI Agent

İşverenlerle aday adına iletişim kuran, yanıtları değerlendiren, riskli durumlarda insan müdahalesi tetikleyen ve Telegram entegrasyonlu çok aşamalı AI agent sistemi.

## Özellikler

- **Career Agent (Birincil):** İşveren mesajı + CV/profil ile profesyonel yanıt üretir
- **Gate Agent (Karar Verici):** LLM ile "Bu mesaja ben cevap verebilir miyim?" kararını verir
- **Response Evaluator (Jüri):** Ton, netlik, bütünlük, güvenlik ve uygunluk puanları; eşik altında otomatik revizyon
- **Telegram Bildirim:** Yeni mesaj, yanıt gönderildi ve insan müdahalesi uyarıları
- **Telegram Reply → Profesyonelleştirme:** Riskli sorulara Telegram'dan reply ile cevap yaz, bot profesyonel hale getirsin
- **3 Aşamalı Güvenlik:** Keyword check → LLM Gate → Evaluator

## Nasıl Çalışır?

```
İşveren Mesajı → Telegram Bildirimi
  → Keyword Risk Check (anlık, API yok)
    → Riskli? → Telegram'a ilet, Web UI'da bekle, reply ile cevapla
    → Güvenli? → LLM Gate kontrolü
      → Gate reddetti? → Telegram'a ilet
      → Gate onayladı? → Career Agent yanıt üretir
        → Evaluator puanlar (5 kriter)
          → Skor < 70? → Revizyon (max 3)
          → Skor ≥ 70? → Onay, gönder
```

## Kurulum

```bash
cd "AI Project 1"
py -3 -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

`.env` dosyası oluştur:
```
GEMINI_API_KEY=sk-or-v1-...   # OpenRouter API key
TELEGRAM_BOT_TOKEN=...         # Telegram bot token
TELEGRAM_CHAT_ID=...           # Telegram chat ID
EVALUATION_THRESHOLD=70
MAX_REVISION_ATTEMPTS=3
```

**Hızlı başlatma (Windows):** `run.bat` dosyasına çift tıklayın.

## Çalıştırma

```bash
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Demo:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 3 Test Senaryosu

```bash
py tests/run_test_cases.py
```

| # | Senaryo | Beklenen Davranış |
|---|---------|-------------------|
| 1 | Standart mülakat daveti | AI profesyonel yanıt üretir, insan müdahalesi yok |
| 2 | Teknik soru (FastAPI/JWT) | AI profil kapsamında yanıt verir |
| 3 | Maaş + sözleşme sorusu | İnsan müdahalesi tetiklenir, AI yanıt üretmez |

## Proje Yapısı

```
├── main.py                      # FastAPI sunucusu
├── agent_loop.py                # Orkestratör (tüm akışı yönetir)
├── config.py                    # Ayarlar (.env okuma)
├── requirements.txt
├── .env                         # API anahtarları
│
├── agents/
│   ├── career_agent.py          # Birincil Agent (yanıt üretici)
│   ├── gate_agent.py            # Gate Agent (karar verici)
│   └── evaluator_agent.py       # Evaluator Agent (jüri)
│
├── llm/
│   └── gemini_client.py         # LLM bağlantısı (OpenRouter/Gemini)
│
├── tools/
│   ├── notification_tool.py     # Telegram bildirim
│   ├── telegram_listener.py     # Reply dinleyici + profesyonelleştirme
│   ├── escalation_store.py      # Escalation takibi (pending → resolved)
│   └── unknown_question_tool.py # (Legacy) LLM tabanlı soru tespiti
│
├── prompts/
│   └── career_agent_prompts.py  # System prompt'ları
│
├── data/
│   └── profile.json             # CV/profil + eskalasyon kuralları
│
├── static/
│   └── index.html               # Web arayüzü
│
├── tests/
│   ├── test_cases.py            # 3 test senaryosu
│   └── run_test_cases.py        # Test runner
│
└── docs/
    ├── ARCHITECTURE.md          # Mimari dokümantasyon
    ├── REPORT.md                # Kısa rapor (3-5 sayfa)
    └── flow_diagram.mmd         # Mermaid akış diyagramı
```

## Dokümantasyon

- **Mimari:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Rapor:** [docs/REPORT.md](docs/REPORT.md)
- **Akış Diyagramı:** [docs/flow_diagram.mmd](docs/flow_diagram.mmd)

## Lisans

Eğitim projesi – ders kapsamında kullanım.
