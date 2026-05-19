from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.models import SearchHistory, AnalysisResult

class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_search(self, product_name: str, user_purpose: str, budget: float | None) -> SearchHistory:
        search = SearchHistory(
            product_name=product_name,
            user_purpose=user_purpose,
            budget=budget
        )
        self.session.add(search)
        await self.session.commit()
        await self.session.refresh(search)
        return search

    async def create_analysis(
        self, 
        search_id: int, 
        ai_result: dict, 
        reviews: list, 
        prices: list, 
        video_summaries: list
    ) -> AnalysisResult:
        analysis = AnalysisResult(
            search_id=search_id,
            ai_report=ai_result.get("ai_report", ""),
            purpose_fit_score=ai_result.get("purpose_fit_score"),
            value_for_money_score=ai_result.get("value_for_money_score"),
            overall_sentiment_score=ai_result.get("overall_sentiment_score"),
            reviews_json=reviews,
            prices_json=prices,
            videos_json=video_summaries
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get_analysis(self, analysis_id: int) -> AnalysisResult | None:
        result = await self.session.execute(
            select(AnalysisResult).where(AnalysisResult.id == analysis_id)
        )
        return result.scalars().first()
