# Career Assistant AI Agent – Kısa Rapor (3–5 Sayfa)

## 1. Tasarım Kararları

**Birincil agent (Career Agent):** İşveren mesajını ve statik profil (CV) bilgisini kullanarak tek bir LLM çağrısıyla yanıt üretiyor. Revizyon turunda evaluator’dan gelen feedback doğrudan prompt’a ekleniyor; ayrı bir “plan-and-execute” agent kullanılmadı. Sebep: görev tek adımlı (yanıt üret) ve revizyon kuralı net; ek karmaşıklık getirmeden hızlı sonuç alındı.

**Response Evaluator:** LLM-as-Judge yaklaşımı seçildi. Kural tabanlı skorlama (kelime sayısı, ton sözlüğü) daha deterministik olurdu ancak anlamsal kalite (güvenlik, uygunluk) için LLM değerlendirmesi daha uygun görüldü. Beş kriter (professional_tone, clarity, completeness, safety, relevance) ve toplam skor ile onay/red kararı veriliyor; eşik (varsayılan 70) konfigüre edilebilir.

**Bildirim aracı:** Telegram Bot API ile mobil bildirim implemente edildi. Kurulumu kolay ve ücretsiz; FCM veya e-posta alternatifleri dokümante edildi. Token/chat_id yoksa sadece log’a yazılıyor, demo için çalışır durumda.

**Bilinmeyen soru tespiti:** Ayrı bir LLM çağrısı ile mesaj sınıflandırılıyor (maaş, hukuki, teknik, belirsiz). Güven skoru eşiği (0.6) ile “emin değilim” durumları da insan müdahalesine yönlendiriliyor. Tetikleyiciler: maaş pazarlığı, hukuki sorular, profil dışı derin teknik sorular, belirsiz iş teklifi.

**Agent döngüsü:** LangChain Agent kullanılmadı; tool invocation doğrudan Python fonksiyon çağrıları ile yapıldı. Akış sabit: bildirim → bilinmeyen kontrol → yanıt üret → değerlendir → onaylıysa gönder, değilse revize (en fazla N deneme). Bu sayede davranış öngörülebilir ve debug kolay.

---

## 2. Değerlendirme Stratejisi

Evaluator, üretilen yanıtı beş boyutta 0–100 puanlıyor ve toplam skor hesaplıyor. Toplam skor ≥ eşik (varsayılan 70) ise yanıt onaylanıyor; aksi halde feedback metni Career Agent’a iletilip revizyon yapılıyor. En fazla 3 revizyon denemesi sonrası son yanıt yine de döndürülüyor ancak `max_revisions_reached` ile log’lanıyor.

Değerlendirme kriterleri:
- **professional_tone:** Profesyonel ve nazik dil
- **clarity:** Anlaşılırlık
- **completeness:** Soruya yeterince cevap
- **safety:** Halüsinasyon yok, yanlış iddia yok, profil ile uyum
- **relevance:** İşveren mesajına doğrudan cevap

Tüm evaluator çıktıları (attempt, scores, feedback, approved) API yanıtında `evaluation_log` olarak dönüyor; raporlama ve iyileştirme için kullanılabilir.

---

## 3. Başarısızlık Durumları ve Edge Case’ler

- **Gemini API hatası:** Career Agent hata verirse kullanıcıya genel bir “kısa süre içinde döneceğim” mesajı döndürülüyor. Evaluator hata verirse varsayılan skor 70 ve approved=true kabul ediliyor.
- **Evaluator JSON parse hatası:** Çıktı bazen markdown veya ek metin içerebiliyor; regex ile JSON blok çıkarılıyor. Parse yine başarısızsa kural tabanlı fallback (70 puan, onaylı) uygulanıyor.
- **Bilinmeyen soru sınıflandırıcı hatası:** Parse veya API hatası durumunda `is_unknown_or_unsafe=true` ve bildirim gönderiliyor; yanlış pozitif tercih edildi (güvenli tarafta kalmak).
- **Maksimum revizyon aşımı:** Eşik altında kalan yanıt 3 denemeden sonra yine de gönderiliyor; `max_revisions_reached` ve tüm evaluation_log raporlanıyor. İleride bu durumda da insan müdahalesi tetiklenebilir.
- **Profil dosyası eksik/bozuk:** Profil yüklenemezse fallback kısa bir metin kullanılıyor; agent çalışmaya devam ediyor.

---

## 4. Yansıma

**Güçlü yönler:** Akış net ve test edilebilir; üç senaryo (davet, teknik soru, bilinmeyen/riskli soru) ile davranış doğrulandı. Evaluator sayesinde ton ve güvenlik kontrol altında; bilinmeyen soru tespiti maaş/hukuk gibi hassas konularda insanı devreye sokuyor. Telegram bildirimi demo için yeterli.

**İyileştirme alanları:** Profil şu an statik JSON; RAG ile CV/deneyim dokümanları eklenebilir. Evaluator’da bazen JSON formatı bozulabiliyor; daha sıkı çıktı formatı (örn. structured output API) kullanılabilir. Bellek (konuşma geçmişi) ve güven skoru görselleştirmesi bonus kapsamında eklenebilir. Son olarak, “yanıt gönderildi” bildirimi gerçek e-posta/SMTP ile de entegre edilebilir.

**Özet:** Ödev gereksinimleri (Career Agent, Evaluator, Notification, Unknown Question, mimari diyagram, 3 test senaryosu, kısa rapor) karşılandı. Sistem canlı demoda çalıştırılabilir ve GitHub’a konulacak kaynak kodu ile teslim edilebilir.
