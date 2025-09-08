Stock Trading Monorepo

This repo is organized as a simple monorepo with a clear frontend/backend split.

Features
- AI 推薦（單股）: 針對指定股票產生精簡的 AI 文字建議，介面顯示模型資訊；後端路由 POST `/api/recommend/ai`。
- 依產業推薦（自動）: 依選定產業自動找出候選標的，提供入場區間、停損、目標價與技術訊號，並彙整投組洞察；後端路由 POST `/api/recommend/auto`。

Project structure
- frontend/ — Next.js 14 app (App Router, Tailwind)
- backend/ — FastAPI service (uvicorn), data fetching, backtesting, DB access

Backend Layout
- core/
  - settings.py — loads `.env`, exposes `get_db_settings()`
  - database.py — connection pool + helpers (psycopg2)
- services/
  - recommendation_service.py — 當沖推薦邏輯（量化洞察 + AI 摘要）
  - analysis_service.py — AI 單股分析與量化洞察工具
  - openai_service.py — OpenAI Completions 客戶端封裝
- api/
  - auto_recommend.py — 依產業自動推薦（POST `/api/recommend/auto`）
  - ai_recommend.py — AI 單股推薦（POST `/api/recommend/ai`）
  - stock_analysis.py — 股票波段/投資分析（POST `/api/stock/analyze`）
  - backtest.py — 回測（POST `/api/backtest`）
  - industries.py, config.py — 輔助查詢與設定
- services/strategies/
  - strategy_common.py — 指標計算與通用策略（單一真源）
  - strategy_day.py — 當沖預設參數包裝（MA5/20/60 等）
  - strategy_stock.py — 波段/投資預設參數包裝（MA20/50/200 等）
- tools/
  - fetch_stocks.py, check_industries.py, verify_db.py — DB 工具腳本

Makefile
- dev: 同時啟動後端/前端（使用 dev.sh）
- dev-backend: 啟動 FastAPI（uvicorn）
- dev-frontend: 啟動 Next.js 開發伺服器
- fetch-stocks: 抓取台股清單並寫入 DB（需先設定 DB）
- check-industries: 列出各產業的股票數量
- verify-db: 檢查資料庫連線與 stocks 資料表

Local development
- Backend
  - cd backend
  - Create venv (optional): python3 -m venv .venv && source .venv/bin/activate
  - Install deps: pip install -r requirements.txt
  - Environment
    - Copy env template: cp .env.example .env, then fill in values.
    - Required DB vars (no in-code defaults):
      - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
    - Optional AI vars:
      - OPENAI_API_KEY, OPENAI_MODEL (use an instruct-capable model, e.g., gpt-3.5-turbo-instruct)
  - Run:
    - Option A: python start.py (http://127.0.0.1:5000)
    - Option B: uvicorn main:app --reload --host 127.0.0.1 --port 8000

- Frontend
  - cd frontend
  - Install deps: npm install
  - Env: cp .env.example .env.local (adjust API URL if needed)
  - Run dev: npm run dev (http://localhost:3000)
  - The app calls the backend at http://localhost:5000 or http://localhost:8000 per backend config.

One-command dev
- From repo root:
  - Copy env templates if needed:
    - cp backend/.env.example backend/.env
    - cp frontend/.env.example frontend/.env.local
  - Start both services: ./dev.sh
  - Stop: Ctrl+C

Housekeeping
- Clean caches: `make clean` (removes __pycache__ and .DS_Store)
- See CONTRIBUTING.md for code layout and how to add endpoints/services.

Key endpoints
- AI 推薦（單股）: POST /api/recommend/ai
  - Body: { "ticker": "2330.TW" }
  - Returns: { type: "ai_recommendation", summary, model, ... }
- 依產業推薦（自動）: POST /api/recommend/auto
  - Body: { "industry": "半導體" }
  - Returns: { type: "recommendation", recommendations: [...] }

API: AI 推薦 schema
- Request (POST `/api/recommend/ai`)
  - `ticker` string, e.g. `2330.TW`
- Response (200)
  - `type` string: `ai_recommendation`
  - `ticker` string
  - `summary` string | null — AI 文字建議（人類可讀）
  - `model` string | null — 使用的模型名稱
  - `details` any | null — 兼容欄位（保留）
  - `error` string | null — 若 AI 產生失敗
  - `ai_insights` object | any — 原始 AI 回傳（保留）
  - `insights` object — 量化洞察（非 AI，指標計算）
    - `price` number | null — 現價
    - `trend`
      - `ma5`, `ma20`, `ma60` number | null — 均線
      - `state` string | null — 多頭排列 | 空頭排列 | 盤整/糾結
    - `momentum`
      - `rsi` number | null
      - `rsi_state` string | null — 超買 | 超賣 | 平衡 | 中性
      - `macd`, `macd_signal`, `macd_hist` number | null
      - `macd_state` string | null — 黃金交叉 | 死亡交叉
    - `volatility`
      - `atr` number | null
      - `atr_pct` number | null — ATR/Price（0.02=2%）
      - `label` string | null — 低波動 | 中等波動 | 高波動
    - `volume`
      - `current` number | null — 當日量
      - `avg20` number | null — 20 日均量
      - `ratio` number | null — 當日/均量（1.5=1.5x）
      - `state` string | null — 放量 | 量縮 | 正常
    - `levels`
      - `support`, `resistance` number | null — 近 20 日區間
      - `distance_to_support_pct`, `distance_to_resistance_pct` number | null — 與支撐/壓力距離（百分比）
    - `performance`
      - `ret_5d_pct`, `ret_20d_pct`, `ret_60d_pct` number | null — 報酬百分比
    - `range_position`
      - `from_high_pct`, `from_low_pct` number | null — 距近高/近低（約近 6 個月）

Notes on features
- Manual recommendation has been removed. The UI supports:
  - AI 推薦 for a single ticker
  - Automatic recommendations by industry

Notes
- Build artifacts and vendor directories (e.g., frontend/.next, node_modules) are git-ignored.
- Python caches (__pycache__) and virtual env folders are git-ignored.
- Backend scripts under backend/scripts are utilities for data ingestion and verification.

Proposed cleanup (safe to remove)
- Top-level package-lock.json (empty/unused)
- Top-level __init__.py (empty placeholder)
- .DS_Store files
- .claude/ folders and frontend/CLAUDE.md (tool-local metadata)

If you’d like, I can remove the items above now.
