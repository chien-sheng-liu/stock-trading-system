from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import traceback

from backtester import run_backtest
from services.strategies.strategy_common import ma_crossover_strategy
from data_fetcher import fetch_data

router = APIRouter()

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy_params: Dict[str, Any]

@router.post("/backtest")
def backtest(request: BacktestRequest):
    """Runs a backtest for a given ticker and strategy."""
    try:
        ticker = request.ticker.strip().upper()

        # 為台股代碼加上 .TW 後綴（如果還沒有）
        if not ticker.endswith('.TW') and ticker.isdigit():
            ticker = f"{ticker}.TW"

        print(f"回測股票: {ticker}")
        print(f"回測參數: {request.strategy_params}")

        data = fetch_data(
            tickers=[ticker],
            start_date=request.start_date,
            end_date=request.end_date
        )

        if ticker not in data:
            raise HTTPException(status_code=404, detail=f"無法獲取 {ticker} 的數據")

        if data[ticker].empty:
            raise HTTPException(status_code=404, detail=f"{ticker} 沒有數據")

        # 設置預設策略參數
        strategy_params = request.strategy_params if request.strategy_params else {"short_window": 5, "long_window": 20}

        results = run_backtest(
            data[ticker],
            ma_crossover_strategy,
            strategy_params
        )

        response_data = {
            "type": "backtest",
            "symbol": ticker,
            "strategy": "Moving Average Crossover",
            "period": f"{request.start_date} to {request.end_date}",
            **results
        }

        print(f"回測結果: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"回測錯誤: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"回測分析失敗: {str(e)}")
