from fastapi import APIRouter
from pydantic import BaseModel
import numpy as np

router = APIRouter()

class InsightsRequest(BaseModel):
    recommendations: list

@router.post("/insights")
def portfolio_insights(req: InsightsRequest):
    recs = req.recommendations
    if not recs:
        return {
            "industry_distribution": {},
            "avg_risk_reward": 0,
            "count": 0
        }

    industries = {}
    risk_rewards = []

    for r in recs:
        industry = r.get("industry", "其他")
        industries[industry] = industries.get(industry, 0) + 1
        try:
            risk_rewards.append(float(r.get("risk_reward_ratio", 0)))
        except:
            continue

    return {
        "industry_distribution": industries,
        "avg_risk_reward": float(np.mean(risk_rewards)) if risk_rewards else 0,
        "count": len(recs)
    }
