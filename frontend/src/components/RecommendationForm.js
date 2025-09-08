'use client';

import React, { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../lib/api';

// Custom Select Component for better UI/UX
const CustomSelect = ({ options, value, onChange, placeholder, disabled }) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef(null);

  const displayValue = value || placeholder;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (selectRef.current && !selectRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleOptionClick = (option) => {
    onChange(option);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={selectRef}>
      <button
        type="button"
        className="mt-1 block w-full bg-secondary border border-border rounded-md shadow-sm py-2 px-3 text-left cursor-default focus:outline-none focus:ring-primary focus:border-primary sm:text-sm text-white flex justify-between items-center"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        {displayValue}
        {/* Arrow icon */}
        <svg className={`w-5 h-5 text-gray-400 transform ${isOpen ? '-rotate-180' : 'rotate-0'} transition-transform duration-200`} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
      </button>

      {isOpen && (
        <ul className="absolute z-10 mt-1 w-full bg-secondary shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
          {options.length > 0 ? (
            options.map((option) => (
              <li
                key={option}
                className="text-gray-300 cursor-default select-none relative py-2 pl-3 pr-9 hover:bg-primary hover:text-primary-foreground"
                onClick={() => handleOptionClick(option)}
              >
                {option}
              </li>
            ))
          ) : (
            <li className="text-gray-500 py-2 pl-3 pr-9">沒有選項</li>
          )}
        </ul>
      )}
    </div>
  );
};

export default function RecommendationForm({ onResults }) {
  const [ticker, setTicker] = useState('');
  const [loadingIndustry, setLoadingIndustry] = useState('');
  const [error, setError] = useState(null);
  const [industries, setIndustries] = useState([]);
  const [selectedIndustry, setSelectedIndustry] = useState('');
  const [aiAvailable, setAiAvailable] = useState(null); // null=unknown, bool=known
  const [aiStatus, setAiStatus] = useState(null);
  const [loadingAiSingle, setLoadingAiSingle] = useState(false);

  // Fetch industries on component mount
  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const response = await apiFetch('/industries');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setIndustries(data.industries || []);
      } catch (e) {
        console.error("Failed to fetch industries:", e);
        // Optionally set an error state to display to the user
      }
    };
    const fetchConfig = async () => {
      try {
        const res = await apiFetch('/config');
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const cfg = await res.json();
        const available = !!(cfg?.ai?.enabled);
        setAiAvailable(available);
        setAiStatus(cfg?.ai || null);
        // If AI is unavailable, we only hide AI actions via flags
      } catch (e) {
        console.warn('AI config unavailable:', e);
        setAiAvailable(false);
        setAiStatus(null);
        // Leave AI actions disabled by availability flag
      }
    };

    fetchIndustries();
    fetchConfig();
  }, []);

  // AI 推薦（/api/recommend/ai）
  const handleAiAnalyze = async (e) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setLoadingAiSingle(true);
    setError(null);
    try {
      // 與後端一致：若是數字且沒有 .TW，補上 .TW
      let t = ticker.trim();
      if (/^\d+$/.test(t) && !t.endsWith('.TW')) t = `${t}.TW`;
      const response = await apiFetch('/recommend/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: t }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      onResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingAiSingle(false);
    }
  };

  // 依產業推薦
  const handleIndustryRecommend = async (industry) => {
    setLoadingIndustry(industry);
    setError(null);
    try {
      const response = await apiFetch('/recommend/auto', {
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

  // Handle industry selection from dropdown
  const handleIndustryChange = (industry) => {
    setSelectedIndustry(industry);
    if (industry) {
      handleIndustryRecommend(industry);
    }
  };

  const ExampleChips = ({ onPick }) => (
    <div className="flex flex-wrap gap-2 mt-2">
      {['2330.TW', '2317.TW', '0050.TW'].map((ex) => (
        <button key={ex} type="button" onClick={() => onPick(ex)} className="px-2 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 text-gray-200 border border-border">
          {ex}
        </button>
      ))}
    </div>
  );

  const AiBadge = () => (
    <div className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${aiAvailable ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30' : 'bg-yellow-500/20 text-yellow-200 border border-yellow-400/30'}`}>
      {aiAvailable ? 'AI 可用' : 'AI 未啟用'}
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* AI 推薦卡片 */}
      <div className="glass-card p-4 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-md font-semibold text-foreground">AI 推薦（單股）</h3>
          {aiAvailable !== null && <AiBadge />}
        </div>
        <p className="text-xs text-gray-400">輸入台股代碼（純數字會自動補 .TW）。</p>
        <form onSubmit={handleAiAnalyze} className="mt-3 space-y-3">
          <input
            type="text"
            inputMode="text"
            autoCorrect="off"
            autoCapitalize="characters"
            spellCheck={false}
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="block w-full bg-secondary border border-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            placeholder="例如: 2330 或 2317.TW"
            aria-label="輸入股票代碼"
          />
          <ExampleChips onPick={(ex) => setTicker(ex)} />
          <button
            type="submit"
            disabled={loadingAiSingle || !ticker.trim() || aiAvailable === false}
            className="w-full py-2 px-4 rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
          >
            {loadingAiSingle ? 'AI 推薦中...' : '生成 AI 推薦'}
          </button>
          {aiAvailable === false && (
            <div className="text-[11px] text-yellow-300">請於後端設定 OPENAI_API_KEY 並安裝 openai 套件。</div>
          )}
          {error && <p className="text-sm text-danger">Error: {error}</p>}
        </form>
      </div>

      {/* 依產業推薦卡片 */}
      <div className="glass-card p-4 rounded-lg">
        <h3 className="text-md font-semibold text-foreground mb-2">依產業推薦</h3>
        <p className="text-xs text-gray-400">選擇產業即自動產生候選標的與投組洞察。</p>
        <div className="mt-3">
          <CustomSelect
            options={industries}
            value={selectedIndustry}
            onChange={handleIndustryChange}
            placeholder={industries.length ? '請選擇產業' : '載入產業中...'}
            disabled={loadingIndustry !== '' || !industries.length}
          />
          {loadingIndustry && <p className="text-sm text-gray-400 mt-2">分析中：{loadingIndustry}...</p>}
        </div>
      </div>
    </div>
  );
}
