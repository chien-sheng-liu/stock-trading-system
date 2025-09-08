from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.recommendation_service import Recommender
from data_fetcher import get_stocks_by_industry


router = APIRouter()

class AutoRecommendRequest(BaseModel):
    industry: str

@router.post("/recommend/auto")
def auto_recommend(request: AutoRecommendRequest):
    try:
        tickers = get_stocks_by_industry(request.industry)
        if not tickers:
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"無法為產業 '{request.industry}' 找到任何股票。",
            }

        recommender_instance = Recommender(tickers)
        candidates = recommender_instance.find_candidates()

        if not candidates:
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"產業 '{request.industry}' 中沒有股票符合推薦條件。",
            }

        recommendations = recommender_instance.generate_recommendations(candidates, enable_ai=True)

        return {
            "type": "recommendation",
            "recommendations": recommendations,
            "message": f"成功為產業 '{request.industry}' 生成 {len(recommendations)} 個推薦。",
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
