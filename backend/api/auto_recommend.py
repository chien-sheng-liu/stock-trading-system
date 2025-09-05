from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from recommender import Recommender  # Import the class
from data_fetcher import get_stocks_by_industry

router = APIRouter()

class AutoRecommendRequest(BaseModel):
    industry: str

@router.post("/recommend/auto")
def auto_recommend(request: AutoRecommendRequest):
    try:
        print(f"Received auto-recommend request for industry: {request.industry}")
        tickers = get_stocks_by_industry(request.industry)
        if not tickers:
            print(f"No tickers found for industry: {request.industry}")
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"無法為產業 '{request.industry}' 找到任何股票。"
            }

        print(f"Found {len(tickers)} tickers for {request.industry}. Initializing recommender...")
        
        # Use the new Recommender class
        recommender_instance = Recommender(tickers)
        
        print("Finding candidates...")
        candidates = recommender_instance.find_candidates()
        
        if not candidates:
            print("No candidates found after analysis.")
            return {
                "type": "recommendation",
                "recommendations": [],
                "message": f"產業 '{request.industry}' 中沒有股票符合推薦條件。"
            }

        print(f"Found {len(candidates)} candidates. Generating recommendations...")
        recommendations = recommender_instance.generate_recommendations(candidates)
        
        print(f"Returning {len(recommendations)} recommendations.")
        return {
            "type": "recommendation",
            "recommendations": recommendations,
            "message": f"成功為產業 '{request.industry}' 生成 {len(recommendations)} 個推薦。"
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
