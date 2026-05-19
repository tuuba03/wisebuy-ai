import httpx
from loguru import logger
from urllib.parse import urlencode

from app.core.config import get_settings
from app.services.scrapers.base import BaseScraper, ScrapedPrice

settings = get_settings()

class GoogleShoppingScraper(BaseScraper):
    SOURCE_NAME = "google_shopping"

    async def get_prices(self, product_name: str) -> list[ScrapedPrice]:
        logger.info(f"[GoogleShopping] Fetching prices for: {product_name}")
        prices: list[ScrapedPrice] = []

        if not settings.serpapi_key:
            logger.warning("[GoogleShopping] SerpApi key is missing!")
            return prices

        try:
            # SerpApi Google Shopping Endpoint
            url = "https://serpapi.com/search.json"
            params = {
                "engine": "google_shopping",
                "q": product_name,
                "gl": "tr",          # Geolocation: Turkey
                "hl": "tr",          # Language: Turkish
                "api_key": settings.serpapi_key
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"[GoogleShopping] SerpApi returned {response.status_code}: {response.text}")
                    return prices

                data = response.json()
                
                # 'shopping_results' listesinde satıcılar ve fiyatları bulunur
                shopping_results = data.get("shopping_results", [])
                
                for item in shopping_results[:10]: # En iyi 10 sonucu alalım
                    # Price extraction: usually string like "47.519,57 TL" or float directly in extracted_price
                    price_val = item.get("extracted_price")
                    
                    if not price_val:
                        # Fallback to string parsing
                        price_str = item.get("price", "")
                        price_val = self._parse_price(price_str)
                        
                    if not price_val or price_val < 1000:
                        continue
                        
                    seller_name = item.get("source", "Bilinmeyen Satıcı")
                    link = item.get("link", "")
                    
                    prices.append(ScrapedPrice(
                        source=self.SOURCE_NAME,
                        price=float(price_val),
                        currency="TRY",
                        seller_name=seller_name,
                        seller_rating=None,  # Shopping API'den reyting genelde gelmez ama varsa eklenebilir
                        url=link,
                    ))

        except Exception as e:
            logger.error(f"[GoogleShopping] Scraping error: {e}")

        logger.success(f"[GoogleShopping] Fetched {len(prices)} prices")
        return prices

    def _parse_price(self, text: str) -> float | None:
        if not text: return None
        cleaned = text.replace("TL", "").replace("₺", "").strip()
        cleaned = cleaned.replace(".", "")   # binlik ayıracı
        cleaned = cleaned.replace(",", ".")  # ondalık
        
        try:
            return float(cleaned)
        except ValueError:
            return None
