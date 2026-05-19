# WiseBuy AI — Backend

Elektronik, giyim, spor ekipmanı ve her türlü ürün alırken sekmeler arasında kaybolan kullanıcılar için yapay zeka destekli alışveriş asistanı.

## Özellikler

- Trendyol & Hepsiburada'dan gerçek zamanlı yorum ve fiyat çekme
- YouTube & TikTok video transkript analizi
- Google Gemini Pro ile kişiselleştirilmiş ürün analizi
- Satıcı güven skoru & ürün memnuniyet skoru
- Alternatif ürün önerisi
- Ürün bazlı follow-up chatbot

## Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/kullanicin/wisebuy-ai.git
cd wisebuy-ai

# 2. Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. .env dosyasını oluştur
cp .env.example .env
# .env dosyasını aç ve GEMINI_API_KEY'i gir

# 5. Çalıştır
uvicorn app.main:app --reload
```

## API Dökümantasyonu

Uygulama ayağa kalktıktan sonra:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Temel Endpoint'ler

### POST /api/v1/products/analyze
Ürün analizi başlatır.

```json
{
  "product_name": "MacBook Air M2",
  "user_purpose": "Yazılım stajyeriyim, Flutter geliştireceğim",
  "budget": 40000
}
```

### POST /api/v1/products/chat
Analiz sonrası soru sorma.

```json
{
  "analysis_id": 1,
  "message": "Bu laptopla Blender kullanabilir miyim?"
}
```

### GET /api/v1/products/history
Son aramaları listeler.

## Mimari

```
app/
├── api/v1/endpoints/   # HTTP katmanı — sadece request/response
├── services/           # İş mantığı
│   ├── scrapers/       # Trendyol, Hepsiburada, YouTube, TikTok
│   └── ai/             # Gemini API entegrasyonu
├── repositories/       # Veritabanı işlemleri
├── models/             # SQLAlchemy ORM modelleri
├── schemas/            # Pydantic request/response şemaları
├── core/               # Config, exceptions
└── db/                 # Database bağlantısı
```

## Gemini API Key Alma

1. https://aistudio.google.com adresine git
2. "Get API Key" butonuna tıkla
3. Oluşturulan key'i .env dosyasına yapıştır
