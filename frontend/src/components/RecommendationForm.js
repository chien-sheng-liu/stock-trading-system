'use client';

import React, { useState } from 'react';

// 固定產業清單（和後端 industries.py 對應）
const INDUSTRIES = [
  "半導體業",
  "電腦及週邊設備業",
  "金融業",
  "通信網路業",
  "生技醫療業",
  "汽車業",
  "塑膠工業",
  "水泥工業"
];

export default function RecommendationForm({ onResults }) {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingIndustry, setLoadingIndustry] = useState('');
  const [error, setError] = useState(null);

  // 手動推薦
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/recommend/all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: "manual", ticker }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      onResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // 依產業推薦
  const handleIndustryRecommend = async (industry) => {
    setLoadingIndustry(industry);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/recommend/auto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ industry }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      onResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingIndustry('');
    }
  };

  return (
    <div className="space-y-6">
      {/* 固定產業推薦 */}
      <div>
        <h3 className="text-md font-semibold text-foreground mb-2">依產業推薦</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {INDUSTRIES.map((industry) => (
            <button
              key={industry}
              onClick={() => handleIndustryRecommend(industry)}
              disabled={loadingIndustry === industry}
              className="py-2 px-3 text-sm rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              {loadingIndustry === industry ? `分析中...` : industry}
            </button>
          ))}
        </div>
      </div>

      {/* 分隔線 */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-background px-2 text-sm text-gray-400">或</span>
        </div>
      </div>

      {/* 手動輸入股票 */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="ticker-recommend" className="block text-sm font-medium text-gray-300">
            輸入特定股票代碼
          </label>
          <input
            type="text"
            id="ticker-recommend"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="mt-1 block w-full bg-secondary border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            placeholder="例如: 2330, 2317.TW"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !ticker.trim()}
          className="w-full py-2 px-4 rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 disabled:opacity-50"
        >
          {loading ? '分析中...' : '分析指定股票'}
        </button>
        {error && <p className="mt-2 text-sm text-danger">Error: {error}</p>}
      </form>
    </div>
  );
}
