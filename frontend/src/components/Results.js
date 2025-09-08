"use client";

import React from 'react';
import BacktestResults from './results/BacktestResults';
import RecommendationResults from './results/RecommendationResults';
import AiSingleAnalysis from './results/AiSingleAnalysis';

export default function Results({ data }) {
  if (!data) return null;
  return (
    <div className="w-full space-y-6">
      {data.type === 'backtest' && <BacktestResults results={data} />}
      {data.type === 'recommendation' && <RecommendationResults results={data} />}
      {data.type === 'ai_recommendation' && <AiSingleAnalysis payload={data} />}
    </div>
  );
}
