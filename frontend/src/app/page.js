'use client';

import { useState, useEffect } from 'react';
import Header from "@/components/Header";
import BacktestForm from "@/components/BacktestForm";
import RecommendationForm from "@/components/RecommendationForm";
import Results from "@/components/Results";

export default function Home() {
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState('recommend');

  const handleResults = (data) => {
    setResults(data);
  };

  return (
    <>
      <Header />
      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground">
              AI-Powered Trading Assistant
            </h1>
            <p className="mt-3 text-lg text-gray-400">
              專業的台股分析與智能交易建議
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
                  當沖標的推薦
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
              {activeTab === 'recommend' && <RecommendationForm onResults={handleResults} />}
              {activeTab === 'backtest' && <BacktestForm onResults={handleResults} />}
            </div>
          </div>

          {results && (
            <div className="mt-12">
              <Results data={results} />
            </div>
          )}
        </div>
      </main>
    </>
  );
}
