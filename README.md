# Career Assistant AI Agent

İşverenlerle aday adına iletişim kuran, yanıtları değerlendiren ve bilinmeyen/riskli sorularda insan müdahalesi isteyen AI agent sistemi.

## Özellikler

- **Career Agent (Birincil):** İşveren mesajı + CV/profil ile profesyonel yanıt üretir; davet kabul/red, teknik sorular, nazik red.
- **Response Evaluator (Critic):** Ton, netlik, bütünlük, güvenlik ve uygunluk puanları; eşik altında otomatik revizyon.
- **Bildirim Aracı:** Yeni mesaj ve “yanıt gönderildi” için Telegram ile mobil bildirim (opsiyonel).
- **Bilinmeyen Soru Tespiti:** Uzun mesajlarda maaş/hukuk vb. anahtar kelime varsa bildirim + insan müdahalesi.

**İnsan müdahalesi ne zaman ve ne olur?**  
Sistem mesajı riskli bulursa (ör. maaş pazarlığı, hukuki soru) işverene otomatik bir *bekleme* cevabı gider: *"Mesajınız için teşekkür ederim. Bu konuda size özel olarak dönüş yapacağım. Kısa süre içinde yanıt vereceğim."* Aynı anda size Telegram ile bildirim gider (Telegram açıksa). Gerçek yanıtı **siz** işverene kendi kanalınızdan (e-posta, LinkedIn vb.) yazarsınız; bu demo arayüzü yanıt girişi almaz, sadece durumu gösterir.

## Kurulum

**Windows’ta `python` bulunamıyorsa** `py` kullanın (Python Launcher):

```bash
cd "AI Project 1"
py -3 -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
# .env içine GEMINI_API_KEY=... ekleyin (https://aistudio.google.com/apikey)
# Telegram için: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (opsiyonel)
```

**Hızlı başlatma (Windows):** `run.bat` dosyasına çift tıklayın; venv yoksa oluşturur, bağımlılıkları kurar ve sunucuyu başlatır.

## Çalıştırma

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# veya: py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **API:** http://localhost:8000  
- **Docs:** http://localhost:8000/docs  
- **Test isteği:**
  ```bash
  curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d "{\"message\": \"Merhaba, sizi yarın mülakata davet ediyoruz.\", \"sender\": \"ABC Şirket\"}"
  ```

## 3 Test Senaryosu

```bash
# GEMINI_API_KEY gerekli
py tests/run_test_cases.py
# veya: run_tests.bat
```

1. **Standart mülakat daveti** – Profesyonel kabul/yanıt  
2. **Teknik soru** – Profil kapsamında yanıt  
3. **Bilinmeyen/riskli soru** – Maaş/hukuk; insan müdahalesi tetiklenir  

## Proje Yapısı

```
├── main.py                 # FastAPI uygulaması
├── agent_loop.py           # Agent döngüsü (orkestrasyon)
├── config.py               # Ayarlar
├── requirements.txt
├── data/
│   └── profile.json        # CV/profil (statik)
├── prompts/
│   └── career_agent_prompts.py
├── agents/
│   ├── career_agent.py     # Birincil agent
│   └── evaluator_agent.py  # Critic/Judge
├── tools/
│   ├── notification_tool.py
│   └── unknown_question_tool.py
├── tests/
│   ├── test_cases.py       # 3 test senaryosu
│   └── run_test_cases.py
└── docs/
    ├── ARCHITECTURE.md     # Mimari ve akış diyagramı
    └── REPORT.md           # Kısa rapor (3–5 sayfa)
```

## Mimari / Akış

Akış diyagramı ve tool çağrı mekanizması için `docs/ARCHITECTURE.md` dosyasına bakın.

## Lisans

Eğitim projesi – ders kapsamında kullanım.
"# Career-Assistant-AI" 
