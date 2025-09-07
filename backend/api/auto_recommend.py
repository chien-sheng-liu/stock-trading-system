from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.recommendation_service import Recommender
from data_fetcher import get_stocks_by_industry
import numpy as np


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
                "insights": { "avg_risk_reward": 0, "count": 0, "industry_distribution": {} }
            }

        recommender_instance = Recommender(tickers)
        candidates = recommender_instance.find_candidates()

        if not candidates:
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"產業 '{request.industry}' 中沒有股票符合推薦條件。",
                "insights": { "avg_risk_reward": 0, "count": 0, "industry_distribution": {} }
            }

        recommendations = recommender_instance.generate_recommendations(candidates, enable_ai=True)

        # Inlined portfolio_insights logic
        recs = recommendations
        if not recs:
            insights_data = {
                "industry_distribution": {},
                "avg_risk_reward": 0,
                "count": 0
            }
        else:
            industries = {}
            risk_rewards = []
            for r in recs:
                # The 'industry' field is missing in the recommendation object, so this will always be '其他'
                industry = r.get("industry", "其他")
                industries[industry] = industries.get(industry, 0) + 1
                try:
                    risk_rewards.append(float(r.get("risk_reward_ratio", 0)))
                except (ValueError, TypeError):
                    continue
            
            avg_risk_reward = float(np.mean(risk_rewards)) if risk_rewards else 0
            insights_data = {
                "industry_distribution": industries,
                "avg_risk_reward": avg_risk_reward,
                "count": len(recs)
            }

        return {
            "type": "recommendation",
            "recommendations": recommendations,
            "message": f"成功為產業 '{request.industry}' 生成 {len(recommendations)} 個推薦。",
            "insights": insights_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))