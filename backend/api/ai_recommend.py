from fastapi import APIRouter
from pydantic import BaseModel

# Import the new, centralized services
from services.analysis_service import analyze_with_ai, compute_quant_insights
from core.database import get_stock_by_ticker

router = APIRouter()

class TickerRequest(BaseModel):
    ticker: str

@router.post("/recommend/ai")
async def recommend_ai(request: TickerRequest):
    """
    AI 推薦 API（單一股票）
    """
    ticker = request.ticker
    try:
        # 1) AI 文字建議 - from analysis_service
        insights_ai = analyze_with_ai(ticker)
        
        summary = None
        model = None
        details = None
        error = None

        if isinstance(insights_ai, dict):
            summary = insights_ai.get("summary") or insights_ai.get("text")
            model = insights_ai.get("model")
            error = insights_ai.get("error")
            details = insights_ai.get("result")

        # 2) 結構化量化洞察（非 AI） - from analysis_service
        more_insights = compute_quant_insights(ticker)

        info = get_stock_by_ticker(ticker) or {}
        return {
            "type": "ai_recommendation",
            "ticker": ticker,
            "name": info.get("name"),
            "summary": summary,
            "model": model,
            "details": details,
            "insights": more_insights,
            "error": error,
            "ai_insights": insights_ai,
        }
    except Exception as e:
        return {"error": str(e)}
