import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import re
import json
import urllib.parse

from app.services.scrapers.base import BaseScraper, ScrapedPrice
from app.core.exceptions import ScrapingException

class AkakceScraper(BaseScraper):
    SOURCE_NAME = "akakce"
    BASE_URL = "https://www.akakce.com"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def get_prices(self, product_name: str) -> list[ScrapedPrice]:
        logger.info(f"[Akakce] Fetching prices for: {product_name}")
        prices: list[ScrapedPrice] = []

        try:
            # Akakçe Cloudflare koruması kullanıyor, bu yüzden DuckDuckGo üzerinden
            # Akakçe'deki fiyat ve satıcı bilgilerini topluyoruz
            ddg_url = "https://html.duckduckgo.com/html/"
            params = {"q": f"site:akakce.com {product_name} fiyat satıcı"}

            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.post(ddg_url, data=params, headers=self.headers)
                
                if response.status_code != 200:
                    logger.warning(f"[Akakce] DuckDuckGo returned {response.status_code}")
                    return prices

                soup = BeautifulSoup(response.text, "html.parser")
                
                # DuckDuckGo sonuçlarından Akakçe linklerini ve snippet'lerini çıkar
                results = soup.select("div.result")
                
                akakce_product_url = None
                
                for result in results:
                    link_el = result.select_one("a.result__a")
                    if not link_el:
                        continue
                    
                    href = link_el.get("href", "")
                    title = link_el.get_text(strip=True)
                    
                    # Sadece akakce.com linklerini al
                    if "akakce.com" not in href:
                        continue
                    
                    # Ürün fiyat sayfasını bul (genelde "en-ucuz" veya "fiyat" içerir)
                    if "en-ucuz" in href or "fiyat" in href:
                        # DuckDuckGo redirect URL'sinden gerçek URL'i çıkar
                        actual_url_match = re.search(r'uddg=(https?[^&]+)', href)
                        if actual_url_match:
                            akakce_product_url = urllib.parse.unquote(actual_url_match.group(1))
                        break
                
                if not akakce_product_url:
                    logger.warning(f"[Akakce] No product URL found via DuckDuckGo")
                    # DuckDuckGo snippet'lerinden fiyat bilgisi çıkarmayı dene
                    prices = self._extract_prices_from_snippets(soup, product_name)
                    if prices:
                        return prices
                    return prices
                
                logger.info(f"[Akakce] Product URL: {akakce_product_url}")
                
                # Akakçe ürün sayfasını direkt çekmeyi dene (bazen Cloudflare geçirir)
                try:
                    prod_response = await client.get(akakce_product_url, headers={
                        **self.headers,
                        "Referer": "https://www.google.com/",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Cache-Control": "no-cache",
                    })
                    
                    if prod_response.status_code == 200 and "Just a moment" not in prod_response.text[:500]:
                        prod_soup = BeautifulSoup(prod_response.text, "html.parser")
                        prices = self._parse_product_page(prod_soup, akakce_product_url)
                        
                        if prices:
                            logger.success(f"[Akakce] Direct scrape successful! {len(prices)} prices")
                            return prices
                except Exception as e:
                    logger.debug(f"[Akakce] Direct scrape failed: {e}")
                
                # Direkt çekme başarısız -> DuckDuckGo'dan daha fazla fiyat bilgisi topla
                logger.info("[Akakce] Falling back to DuckDuckGo price extraction")
                
                # Akakçe'nin farklı satıcılarını DuckDuckGo'dan ara
                response2 = await client.post(ddg_url, data={
                    "q": f"akakce.com {product_name} TL satıcı pttavm hepsiburada trendyol"
                }, headers=self.headers)
                
                if response2.status_code == 200:
                    soup2 = BeautifulSoup(response2.text, "html.parser")
                    prices = self._extract_prices_from_snippets(soup2, product_name)

        except Exception as e:
            logger.error(f"[Akakce] Scraping error: {e}")

        logger.success(f"[Akakce] Fetched {len(prices)} prices")
        return prices

    def _parse_product_page(self, soup: BeautifulSoup, product_url: str) -> list[ScrapedPrice]:
        """Akakçe ürün sayfasından satıcı/fiyat bilgilerini çıkarır."""
        prices = []
        
        # Farklı selector'ları dene
        seller_cards = (
            soup.select("a.iC") or 
            soup.select("ul#PL li") or 
            soup.select("div.pl_v8 li")
        )
        
        for card in seller_cards:
            # Fiyat
            price_el = card.select_one("span.pt_v8") or card.select_one("span.pt_v9")
            if not price_el:
                continue
            
            price_value = self._parse_price(price_el.get_text(strip=True))
            if not price_value:
                continue
            
            # Satıcı adı
            seller_name = "Bilinmeyen Satıcı"
            seller_span = card.select_one("span.v_v8")
            if seller_span:
                img = seller_span.select_one("img")
                platform = img.get("alt", "") if img else ""
                raw_text = seller_span.get_text(separator=" ", strip=True)
                store = raw_text.replace(platform, "").strip().lstrip("/").strip()
                
                if store and platform:
                    seller_name = f"{store} ({platform})"
                elif store:
                    seller_name = store
                elif platform:
                    seller_name = platform
            
            # Link
            url = product_url
            href = card.get("href", "") if card.name == "a" else ""
            if href and href.startswith("/"):
                url = self.BASE_URL + href
            
            prices.append(ScrapedPrice(
                source=self.SOURCE_NAME,
                price=price_value,
                currency="TRY",
                seller_name=seller_name,
                seller_rating=None,
                url=url,
            ))
        
        return prices

    def _extract_prices_from_snippets(self, soup: BeautifulSoup, product_name: str) -> list[ScrapedPrice]:
        """DuckDuckGo snippet'lerinden fiyat ve satıcı bilgisi çıkarır."""
        prices = []
        seen_sellers = set()
        
        results = soup.select("div.result")
        
        for result in results:
            snippet_el = result.select_one("a.result__snippet")
            title_el = result.select_one("a.result__a")
            link_el = result.select_one("a.result__a")
            
            if not title_el:
                continue
            
            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            full_text = f"{title} {snippet}"
            
            # "akakce" içermeyen sonuçları atla
            href = link_el.get("href", "") if link_el else ""
            if "akakce" not in href and "akakce" not in title.lower():
                continue
            
            # URL'i çöz
            actual_url = href
            url_match = re.search(r'uddg=(https?[^&]+)', href)
            if url_match:
                actual_url = urllib.parse.unquote(url_match.group(1))
            
            # Fiyat bilgisi çıkar (örn: "47.519,57 TL", "47.519 TL")
            price_matches = re.findall(r'([\d.]+[,]?\d*)\s*TL', full_text)
            
            # Satıcı adı çıkar
            known_sellers = [
                "PttAVM", "Hepsiburada", "Trendyol", "Amazon", "N11", "GittiGidiyor",
                "Pazarama", "Teknosa", "MediaMarkt", "Vatan", "Çiçeksepeti", "Letgo",
                "MAC INTERNET", "İstanbul Bilişim", "lotusgsm", "Gürgenler"
            ]
            
            for price_text in price_matches[:1]:  # Her sonuçtan sadece ilk fiyatı al
                price_value = self._parse_price(price_text + " TL")
                if not price_value or price_value < 1000:
                    continue
                
                # Satıcıyı bul
                seller_name = "Akakçe"
                for seller in known_sellers:
                    if seller.lower() in full_text.lower():
                        if seller not in seen_sellers:
                            seller_name = seller
                            seen_sellers.add(seller)
                            break
                
                prices.append(ScrapedPrice(
                    source=self.SOURCE_NAME,
                    price=price_value,
                    currency="TRY",
                    seller_name=seller_name,
                    seller_rating=None,
                    url=actual_url,
                ))
        
        return prices

    def _parse_price(self, text: str) -> float | None:
        """Türk fiyat formatını float'a çevirir. Örn: '47.519,57 TL' -> 47519.57"""
        cleaned = text.replace("TL", "").strip()
        cleaned = cleaned.replace(".", "")   # binlik ayıracı
        cleaned = cleaned.replace(",", ".")  # ondalık
        
        try:
            return float(cleaned)
        except ValueError:
            return None
