# 🛒 WiseBuy AI — Akıllı Alışveriş Asistanı

> **"Yanlış ürün almak için zaman ve para harcamayın."**  
> WiseBuy AI, yapay zeka destekli analiz sistemiyle doğru ürünü, doğru fiyata, doğru satıcıdan almanıza yardımcı olur.

---

## 🚀 Nedir?

WiseBuy AI, kullanıcıların herhangi bir ürün veya kategori hakkında doğal dilde arama yapmasına ve saniyeler içinde derinlemesine bir alışveriş analizi almasına olanak tanıyan bir web uygulamasıdır.

**Örnek:** _"Evde kahve yapmak için 20.000 TL bütçeyle kahve makinesi almak istiyorum"_ yazdığınızda sistem otomatik olarak:
- Piyasadaki en uygun modeli tespit eder
- Güncel fiyatları karşılaştırır
- YouTube ve TikTok inceleme videolarını analiz eder
- Şikayetvar'dan satıcı ve ürün şikayetlerini tarar
- Kullanıcı memnuniyetini skorlar
- Bütçenize göre alternatifler önerir

---

## ✨ Özellikler

| Özellik | Açıklama |
|---|---|
| 🧠 **Doğal Dil Anlama** | "Oyun için laptop" gibi kategori aramalarında AI en iyi modeli önerir |
| 💰 **Gerçek Zamanlı Fiyat Karşılaştırma** | Google Shopping'den canlı fiyat ve satıcı verisi |
| 📺 **Video Analizi** | YouTube & TikTok inceleme videolarından somut tespitler |
| ⚠️ **Güvenilirlik Denetimi** | Şikayetvar entegrasyonu ile satıcı ve ürün şikayetleri |
| 📊 **Kullanıcı Memnuniyeti Skoru** | Genel memnuniyet, amaca uygunluk ve fiyat/performans metrikleri |
| 🤖 **AI Sohbet Asistanı** | Analiz sonrası bağlama duyarlı soru-cevap (sohbet geçmişi korunur) |
| 🔄 **Alternatif Öneriler** | Bütçeye ve amaca daha uygun ürünler otomatik olarak önerilir |

---

## 🛠️ Kullanılan Teknolojiler

### Backend
| Teknoloji | Kullanım |
|---|---|
| **Python 3.11+** | Ana programlama dili |
| **FastAPI** | REST API framework |
| **SQLite + SQLAlchemy** | Analiz geçmişi veritabanı |
| **Google Gemini API** | Doğal dil anlama, rapor üretme, duygu analizi |
| **httpx + BeautifulSoup** | Google Shopping & Şikayetvar veri çekme |
| **youtube-transcript-api** | YouTube video transkript analizi |
| **Loguru** | Gelişmiş loglama |

### Frontend
| Teknoloji | Kullanım |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build aracı |
| **Vanilla CSS** | Özel tasarım sistemi |
| **Lucide React** | İkon seti |
| **localStorage** | Oturum bazlı sohbet geçmişi saklama |

---

## 📁 Proje Yapısı

```
wisebuy-ai/
├── app/
│   ├── api/v1/router.py          # API endpoint'leri
│   ├── services/
│   │   ├── ai/gemini_service.py  # Gemini AI entegrasyonu
│   │   ├── scrapers/             # Google Shopping, YouTube, Şikayetvar
│   │   └── product_analysis_service.py
│   ├── schemas/schemas.py        # Pydantic modelleri
│   └── db/                       # Veritabanı
├── frontend/
│   └── src/
│       ├── App.jsx               # Ana React bileşeni
│       └── App.css               # Tasarım sistemi
├── main.py                       # Uygulama giriş noktası
└── requirements.txt
```

---

## ⚙️ Kurulum

### 1. Gereksinimler

```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenleri

`.env.example` dosyasını kopyalayın:

```bash
cp .env.example .env
```

`.env` içine Gemini API anahtarınızı ekleyin:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

> API anahtarı almak için: [aistudio.google.com](https://aistudio.google.com)

### 3. Backend'i Başlatın

```bash
py -m uvicorn main:app --reload
```

### 4. Frontend'i Başlatın

```bash
cd frontend
npm install
npm run dev
```

Uygulama `http://localhost:5173` adresinde çalışmaya başlar.

---

## 🔑 Gemini API Kullanımı

Uygulama her analiz için yaklaşık **4 Gemini API isteği** kullanır (video analizi dahil batch optimizasyonu yapılmıştır). Ücretsiz plan ile kullanılabilir.

Model öncelik sırası (otomatik fallback):
1. `gemini-2.5-pro` → En kaliteli
2. `gemini-2.5-flash` → Hızlı ve dengeli
3. `gemini-2.0-flash` → Güvenilir yedek
4. `gemini-2.0-flash-lite` → Son çare

---

## 📄 Lisans

MIT License
