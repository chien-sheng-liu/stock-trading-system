'use client';

import React, { useState, useEffect, useRef } from 'react';

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
  const [loading, setLoading] = useState(false);
  const [loadingIndustry, setLoadingIndustry] = useState('');
  const [error, setError] = useState(null);
  const [industries, setIndustries] = useState([]);
  const [selectedIndustry, setSelectedIndustry] = useState('');

  // Fetch industries on component mount
  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/api/industries');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setIndustries(data.industries || []);
      } catch (e) {
        console.error("Failed to fetch industries:", e);
        // Optionally set an error state to display to the user
      }
    };
    fetchIndustries();
  }, []);

  // 手動推薦
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
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

  // Handle industry selection from dropdown
  const handleIndustryChange = (industry) => {
    setSelectedIndustry(industry);
    if (industry) {
      handleIndustryRecommend(industry);
    }
  };

  return (
    <div className="space-y-6">
      {/* 依產業推薦 (Custom Dropdown) */}
      <div>
        <h3 className="text-md font-semibold text-foreground mb-2">依產業推薦</h3>
        <CustomSelect
          options={industries}
          value={selectedIndustry}
          onChange={handleIndustryChange}
          placeholder="請選擇產業"
          disabled={loadingIndustry !== ''}
        />
        {loadingIndustry && <p className="text-sm text-gray-400 mt-2">分析中: {loadingIndustry}...</p>}
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
