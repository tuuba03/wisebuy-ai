from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.database import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.services.product_analysis_service import ProductAnalysisService
from app.schemas.schemas import AnalyzeProductRequest, AnalyzeProductResponse

api_router = APIRouter()

@api_router.post("/analyze", response_model=AnalyzeProductResponse, summary="Analyze a product", tags=["Analysis"])
async def analyze_product(request: AnalyzeProductRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Received analysis request for {request.product_name}")
    repository = AnalysisRepository(db)
    service = ProductAnalysisService(repository)
    
    try:
        response = await service.analyze(
            product_name=request.product_name,
            user_purpose=request.purpose,
            budget=request.budget
        )
        return response
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/chat", summary="Chat with Gemini about the product", tags=["Chat"])
async def chat_with_gemini(request: dict, db: AsyncSession = Depends(get_db)):
    """Chat endpoint - analysis_context + message + product_name alır."""
    message = request.get("message")
    analysis_context = request.get("analysis_context", "")
    product_name = request.get("product_name", "")
    
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    
    # analysis_id varsa DB'den al
    analysis_id = request.get("analysis_id")
    if analysis_id and not analysis_context:
        repository = AnalysisRepository(db)
        analysis = await repository.get_analysis(analysis_id)
        if analysis:
            analysis_context = analysis.ai_report or ""
        
    from app.services.ai.gemini_service import GeminiAIService
    ai_service = GeminiAIService()
    
    try:
        reply = await ai_service.chat(
            analysis_context=analysis_context,
            user_message=message,
            product_name=product_name
        )
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Error during chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
