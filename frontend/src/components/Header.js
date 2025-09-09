"use client";

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

export default function Header({ onAnalyze, onAnalyzeDaytrade, onGoWatchlist }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [prices, setPrices] = useState({});
  const [loadingPrice, setLoadingPrice] = useState({});
  const [q, setQ] = useState('');
  const timeAgo = (iso) => {
    if (!iso) return '';
    try {
      const now = Date.now();
      const t = Date.parse(iso);
      if (!isFinite(t)) return '';
      const diff = Math.floor((now - t) / 1000); // seconds
      if (diff < 60) return `${diff}s前`;
      if (diff < 3600) return `${Math.floor(diff/60)}分前`;
      if (diff < 86400) return `${Math.floor(diff/3600)}小時前`;
      return `${Math.floor(diff/86400)}天前`;
    } catch (_) {
      return '';
    }
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/watchlist');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      setItems(Array.isArray(json.items) ? json.items : []);
    } catch (_) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const ensurePrice = async (t) => {
    const key = (t || '').toString();
    if (!key || prices[key] != null || loadingPrice[key]) return;
    try {
      setLoadingPrice(s => ({ ...s, [key]: true }));
      const res = await apiFetch('/stock/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: key })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      const px = (json && json.metrics && typeof json.metrics.price === 'number') ? json.metrics.price : null;
      setPrices(m => ({ ...m, [key]: px }));
    } catch (_) {
      setPrices(m => ({ ...m, [key]: null }));
    } finally {
      setLoadingPrice(s => ({ ...s, [key]: false }));
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-2xl" role="img" aria-label="logo">📈</span>
            <div>
              <h1 className="text-lg font-bold text-foreground">AI Trading Pro</h1>
              <p className="text-xs text-gray-400">台股智能交易系統</p>
            </div>
          </div>
          <div className="relative">
            <button
              type="button"
              onClick={() => setOpen(o => !o)}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-secondary hover:bg-secondary/80 border border-border text-foreground"
              title="查看自選清單"
            >自選清單{items && items.length ? `（${items.length}）` : ''}</button>
            {open && (
              <div className="absolute right-0 mt-2 w-72 bg-background border border-border rounded-md shadow-lg z-50">
                <div className="flex items-center justify-between px-2 py-1 border-b border-border">
                  <span className="text-xs text-gray-400">自選清單</span>
                  <button
                    className="text-[11px] px-2 py-0.5 rounded bg-secondary hover:bg-secondary/80 border border-border"
                    onClick={(e)=>{ e.stopPropagation(); refresh(); }}
                    disabled={loading}
                  >{loading ? '載入中…' : '重新整理'}</button>
                </div>
                <div className="px-2 py-1 border-b border-border">
                  <input
                    type="text"
                    value={q}
                    onChange={(e)=>setQ(e.target.value)}
                    placeholder="搜尋代碼或備註…"
                    className="w-full bg-secondary border border-border rounded px-2 py-1 text-xs"
                  />
                </div>
                <div className="max-h-72 overflow-auto">
                  {(!items || items.length === 0) ? (
                    <div className="p-3 text-xs text-gray-500">尚無自選。</div>
                  ) : (
                    <ul className="divide-y divide-border">
                      {items
                        .filter((it) => {
                          if (!q) return true;
                          const s = q.toLowerCase();
                          return (
                            (it.ticker && it.ticker.toLowerCase().includes(s)) ||
                            (it.name && String(it.name).toLowerCase().includes(s)) ||
                            (it.note && String(it.note).toLowerCase().includes(s))
                          );
                        })
                        .map((it) => (
                          <li key={it.ticker} className="px-2 py-2 text-sm hover:bg-secondary/40" onMouseEnter={()=>ensurePrice(it.ticker)}>
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <button
                                  className="text-foreground hover:underline"
                                  onClick={() => { setOpen(false); onAnalyze && onAnalyze(it.ticker); }}
                                  title="開啟股票分析"
                                >{it.ticker}{it.name ? `（${it.name}）` : ''}</button>
                                <div className="text-[11px] text-gray-500 truncate max-w-[220px]">
                                  {it.note ? String(it.note) : (prices[it.ticker] != null ? `現價 ${prices[it.ticker]?.toFixed ? prices[it.ticker].toFixed(2) : prices[it.ticker]}` : '—')}
                                  {it.created_at && (
                                    <span className="ml-1 text-[10px] text-gray-600">· {timeAgo(it.created_at)}</span>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <button
                                  className="text-[11px] px-1.5 py-0.5 rounded bg-secondary hover:bg-secondary/80 border border-border"
                                  title="股票分析"
                                  onClick={() => { setOpen(false); onAnalyze && onAnalyze(it.ticker); }}
                                >股</button>
                                <button
                                  className="text-[11px] px-1.5 py-0.5 rounded bg-secondary hover:bg-secondary/80 border border-border"
                                  title="當沖即時分析"
                                  onClick={() => { setOpen(false); onAnalyzeDaytrade && onAnalyzeDaytrade(it.ticker); }}
                                >沖</button>
                                <button
                                  className="text-[11px] text-rose-300 hover:text-rose-200"
                                  onClick={async (e)=>{
                                    e.stopPropagation();
                                    try { await apiFetch(`/watchlist/${it.ticker}`, { method: 'DELETE' }); } catch(_) {}
                                    refresh();
                                  }}
                                >移除</button>
                              </div>
                            </div>
                          </li>
                      ))}
                      {items.filter((it)=>{
                        if (!q) return false; // only show when searching and nothing matched
                        const s = q.toLowerCase();
                        return !((it.ticker && it.ticker.toLowerCase().includes(s)) || (it.note && String(it.note).toLowerCase().includes(s)));
                      }).length === items.length && (
                        <li className="px-2 py-2 text-xs text-gray-500">無符合「{q}」的項目</li>
                      )}
                    </ul>
                  )}
                </div>
                <div className="px-2 py-1 border-t border-border flex justify-end">
                  <button
                    className="text-[11px] px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white"
                    onClick={() => { setOpen(false); onGoWatchlist && onGoWatchlist(); }}
                  >管理自選清單</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
