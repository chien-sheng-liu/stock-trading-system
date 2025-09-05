from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback

from recommender import generate_recommendations

router = APIRouter()

class RecommendationRequest(BaseModel):
    ticker: str

@router.post("/recommend")
def recommend(request: RecommendationRequest):
    """Returns trading recommendations for a list of tickers."""
    try:
        # 分割股票代碼
        ticker_list = [ticker.strip().upper() for ticker in request.ticker.split(',')]

        # 為台股代碼加上 .TW 後綴（如果還沒有）
        formatted_tickers = []
        for ticker in ticker_list:
            if not ticker.endswith('.TW') and ticker.isdigit():
                ticker = f"{ticker}.TW"
            formatted_tickers.append(ticker)

        print(f"為指定股票生成推薦: {formatted_tickers}")
        
        # Directly generate recommendations without filtering
        recommendations = generate_recommendations(formatted_tickers)
        
        if not recommendations:
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"無法為 {', '.join(formatted_tickers)} 生成推薦，請檢查股票代碼是否正確。"
            }

        return {
            "type": "recommendation",
            "recommendations": recommendations,
            "message": f"成功為 {len(recommendations)} 支股票生成推薦"
        }
    except Exception as e:
        print(f"推薦錯誤: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"推薦分析失敗: {str(e)}")
