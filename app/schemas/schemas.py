from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class ReviewItem(BaseModel):
    source: str
    rating: Optional[float]
    comment: str
    date: Optional[str]

class PriceEntry(BaseModel):
    source: str
    price: float
    currency: str
    seller_name: str
    seller_rating: Optional[float]
    url: str

class VideoSummary(BaseModel):
    platform: str
    video_title: str
    video_url: str
    key_points: List[str]

class AlternativeProduct(BaseModel):
    name: str
    reason: str
    approximate_price: Optional[float]

class ComplaintCategory(BaseModel):
    label: str
    percentage: float

class AnalyzeProductRequest(BaseModel):
    product_name: str
    purpose: str
    budget: Optional[float] = None

class AnalyzeProductResponse(BaseModel):
    analysis_id: int
    product_name: str
    purpose_fit_score: Optional[float]
    value_for_money_score: Optional[float]
    overall_sentiment_score: Optional[float]
    ai_report: str
    prices: List[PriceEntry]
    top_reviews: List[ReviewItem]
    video_summaries: List[VideoSummary]
    alternatives: List[AlternativeProduct]
    top_pros: List[str] = []
    top_cons: List[str] = []
    complaint_categories: List[ComplaintCategory] = []
    created_at: datetime

class ChatRequest(BaseModel):
    analysis_id: int
    message: str

class ChatResponse(BaseModel):
    reply: str
