'use client';

import { useState, useEffect } from 'react';
import Header from "@/components/Header";
import BacktestForm from "@/components/BacktestForm";
import DaytradeTabs from "@/components/DaytradeTabs";
import RealtimeRecommend from "@/components/RealtimeRecommend";
import RecommendationForm from "@/components/RecommendationForm";
import StockAnalysis from "@/components/StockAnalysis";
import WatchlistPage from "@/components/WatchlistPage";

export default function Home() {
  const [activeTab, setActiveTab] = useState('recommend');
  const [stockTicker, setStockTicker] = useState('');
  const [pendingDaytradeTicker, setPendingDaytradeTicker] = useState(null);
  const openStockAnalysis = (t) => {
    setStockTicker(t);
    setActiveTab('stock');
  };
  const openDaytradeAnalysis = (t) => {
    setPendingDaytradeTicker(t);
    setActiveTab('recommend');
  };
  const openWatchlist = () => setActiveTab('watch');

  const handleResults = (_data) => {};

  return (
    <>
      <Header onAnalyze={openStockAnalysis} onAnalyzeDaytrade={openDaytradeAnalysis} onGoWatchlist={openWatchlist} />
      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground">
              台股 AI 推薦與產業選股
            </h1>
            <p className="mt-3 text-lg text-gray-400">
              專業的量化洞察 x 精簡的 AI 文字建議
            </p>
          </div>

          <div className="w-full">
            <div className="mb-4 border-b border-gray-700">
              <nav className="-mb-px flex space-x-8" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('recommend')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'recommend'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  即時當沖
                </button>
                <button
                  onClick={() => setActiveTab('realtime')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'realtime'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  當沖推薦
                </button>
                <button
                  onClick={() => setActiveTab('ai')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'ai'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  AI 推薦
                </button>
                <button
                  onClick={() => setActiveTab('stock')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'stock'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  股票分析
                </button>
                <button
                  onClick={() => setActiveTab('watch')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'watch'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  自選清單
                </button>
                <button
                  onClick={() => setActiveTab('backtest')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'backtest'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
                  }`}
                >
                  策略回測
                </button>
              </nav>
            </div>

            <div className="pt-8">
              {(() => {
                const infoMap = {
                  recommend: '單股即時分K分析，提供當下買/賣/停損與資料來源標註（自動退階 1m/5m/15m）。',
                  realtime: '依選定產業掃描即時候選清單，排序顯示入場訊號與關鍵水位。',
                  ai: '以日線量化摘要，由 AI 產生簡潔的操作建議與亮點整理。',
                  stock: '波段/投資視角：計算買點/賣點/停損與風險報酬，並支援依產業批次分析。',
                  watch: '管理與快速存取自選代碼，支援即時分析與備註維護。',
                  backtest: '對歷史資料套用策略參數，檢視績效曲線與交易統計指標。',
                };
                const d = infoMap[activeTab] || '';
                return d ? (
                  <div className="mb-4 text-sm text-gray-400 flex items-start gap-2">
                    <span className="mt-0.5">💡</span>
                    <p className="leading-relaxed">{d}</p>
                  </div>
                ) : null;
              })()}
              {activeTab === 'recommend' && <DaytradeTabs triggerDaytradeTicker={pendingDaytradeTicker} onOpenStock={openStockAnalysis} />}
              {activeTab === 'realtime' && <RealtimeRecommend />}
              {activeTab === 'ai' && <RecommendationForm mode="single" aiOnly={true} />}
              {activeTab === 'stock' && <StockAnalysis initialTicker={stockTicker} onOpenDaytrade={openDaytradeAnalysis} />}
              {activeTab === 'watch' && <WatchlistPage onAnalyze={openStockAnalysis} />}
            {activeTab === 'backtest' && <BacktestForm />}
          </div>
        </div>
        </div>
      </main>
    </>
  );
}
