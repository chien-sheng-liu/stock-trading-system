'use client';

import React, { useState } from 'react';

export default function BacktestForm({ onResults }) {
  const [ticker, setTicker] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [strategyParams, setStrategyParams] = useState('{}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          start_date: startDate,
          end_date: endDate,
          strategy_params: JSON.parse(strategyParams),
        }),
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

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="ticker-backtest" className="block text-sm font-medium text-gray-300">
          股票代碼
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="ticker-backtest"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="block w-full bg-secondary border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            placeholder="例如: 2330"
            required
          />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-medium text-gray-300">
            開始日期
          </label>
          <div className="mt-1">
            <input
              type="date"
              id="start-date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="block w-full bg-secondary border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
              required
            />
          </div>
        </div>
        <div>
          <label htmlFor="end-date" className="block text-sm font-medium text-gray-300">
            結束日期
          </label>
          <div className="mt-1">
            <input
              type="date"
              id="end-date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="block w-full bg-secondary border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
              required
            />
          </div>
        </div>
      </div>
      <div>
        <label htmlFor="strategy-params" className="block text-sm font-medium text-gray-300">
          策略參數 (JSON)
        </label>
        <div className="mt-1">
          <textarea
            id="strategy-params"
            rows={3}
            value={strategyParams}
            onChange={(e) => setStrategyParams(e.target.value)}
            className="block w-full bg-secondary border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            placeholder='例如: { "short_window": 5, "long_window": 20 }'
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {loading ? '回測中...' : '開始回測'}
      </button>
      {error && <p className="mt-2 text-sm text-danger">Error: {error}</p>}
    </form>
  );
}