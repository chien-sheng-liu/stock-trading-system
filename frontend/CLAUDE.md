# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered Taiwan stock trading system with a Next.js frontend and Python Flask backend. The application provides day trading stock recommendations and strategy backtesting for Taiwan Stock Exchange (台股) securities.

## Architecture

**Frontend (Next.js 14)**
- Located in `/frontend/` directory
- Uses App Router with client-side components
- Styled with Tailwind CSS and custom glass-morphic design
- Components communicate with backend via REST API calls to `http://127.0.0.1:5000`

**Backend (Python)**  
- Located in `/backend/` directory
- Flask-based API server
- Technical analysis strategies in `strategy.py` using pandas/numpy
- Provides `/api/backtest` and `/api/recommend` endpoints

**Key Components:**
- `src/app/page.js` - Main dashboard with hero section and feature cards
- `src/components/BacktestForm.js` - Strategy backtesting form (POST to `/api/backtest`)
- `src/components/RecommendationForm.js` - Stock recommendation form (POST to `/api/recommend`)  
- `src/components/Results.js` - Displays API response data
- `backend/strategy.py` - Technical indicators (MA, RSI, ATR, Volume Spike) and crossover strategies

## Development Commands

**Frontend Development:**
```bash
cd frontend
npm run dev          # Start development server on http://localhost:3000
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
```

**Backend Development:**
```bash
cd backend
python app.py        # Start Flask server on http://127.0.0.1:5000 (assumed)
```

## Code Conventions

- **Language**: Mixed Chinese/English UI with Chinese labels and English code
- **Styling**: Tailwind CSS with custom utilities in `globals.css`
- **Components**: Functional React components using hooks
- **API Communication**: Async/await with fetch(), JSON request/response
- **Forms**: Controlled components with loading/error states
- **Fonts**: Inter + Noto Sans TC for Chinese character support

## Technical Details

- **Stock Ticker Format**: Taiwan stock codes (e.g., "2330" for TSMC)
- **Date Range**: ISO date format (YYYY-MM-DD) for start/end dates
- **Strategy Parameters**: JSON string format for backtest configuration
- **API Endpoints**: Flask backend serves both recommendation and backtesting
- **State Management**: React useState for form data and API responses

## Key Features

1. **Day Trading Recommendations** - AI-driven stock picks for Taiwan market
2. **Strategy Backtesting** - Test trading strategies against historical data  
3. **Technical Indicators** - MA crossover, RSI, ATR, volume analysis
4. **Real-time UI** - Loading states and error handling for API calls