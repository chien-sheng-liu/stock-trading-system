'use client';

import React, { useState, useMemo } from 'react';

const StatCard = ({ label, value, icon }) => (
  <div className="glass-card p-4 rounded-lg">
    <div className="flex items-center">
      <div className="flex-shrink-0 bg-secondary rounded-md p-3">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="ml-4">
        <p className="text-sm font-medium text-gray-400 truncate">{label}</p>
        <p className="text-lg font-semibold text-foreground">{value}</p>
      </div>
    </div>
  </div>
);

const renderBacktestResults = (results) => (
  <div className="space-y-6">
    <div>
      <h3 className="text-lg font-semibold text-foreground">
        回測結果: {results.symbol}
      </h3>
      <p className="text-sm text-gray-400">{results.period}</p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard label="總回報" value={`${results.totalReturn?.toFixed(2) ?? 'N/A'}%`} icon="💰" />
      <StatCard label="勝率" value={`${results.winRate?.toFixed(2) ?? 'N/A'}%`} icon="🎯" />
      <StatCard label="夏普比率" value={results.sharpeRatio?.toFixed(2) ?? 'N/A'} icon="📈" />
      <StatCard label="最大回撤" value={`${results.maxDrawdown?.toFixed(2) ?? 'N/A'}%`} icon="📉" />
      <StatCard label="交易次數" value={results.trades} icon="🔄" />
      <StatCard label="獲利交易" value={results.profitableTrades} icon="👍" />
    </div>
  </div>
);

const getRatingClass = (rating) => {
  switch (rating) {
    case '強烈推薦':
      return 'bg-green-500/20 text-green-400';
    case '推薦':
      return 'bg-blue-500/20 text-blue-400';
    case '謹慎推薦':
      return 'bg-yellow-500/20 text-yellow-400';
    case '不推薦':
      return 'bg-red-500/20 text-red-400';
    default:
      return 'bg-gray-500/20 text-gray-400';
  }
};

const RecommendationResults = ({ results }) => {
  const [activeTab, setActiveTab] = useState('recommended');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const { recommended, notRecommended } = useMemo(() => {
    const recommended = [];
    const notRecommended = [];
    (results.recommendations || []).forEach(rec => {
      if (rec.rating === '不推薦') {
        notRecommended.push(rec);
      } else {
        recommended.push(rec);
      }
    });
    return { recommended, notRecommended };
  }, [results.recommendations]);

  const activeList = activeTab === 'recommended' ? recommended : notRecommended;

  const paginatedRecommendations = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return activeList.slice(startIndex, startIndex + itemsPerPage);
  }, [activeList, currentPage]);

  const totalPages = Math.ceil(activeList.length / itemsPerPage);

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    setCurrentPage(1); // Reset to first page when switching tabs
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-foreground">推薦結果</h3>
      {results.message && (
        <div className="bg-secondary p-3 rounded-lg">
          <p className="text-sm text-gray-300">{results.message}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => handleTabClick('recommended')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'recommended'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
            }`}
          >
            推薦 ({recommended.length})
          </button>
          <button
            onClick={() => handleTabClick('not-recommended')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'not-recommended'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
            }`}
          >
            不推薦 ({notRecommended.length})
          </button>
        </nav>
      </div>

      {paginatedRecommendations.length > 0 ? (
        <div className="space-y-4 pt-4">
          {paginatedRecommendations.map((rec, index) => (
            <div key={index} className="glass-card p-4 rounded-lg">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h4 className="font-bold text-lg text-foreground">{rec.name}</h4>
                  <p className="text-sm text-gray-400">{rec.ticker}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRatingClass(rec.rating)}`}>
                  {rec.rating}
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-400">現價</p>
                  <p className="font-mono text-foreground">{rec.current_price}</p>
                </div>
                <div>
                  <p className="text-gray-400">進場區間</p>
                  <p className="font-mono text-foreground">{rec.entry_price_range}</p>
                </div>
                <div>
                  <p className="text-gray-400">目標價</p>
                  <p className="font-mono text-green-400">{rec.target_profit}</p>
                </div>
                <div>
                  <p className="text-gray-400">停損點</p>
                  <p className="font-mono text-red-400">{rec.stop_loss}</p>
                </div>
                <div>
                  <p className="text-gray-400">風險收益比</p>
                  <p className="font-mono text-foreground">{rec.risk_reward_ratio}:1</p>
                </div>
                <div>
                  <p className="text-gray-400">潛在報酬</p>
                  <p className="font-mono text-green-400">{rec.potential_return}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-400 pt-4">此分類中沒有標的。</p>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-4 pt-4">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 bg-secondary rounded-md disabled:opacity-50"
          >
            上一頁
          </button>
          <span className="text-sm text-gray-400">
            第 {currentPage} 頁 / 共 {totalPages} 頁
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 bg-secondary rounded-md disabled:opacity-50"
          >
            下一頁
          </button>
        </div>
      )}
    </div>
  );
};

export default function Results({ data }) {
  if (!data) {
    return null; // Don't render anything if there's no data
  }

  return (
    <div className="w-full glass-card p-6 animate-fade-in border rounded-xl">
      {data.type === 'backtest' && renderBacktestResults(data)}
      {data.type === 'recommendation' && <RecommendationResults results={data} />}
    </div>
  );
}
