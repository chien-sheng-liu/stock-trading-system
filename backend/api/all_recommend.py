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
def all_recommend(request: AllRecommendRequest):
    """
    統一推薦接口:
    - mode = "auto" -> 隨機挑選熱門股票
    - mode = "manual" -> 根據輸入 ticker(s)
    - mode = "sector" -> 依照股票產業分類推薦
    """
    try:
        if request.mode == "auto":
            all_stocks = fetch_tw_stock_list()
            if not all_stocks:
                raise HTTPException(status_code=500, detail="無法取得熱門股票清單")

            num_stocks = random.randint(5, 8)
            selected_stocks = random.sample(all_stocks, num_stocks)

            candidates = find_candidates(selected_stocks)
            if not candidates:
                candidates = selected_stocks

            recommendations = generate_recommendations(candidates)
            return {
                "type": "recommendation",
                "mode": "auto",
                "recommendations": recommendations,
                "analyzed_stocks": selected_stocks,
                "message": f"AI分析了 {len(selected_stocks)} 支熱門股票，找到 {len(recommendations)} 支推薦標的"
            }

        elif request.mode == "manual":
            if not request.ticker:
                raise HTTPException(status_code=400, detail="manual 模式需要提供 ticker")

            ticker_list = [t.strip().upper() for t in request.ticker.split(',')]
            formatted_tickers = []
            for ticker in ticker_list:
                if not ticker.endswith('.TW') and ticker.isdigit():
                    ticker = f"{ticker}.TW"
                formatted_tickers.append(ticker)

            recommendations = generate_recommendations(formatted_tickers)
            return {
                "type": "recommendation",
                "mode": "manual",
                "recommendations": recommendations,
                "message": f"成功為 {len(recommendations)} 支股票生成推薦"
            }

        elif request.mode == "sector":
            all_stocks = fetch_tw_stock_list()
            if not all_stocks:
                raise HTTPException(status_code=500, detail="無法取得股票清單")

            # 分類股票
            sector_groups = {}
            for ticker in all_stocks:
                info = get_ticker_info(ticker)
                if not info:
                    continue
                sector = info.get("sector", "其他")
                if sector not in sector_groups:
                    sector_groups[sector] = []
                sector_groups[sector].append(ticker)

            results_by_sector = {}
            for sector, tickers in sector_groups.items():
                candidates = find_candidates(tickers)
                recs = generate_recommendations(candidates)
                if recs:
                    results_by_sector[sector] = recs

            return {
                "type": "recommendation",
                "mode": "sector",
                "recommendations_by_sector": results_by_sector,
                "message": f"依照產業分類，共分析 {len(all_stocks)} 支股票，分為 {len(sector_groups)} 個領域"
            }

        else:
            raise HTTPException(status_code=400, detail="mode 必須是 'auto'、'manual' 或 'sector'")

    except Exception as e:
        print(f"統一推薦錯誤: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"推薦失敗: {str(e)}")
