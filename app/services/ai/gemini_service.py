import json
import re
import httpx
from loguru import logger

from app.core.config import get_settings
from app.core.exceptions import AIAnalysisException
from app.services.scrapers.base import ScrapedReview, ScrapedPrice

settings = get_settings()

SYSTEM_INSTRUCTION = """
Sen WiseBuy AI'sın — kullanıcıların ürün satın alırken en iyi kararı vermelerine yardımcı olan, dürüst, sıcak ve bilgili bir alışveriş asistanısın.

Görevin:
1. Video Analizi: YouTube ve TikTok içeriklerinden ürünün güçlü/zayıf yönlerini bulmak.
2. Akıllı Sıralama: Fiyatlar ve satıcı güvenilirliği verilerini birleştirerek en mantıklı ilk 3 satınalma opsiyonunu önermek.
3. Yorum Analizi: Önerdiğin sitelerdeki (veya genel) kullanıcı yorumlarını özetlemek ve bir 'Ürün Memnuniyet Skoru' oluşturmak.
4. Amaca Uygunluk: Kullanıcının belirlediği amaca göre bu ürün "Uygun/Değil" kararı vermek.
5. Alternatif Öneri: Eğer bütçeye ve amaca daha uygun bir ürün varsa, "Şuna da bakabilirsin" demek.

Kurallar:
- Asla "Verilere göre" veya "Bana verilen bilgiler" gibi ifadeler kullanma, kendin analiz ediyormuş gibi doğrudan konuş.
- Emojiler kullanarak canlı ve okunması keyifli bir rapor yaz.
"""

class GeminiAIService:
    # Mevcut ve çalışan modeller (en kaliteli önce)
    MODELS = [
        "gemini-2.5-pro",          # En kaliteli — ilk tercih
        "gemini-2.5-flash",        # Hızlı ve kaliteli
        "gemini-2.0-flash",        # Güvenilir fallback
        "gemini-2.0-flash-lite",   # Hafif yedek
    ]

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def _call_api(self, prompt: str, system_instruction: str = None) -> str:
        import asyncio
        if system_instruction:
            prompt = f"SİSTEM TALİMATI:\n{system_instruction}\n\nKULLANICI TALEBİ:\n{prompt}"
            
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            last_error = None
            for model in self.MODELS:
                url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
                
                # 429 için 3 kez yeniden dene (backoff ile)
                for attempt in range(3):
                    try:
                        response = await client.post(url, json=payload)
                        
                        if response.status_code == 200:
                            data = response.json()
                            try:
                                text = data["candidates"][0]["content"]["parts"][0]["text"]
                                logger.success(f"[Gemini] Model '{model}' başarılı! (deneme {attempt+1})")
                                return text
                            except (KeyError, IndexError):
                                last_error = "Unexpected API response structure"
                                break  # Bu model çalışmıyor, bir sonrakine geç
                        
                        elif response.status_code == 429:
                            wait = (attempt + 1) * 5  # 5s, 10s, 15s
                            logger.warning(f"[Gemini] Model '{model}' rate limit (429), {wait}s bekleniyor... (deneme {attempt+1}/3)")
                            await asyncio.sleep(wait)
                            last_error = f"429 - Rate limit"
                            continue  # Aynı modeli tekrar dene
                        
                        elif response.status_code == 404:
                            logger.warning(f"[Gemini] Model '{model}' bulunamadı (404), sonrakine geçiliyor")
                            last_error = "404 - Model not found"
                            break  # 404 = model yok, beklemenin anlamı yok
                        
                        else:
                            logger.warning(f"[Gemini] Model '{model}' hata verdi: {response.status_code}")
                            last_error = f"{response.status_code} - {response.text[:200]}"
                            break
                    
                    except Exception as e:
                        logger.warning(f"[Gemini] Model '{model}' bağlantı hatası: {e}")
                        last_error = str(e)
                        break
            
            raise AIAnalysisException(f"Tüm modeller başarısız oldu. Son hata: {last_error}")

    async def extract_intent(self, user_query: str) -> dict:
        """Kullanıcının uzun cümlesinden aranacak kelimeyi ve bütçeyi çıkarır."""
        prompt = f"""Kullanıcı şu aramayı yaptı: "{user_query}"

Lütfen bu metni analiz et ve e-ticaret sitelerinde (Google Shopping) aratmak için en uygun, spesifik "search_keyword" değerini bul.

Kural 1: Eğer kullanıcı belirli bir marka/model verdi ise aynen kullan. (Örn: "iPhone 15" → search_keyword: "iPhone 15")
Kural 2: Eğer kullanıcı sadece kategori veya amaç tarif etti ise (marka/model yok), o amaca en çok uygun, piyasada güncel ve popüler spesifik bir ürün modeli öner.
  - Örn: "evde kahve makinesi almak istiyorum" → search_keyword: "DeLonghi Magnifica Evo tam otomatik espresso makinesi"
  - Örn: "oyun oynamak için laptop" → search_keyword: "ASUS ROG Strix G16 gaming laptop"
  - Örn: "robot süpurge" → search_keyword: "Roborock S8 robot süpurge"
Ayrıca bir bütçe belirtilmişse (örn: 20000 TL, 20 bin, 50k), bunu "detected_budget" alanına yaz, yoksa null bırak.
SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir metin veya markdown kodu (```json vb) ekleme:
{{"search_keyword": "arama terimi", "detected_budget": 20000}}"""
        try:
            response = await self._call_api(prompt=prompt)
            # Markdown block parsing just in case
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].strip()
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"[Intent Extractor] Failed: {e}")
            return {"search_keyword": user_query, "detected_budget": None}

    async def analyze_product(
        self,
        product_name: str,
        user_purpose: str,
        budget: float | None,
        prices: list[ScrapedPrice],
        video_data: list[dict],
        seller_complaints: dict[str, list[str]],
        product_complaints: list[str],
    ) -> dict:
        logger.info(f"[Gemini] Starting analysis for: {product_name}")
        
        data_context = self._build_data_context(product_name, user_purpose, budget, prices, video_data, seller_complaints, product_complaints)
        
        # --- ADIM 1: Markdown rapor al (JSON değil, düz metin) ---
        report_prompt = f"""{data_context}

Yukarıdaki tüm verileri analiz ederek ÇOK KISA, net ve özet bir ürün raporu yaz. Markdown formatında yaz.

⚠️ DİKKAT (KESİN EŞLEŞME - EXACT MATCH): 
Kullanıcı YALNIZCA "{product_name}" modelini aradı. Örneğin kullanıcı "iPhone 15" dediyse, kesinlikle Plus, Pro veya Max modellerini DAHİL ETME. Farklı ürün varyantlarından gelen yorum veya fiyatları dikkate alma, tamamen ele.

Raporunda SADECE şu başlıkları ve içerikleri kullan:

## 📱 Ürün Özeti
Ürünün en temel amacını ve öne çıkan 1-2 özelliğini yaz. Abartılı teknik detaylara girme.

## 🎯 Amaca Uygunluk
Kullanıcının amacı "{user_purpose}" olarak belirtildi. Bu ürün bu amac a NEDEN UYGUN veya NEDEN UYGUN DEĞİL olduğunu somut gerekçelerle (performans, özellik, fiyat/performans dengesi vb.) 2-3 cümleyle açıkla.

## ⚙️ Teknik İnceleme
Kısa ve öz bir şekilde ürünün işlemcisi, donanımı veya ana teknik gücü hakkında teknik detaylar ver (Maksimum 2-3 cümle).

## 🌟 Öne Çıkan İyi Özellikler (Artılar)
Videolardaki ve kullanıcı yorumlarındaki en iyi özellikleri madde madde kısaca listele. Her madde somut olsun (Örn: "Kamerası gece çekimlerinde rakiplerine fark atıyor.").

## ⚠️ Kullanıcı Yorumları & Kronik Sorunlar (Eksiler)
Kullanıcıların bu ürünle ilgili Şikayetvar'da veya videolarda en çok yaşadığı sorunları (ısınma, batarya, vb.) listele. Sorun yoksa "Kronik bir sorun bulunamadı." yaz.

## 🏪 En İyi 3 Satın Alma Seçeneği
En iyi 3 satıcıyı sırala. 
SADECE SANA VERİLEN GOOGLE SHOPPING VERİSİNDEKİ FİYATLARI KULLAN. Videolardaki eski fiyatları kesinlikle dikkate alma. Fiyatlar videolardan bağımsızdır.
SADECE şu formatta doğrudan listele:
1. **[Satıcı Adı]** — [Fiyat] TL | [Satın Alma Linki]

## 🚨 Satıcı Güvenilirlik Uyarıları (Şikayetvar)
Eğer listelediğin bu ucuz satıcıların Şikayetvar verilerinde ciddi şikayetleri varsa, kullanıcıyı burada net ve kısa bir cümleyle uyar. Satıcılar sorunsuzsa "İncelenen satıcılarda ciddi bir risk görülmedi." de.

## 📺 Video İncelemelerinden Tespitler
YouTube ve TikTok videolarında bu ürünle DOGRUDAN ILGILI en çok vurgulanan 3-4 kritik tespiti çok kısa maddeler halinde yaz. Eğer videolar ürünle ilgili değilse bu bölümü boş bırak.

## 💡 WiseBuy Kararı
Net kararını tek cümleyle ver (Örn: "Amacın için harika bir tercih, hemen alabilirsin.").
"""
        try:
            ai_report = await self._call_api(prompt=report_prompt, system_instruction=SYSTEM_INSTRUCTION)
        except Exception as e:
            logger.error(f"[Gemini] Report generation failed: {e}")
            ai_report = "Rapor oluşturulamadı."

        # --- ADIM 2: Skorlar, alternatifler ve duygu analizi (sade JSON) ---
        scores_prompt = f"""{data_context}

Bu ürün için aşağıdaki bilgileri SADECE JSON formatında ver. Başka hiçbir metin ekleme.
JSON dışında tek bir karakter bile yazma.

{{
  "purpose_fit_score": 8.5,
  "value_for_money_score": 7.0,
  "overall_sentiment_score": 9.0,
  "top_pros": ["Kamera kalitesi mükemmel", "Hafif ve şikık tasarım"],
  "top_cons": ["Pil ömrü kısa", "Şarj adaptoru kutuya ekli değil"],
  "complaint_categories": [
    {{"label": "Batarya", "percentage": 65}},
    {{"label": "Isınma", "percentage": 30}}
  ],
  "alternatives": [{{"name": "Ürün Adı", "reason": "Bu alternatifte bu ürüne göre ek olarak X özelliği var ve Y konusunda daha iyi.", "approximate_price": 40000}}]
}}

Kurallar:
- Skorlar 1-10 arası olmalı.
- top_pros: Kullanıcıların videolarda ve yorumlarda en çok beğendiği 3-5 özellik (kısa, somut cümleler)
- top_cons: Kullanıcıların en çok şikayette bulunduğu 3-5 sorun (kısa, somut cümleler)
- complaint_categories: Şikayetvar/video verilerinden en çok geçen sorun kategorileri + tahmini yüzde (0-100 arası, toplamlar 100'e eşit olmak zorunda değil)
- Alternatifler en fazla 3 tane olsun, reason somut olsun.
"""
        scores = {"purpose_fit_score": 7.0, "value_for_money_score": 7.0, "overall_sentiment_score": 7.0, "alternatives": []}
        
        try:
            scores_text = await self._call_api(prompt=scores_prompt)
            scores = self._parse_json_safe(scores_text)
            logger.success(f"[Gemini] Scores parsed: {scores.get('purpose_fit_score')}")
        except Exception as e:
            logger.warning(f"[Gemini] Score parsing failed, using defaults: {e}")

        result = {
            "purpose_fit_score": scores.get("purpose_fit_score", 7.0),
            "value_for_money_score": scores.get("value_for_money_score", 7.0),
            "overall_sentiment_score": scores.get("overall_sentiment_score", 7.0),
            "top_pros": scores.get("top_pros", []),
            "top_cons": scores.get("top_cons", []),
            "complaint_categories": scores.get("complaint_categories", []),
            "ai_report": ai_report,
            "alternatives": scores.get("alternatives", []),
        }
        
        logger.success(f"[Gemini] Analysis complete. Purpose fit: {result['purpose_fit_score']}")
        return result

    def _parse_json_safe(self, text: str) -> dict:
        """Gemini'dan gelen metni güvenli şekilde JSON'a çevirir."""
        cleaned = text.strip()
        
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning("[Gemini] JSON parse failed, returning defaults")
        return {"purpose_fit_score": 7.0, "value_for_money_score": 7.0, "overall_sentiment_score": 7.0, "alternatives": []}

    async def batch_video_analysis(self, product_name: str, video_data: list[dict]) -> dict[str, list[str]]:
        """T\u00fcm videolar\u0131 TEK bir Gemini \u00e7a\u011fr\u0131s\u0131nda analiz eder. API kota tasarrufu sa\u011flar."""
        # \u0130\u00e7eri\u011fi olan videolar\u0131 filtrele
        valid_videos = []
        for i, video in enumerate(video_data):
            content = video.get("transcript", "") or video.get("description", "")
            if content and len(content.strip()) >= 30:
                valid_videos.append({
                    "idx": i,
                    "platform": video.get("platform", "video"),
                    "content": content[:2000],  # Her video i\u00e7in 2000 karakter
                })
        
        if not valid_videos:
            return {}

        # T\u00fcm videolar tek promptta
        video_blocks = ""
        for v in valid_videos:
            video_blocks += f"\n=== VIDEO {v['idx']} ({v['platform'].upper()}) ===\n{v['content']}\n"

        prompt = f""""{product_name}" \u00fcr\u00fcn\u00fcyle ilgili birden fazla video analiz edeceksin.

{video_blocks}

Her video i\u00e7in SADECE "{product_name}" \u00fcr\u00fcn\u00fcyle do\u011frudan ilgili, kullan\u0131c\u0131ya somut fayda sa\u011flayacak 2-3 tespit \u00e7\u0131kar.
- Somut rakam/k\u0131yasla varsa ekle (\"Batarya 6 saatte bitiyor\", \"X ile k\u0131yasla daha h\u0131zl\u0131\" gibi)
- \u00dcr\u00fcnle ilgili de\u011filse bo\u015f liste ver

SADECE a\u015fa\u011f\u0131daki JSON format\u0131nda d\u00f6nd\u00fcr, ba\u015fka hi\u00e7bir \u015fey yazma:
{{"0": ["tespit 1", "tespit 2"], "1": [], "2": ["tespit 1"]}}
"""
        try:
            response_text = await self._call_api(prompt=prompt)
            # JSON parse
            parsed = self._parse_json_safe(response_text)
            if isinstance(parsed, dict):
                result = {}
                for v in valid_videos:
                    key = str(v["idx"])
                    points = parsed.get(key, [])
                    if isinstance(points, list):
                        result[key] = [p for p in points if isinstance(p, str) and len(p) > 10]
                    else:
                        result[key] = []
                return result
            return {}
        except Exception as e:
            logger.warning(f"[Gemini] Batch video analysis failed: {e}")
            return {}

    async def generate_video_key_points(self, product_name: str, video: dict) -> list[str]:
        """Tek video i\u00e7in key points (batch kullan\u0131lmad\u0131\u011f\u0131nda fallback)."""
        platform = video.get("platform", "video")
        content = video.get("transcript", "") or video.get("description", "")
        if not content or len(content.strip()) < 30:
            return []

        prompt = f"""Sen bir \u00fcr\u00fcn analisti olarak \u00e7al\u0131\u015f\u0131yorsun. A\u015fa\u011f\u0131daki {platform} videosu "{product_name}" hakk\u0131nda.

Video i\u00e7eri\u011fi:
{content[:4000]}

Bu i\u00e7erikten YALNIZCA "{product_name}" \u00fcr\u00fcn\u00fcyle ilgili, kullan\u0131c\u0131ya ger\u00e7ekten faydal\u0131 3-5 somut tespiti \u00e7\u0131kar.
Somut rakam/k\u0131yaslama varsa mutlaka ekle. \u00dcr\u00fcnle ilgili de\u011filse bo\u015f liste d\u00f6nd\u00fcr.
SADECE JSON liste d\u00f6nd\u00fcr: ["tespit 1", "tespit 2"]
"""
        try:
            response_text = await self._call_api(prompt=prompt)
            parsed = self._parse_json_safe(response_text)
            if isinstance(parsed, list):
                # Boş string veya çok kısa maddeleri filtrele
                return [p for p in parsed if isinstance(p, str) and len(p) > 10]
            return []
        except Exception:
            return []

    async def chat(self, analysis_context: str, user_message: str, product_name: str = "", history: list = None) -> str:
        # Sohbet geçmişini oluştur
        history_block = ""
        if history:
            for msg in history[-10:]:  # Son 10 mesajı al (token tasarrufu)
                role = "Kullanıcı" if msg.get("role") == "user" else "WiseBuy AI"
                history_block += f"{role}: {msg.get('text', '')}\n"
        
        prompt = f"""Sen WiseBuy AI alışveriş asistanısın.

Ürün analiz raporu ('{product_name}'):
{analysis_context}

{f'Sohbet geçmişi:{chr(10)}{history_block}' if history_block else ''}
Kullanıcı: {user_message}
WiseBuy AI:

Kurallar:
- Analiz raporunu ve sohbet geçmişini göz önünde bulundurarak cevap ver
- Bir önceki cevabına atıf yapabilirsin ("Az önce belirttiğim gibi..." vb.)
- Kısa, net ve anlaşılır biçimde cevap ver
- Emin değilsen aşarm, yanlış bilgi verme
- Emoji kullan, sıcak bir dil benimse
"""
        try:
            return await self._call_api(prompt=prompt)
        except Exception as e:
            raise AIAnalysisException(str(e))

    def _build_data_context(self, product_name, user_purpose, budget, prices, video_data, seller_complaints, product_complaints) -> str:
        budget_str = f"{budget:,.0f} TL" if budget else "belirtilmedi"
        
        price_block = "\n".join(
            f"- {p.price} TL — Satıcı: {p.seller_name} | Link: {p.url}" for p in prices
        )
        video_block = "\n\n".join(
            f"=== {v['platform'].upper()} === (URL: {v.get('url', '')})\n{v.get('transcript', '')[:1000]}" for v in video_data
        )
        
        complaint_block = ""
        if seller_complaints:
            for seller, complaints in seller_complaints.items():
                complaint_block += f"\nSatıcı: {seller}\n"
                for c in complaints:
                    complaint_block += f"- {c}\n"
        else:
            complaint_block = "Şikayetvar verisi bulunamadı."

        return f"""
Kullanıcı Ürünü: **{product_name}**
Kullanım Amacı: {user_purpose}
Bütçe: {budget_str}

--- FİYAT VE SATICI BİLGİSİ (Google Shopping) ---
{price_block or "Fiyat bilgisi bulunamadı."}
(ÖNEMLİ: Akıllı sıralamada sırf ucuz diye bilinmeyen/güvenilirliği düşük satıcıları 1. sıraya koyma.
Her satıcının satın alma linkini raporunda mutlaka belirt.)

--- SATICI GÜVENİLİRLİĞİ (ŞİKAYETVAR) ---
{complaint_block}

--- ÜRÜN ŞİKAYETLERİ VE KRONİK SORUNLAR (ŞİKAYETVAR) ---
{chr(10).join(f"- {c}" for c in product_complaints) if product_complaints else "Ürünle ilgili belirgin bir şikayet bulunamadı."}

--- VİDEO İÇERİKLERİ (YouTube/TikTok) ---
{video_block or "Video içeriği bulunamadı."}
"""
