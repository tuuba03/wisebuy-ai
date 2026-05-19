import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlencode

from app.core.config import get_settings
from app.services.scrapers.base import BaseScraper

settings = get_settings()

class SikayetvarScraper(BaseScraper):
    SOURCE_NAME = "sikayetvar"

    async def get_seller_complaints(self, seller_name: str) -> list[str]:
        logger.info(f"[Sikayetvar] Fetching complaints for: {seller_name}")
        complaints = []
        
        # "trendyol.com" veya "ciceksepeti.com" gibi domain uzantılarını temizleyelim
        clean_seller_name = seller_name.split('.')[0]
        
        # DuckDuckGo HTML araması
        url = "https://html.duckduckgo.com/html/"
        params = {"q": f"site:sikayetvar.com {clean_seller_name} şikayet"}
        
        headers = {
            "User-Agent": settings.scraper_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, data=params, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"[Sikayetvar] Failed to fetch data for {seller_name}, status: {response.status_code}")
                    return complaints

                soup = BeautifulSoup(response.text, "html.parser")
                results = soup.select(".result__snippet")
                
                for res in results[:5]: # En güncel/ilgili 5 şikayet snippet'ini al
                    text = res.text.strip()
                    if text:
                        complaints.append(text)

        except Exception as e:
            logger.error(f"[Sikayetvar] Scraping error for {seller_name}: {e}")

        logger.success(f"[Sikayetvar] Found {len(complaints)} complaints for {seller_name}")
        return complaints
