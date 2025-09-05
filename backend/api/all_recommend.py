from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback
import random

from recommender import find_candidates, generate_recommendations
from data_fetcher import fetch_tw_stock_list, get_ticker_info

router = APIRouter()

class AllRecommendRequest(BaseModel):
    mode: str  # "auto" | "manual" | "sector"
    ticker: str | None = None  # manual 模式才需要

@router.post("/recommend/all")
@router.post("/recommend/all")
def all_recommend(request: AllRecommendRequest):
    try:
        if request.mode == "auto":
            all_stocks = get_stocks_from_db()
            if not all_stocks:
                raise HTTPException(status_code=500, detail="No stocks found in DB")

            selected_stocks = random.sample([s["ticker"] for s in all_stocks], k=min(8, len(all_stocks)))
            candidates = find_candidates(selected_stocks)
            recommendations = generate_recommendations(candidates or selected_stocks)

            return {
                "type": "recommendation",
                "mode": "auto",
                "recommendations": recommendations,
                "analyzed_stocks": selected_stocks,
            }

        elif request.mode == "manual":
            ...
            # same as before, just call generate_recommendations()

        elif request.mode == "sector":
            all_stocks = get_stocks_from_db()
            if not all_stocks:
                raise HTTPException(status_code=500, detail="No stocks in DB")

            sector_groups = {}
            for s in all_stocks:
                info = get_ticker_info(s["ticker"])
                if not info: continue
                sector = info.get("sector", "Other")
                sector_groups.setdefault(sector, []).append(s["ticker"])

            results_by_sector = {}
            for sector, tickers in sector_groups.items():
                candidates = find_candidates(tickers)
                recs = generate_recommendations(candidates)
                if recs:
                    results_by_sector[sector] = recs

            return {
                "type": "recommendation",
                "mode": "sector",
                "recommendations_by_sector": results_by_sector
            }

        else:
            raise HTTPException(status_code=400, detail="Invalid mode")

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {e}")
