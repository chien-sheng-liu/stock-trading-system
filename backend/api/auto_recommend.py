from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import traceback
from typing import Optional

from recommender import generate_recommendations
from data_fetcher import get_stocks_by_industry

router = APIRouter()

class AutoRecommendRequest(BaseModel):
    industry: Optional[str] = None

@router.post("/recommend/auto")
def auto_recommend(request: AutoRecommendRequest = Body(...)):
    """
    按產業推薦股票，為產業內所有股票生成評級。
    """
    try:
        if not request or not request.industry:
            raise HTTPException(status_code=400, detail="Industry is required.")

        industry = request.industry
        print(f"為「{industry}」產業內所有股票生成推薦...")
        
        stocks_in_industry = get_stocks_by_industry(industry)
        if not stocks_in_industry:
            raise HTTPException(status_code=404, detail=f"找不到該產業的股票: {industry}")

        # Directly generate recommendations for all stocks in the industry
        recommendations = generate_recommendations(stocks_in_industry)

        return {
            "type": "recommendation",
            "mode": "industry",
            "industry": industry,
            "recommendations": recommendations,
            "message": f"成功分析「{industry}」產業中的 {len(stocks_in_industry)} 支股票"
        }
    except Exception as e:
        print(f"自動推薦錯誤: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"推薦失敗: {str(e)}")
