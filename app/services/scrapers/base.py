from typing import Optional
from pydantic import BaseModel
from app.core.config import get_settings

class ScrapedReview(BaseModel):
    source: str
    rating: Optional[float]
    comment: str
    date: Optional[str]

class ScrapedPrice(BaseModel):
    source: str
    price: float
    currency: str
    seller_name: str
    seller_rating: Optional[float]
    url: str

class BaseScraper:
    def __init__(self):
        settings = get_settings()
        self.headers = {"User-Agent": settings.scraper_user_agent}
        self.timeout = settings.scraper_timeout
        self.max_reviews = 30

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return " ".join(text.replace("\n", " ").split()).strip()

    def _safe_float(self, text: str) -> Optional[float]:
        try:
            import re
            cleaned = re.sub(r"[^\d.,]", "", text)
            if not cleaned:
                return None
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            return float(cleaned)
        except Exception:
            return None
