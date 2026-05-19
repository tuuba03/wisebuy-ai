import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    user_purpose = Column(String)
    budget = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    analysis = relationship("AnalysisResult", back_populates="search", uselist=False)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_history.id"))
    
    ai_report = Column(String)
    purpose_fit_score = Column(Float, nullable=True)
    value_for_money_score = Column(Float, nullable=True)
    overall_sentiment_score = Column(Float, nullable=True)
    
    reviews_json = Column(JSON)
    prices_json = Column(JSON)
    videos_json = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    search = relationship("SearchHistory", back_populates="analysis")
