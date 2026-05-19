import asyncio
from loguru import logger

from app.services.scrapers.google_shopping import GoogleShoppingScraper
from app.services.scrapers.sikayetvar import SikayetvarScraper
from app.services.scrapers.video_scraper import VideoScraperService
from app.services.ai.gemini_service import GeminiAIService
from app.schemas.schemas import (
    AnalyzeProductResponse,
    ReviewItem,
    VideoSummary,
    PriceEntry,
    AlternativeProduct,
    ComplaintCategory,
)
from app.repositories.analysis_repository import AnalysisRepository
from app.core.exceptions import ScrapingException

class ProductAnalysisService:
    def __init__(self, repository: AnalysisRepository):
        self.repository = repository
        self.shopping_scraper = GoogleShoppingScraper()
        self.sikayetvar_scraper = SikayetvarScraper()
        self.video_service = VideoScraperService()
        self.ai_service = GeminiAIService()

    async def analyze(self, product_name: str, user_purpose: str, budget: float | None) -> AnalyzeProductResponse:
        # Intent Extraction - kullanıcının metninden arama kelimesini ve bütçeyi çıkar
        intent = await self.ai_service.extract_intent(product_name)
        search_keyword = intent.get("search_keyword", product_name)
        budget = intent.get("detected_budget") or budget

        search = await self.repository.create_search(search_keyword, user_purpose, budget)
        logger.info(f"[Service] Search #{search.id} created for: {search_keyword}")

        # 1. Fiyatları Google Shopping'den, Videoları YouTube ve TikTok'tan eşzamanlı çek
        tasks = [
            self._safe_scrape_prices(self.shopping_scraper, search_keyword),
            self.video_service.get_youtube_summaries(search_keyword),
            self.video_service.get_tiktok_summaries(search_keyword),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = results[0] if isinstance(results[0], list) else []
        youtube_data = results[1] if isinstance(results[1], list) else []
        tiktok_data = results[2] if isinstance(results[2], list) else []

        all_video_data = youtube_data + tiktok_data
        
        # 1.5. Google Shopping'den gelen fiyatlardan en iyi 5 eşsiz satıcıyı seç
        # Yalnızca ilk 10 fiyata bak (bot veya alakasız sonuçları elemek için)
        sorted_prices = sorted(prices, key=lambda x: x.price)[:10]
        unique_sellers = []
        for p in sorted_prices:
            if p.seller_name not in unique_sellers:
                unique_sellers.append(p.seller_name)
            if len(unique_sellers) >= 5:
                break
                
        sikayetvar_tasks = [
            self.sikayetvar_scraper.get_seller_complaints(seller) for seller in unique_sellers
        ]
        # Ürün için de genel şikayetleri (kronik sorunları) çekelim
        sikayetvar_tasks.append(self.sikayetvar_scraper.get_seller_complaints(search_keyword))
        
        complaints_results = await asyncio.gather(*sikayetvar_tasks, return_exceptions=True)
        
        seller_complaints = {}
        product_complaints = []
        
        # Sonuçların sonuncusu ürün şikayetleridir
        if isinstance(complaints_results[-1], list):
            product_complaints = complaints_results[-1]
            
        for seller, complaints in zip(unique_sellers, complaints_results[:-1]):
            if isinstance(complaints, list) and complaints:
                seller_complaints[seller] = complaints

        # 2. Gemini'a gönder
        ai_result = await self.ai_service.analyze_product(
            product_name=search_keyword,
            user_purpose=user_purpose,
            budget=budget,
            prices=prices,
            video_data=all_video_data,
            seller_complaints=seller_complaints,
            product_complaints=product_complaints,
        )

        # 3. Videolar için madde madde özetleri oluştur
        video_summaries = await self._build_video_summaries(search_keyword, all_video_data)

        # 4. DB'ye kaydet
        analysis = await self.repository.create_analysis(
            search_id=search.id,
            ai_result=ai_result,
            reviews=[],
            prices=[p.__dict__ for p in prices],
            video_summaries=[v.dict() for v in video_summaries],
        )

        alternatives = [AlternativeProduct(**alt) for alt in ai_result.get("alternatives", [])]
        complaint_categories = [
            ComplaintCategory(**cat) 
            for cat in ai_result.get("complaint_categories", [])
            if isinstance(cat, dict) and 'label' in cat and 'percentage' in cat
        ]

        # 5. Dönüş modeli oluştur
        return AnalyzeProductResponse(
            analysis_id=analysis.id,
            product_name=product_name,
            purpose_fit_score=ai_result.get("purpose_fit_score"),
            value_for_money_score=ai_result.get("value_for_money_score"),
            overall_sentiment_score=ai_result.get("overall_sentiment_score"),
            ai_report=ai_result.get("ai_report", ""),
            prices=self._map_prices(prices),
            top_reviews=[],
            video_summaries=video_summaries,
            alternatives=alternatives,
            top_pros=ai_result.get("top_pros", []),
            top_cons=ai_result.get("top_cons", []),
            complaint_categories=complaint_categories,
            created_at=analysis.created_at,
        )

    async def _safe_scrape_prices(self, scraper, product_name: str) -> list:
        try:
            return await scraper.get_prices(product_name)
        except ScrapingException as e:
            logger.warning(f"[Service] Price scraping failed: {e.reason}")
            return []

    async def _build_video_summaries(self, product_name: str, video_data: list[dict]) -> list[VideoSummary]:
        """T\u00fcm videolar\u0131 TEK Gemini \u00e7a\u011fr\u0131s\u0131yla analiz et \u2014 API kota tasarrufu."""
        if not video_data:
            return []

        # Tek \u00e7a\u011fr\u0131da t\u00fcm videolar\u0131 analiz et
        batch_results = await self.ai_service.batch_video_analysis(product_name, video_data)

        summaries = []
        for i, video in enumerate(video_data):
            key_points = batch_results.get(str(i), [])
            if not key_points:
                continue  # Sonucu olmayan videoyu atla

            title = (video.get("description") or
                     video.get("title") or
                     video.get("url", "").split("v=")[-1][:30] or
                     video.get("video_id", "Video"))

            summaries.append(
                VideoSummary(
                    platform=video.get("platform", "video"),
                    video_title=title[:100],
                    video_url=video.get("url", ""),
                    key_points=key_points,
                )
            )
        return summaries

    def _map_prices(self, prices: list) -> list[PriceEntry]:
        return [
            PriceEntry(
                source=p.source,
                price=p.price,
                currency=p.currency,
                seller_name=p.seller_name,
                seller_rating=p.seller_rating,
                url=p.url,
            )
            for p in prices
        ]
