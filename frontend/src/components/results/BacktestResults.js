'use client';

import React from 'react';

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

export default function BacktestResults({ results }) {
  if (!results) return null;
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-foreground">回測結果: {results.symbol}</h3>
      <p className="text-sm text-gray-400">{results.period}</p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="總回報" value={`${results.totalReturn?.toFixed(2) ?? 'N/A'}%`} icon="💰" />
        <StatCard label="勝率" value={`${results.winRate?.toFixed(2) ?? 'N/A'}%`} icon="🎯" />
        <StatCard label="夏普比率" value={results.sharpeRatio?.toFixed(2) ?? 'N/A'} icon="📈" />
        <StatCard label="最大回撤" value={`${results.maxDrawdown?.toFixed(2) ?? 'N/A'}%`} icon="📉" />
        <StatCard label="交易次數" value={results.trades} icon="🔄" />
        <StatCard label="獲利交易" value={results.profitableTrades} icon="👍" />
      </div>
    </div>
  );
}

