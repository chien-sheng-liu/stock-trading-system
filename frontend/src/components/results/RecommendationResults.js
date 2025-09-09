'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const Pill = ({ children, className = '' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>{children}</span>
);

const deriveHighlightsFromInsights = (q) => {
  if (!q) return [];
  const hs = [];
  if (q.trend?.state) hs.push(`趨勢：${q.trend.state}`);
  if (q.momentum?.rsi_state) hs.push(`RSI：${q.momentum.rsi_state}`);
  if (q.momentum?.macd_state) hs.push(`MACD：${q.momentum.macd_state}`);
  if (q.volatility?.label) hs.push(`波動：${q.volatility.label}`);
  if (q.volume?.state) hs.push(`量能：${q.volume.state}`);
  return hs.slice(0, 4);
};

const getRatingClass = (rating) => {
  switch (rating) {
    case '強烈推薦': return 'bg-green-500/20 text-green-400';
    case '推薦': return 'bg-blue-500/20 text-blue-400';
    case '謹慎推薦': return 'bg-yellow-500/20 text-yellow-400';
    case '不推薦': return 'bg-red-500/20 text-red-400';
    default: return 'bg-gray-500/20 text-gray-400';
  }
};

const AiSummary = ({ ai }) => {
  if (!ai) return null;
  if (ai.error) {
    return (
      <div className="bg-rose-900/20 border border-rose-700/40 rounded-md p-3 text-sm">
        <div className="flex items-center gap-2 text-rose-300">
          <span>⚠️</span>
          <span>AI 錯誤：{String(ai.error)}</span>
        </div>
      </div>
    );
  }
  const summary = ai.summary || ai.text;
  // Try to extract core ops: 買點 / 賣點 / 停損 / 風控
  const parseOps = (text) => {
    if (!text || typeof text !== 'string') return null;
    try {
      const buyMatch = text.match(/買點[:：]\s*([^；。]+)/);
      const sellMatch = text.match(/賣點[:：]\s*([^；。\/\n]+)/);
      const stopMatch = text.match(/停損[:：]\s*([^；。\n]+)/);
      const riskMatch = text.match(/風控[:：]\s*([^；。\n]+)/);
      return {
        buy: buyMatch ? buyMatch[1].trim() : null,
        sell: sellMatch ? sellMatch[1].trim() : null,
        stop: stopMatch ? stopMatch[1].trim() : null,
        risk: riskMatch ? riskMatch[1].trim() : null,
      };
    } catch (_) {
      return null;
    }
  };
  const ops = parseOps(summary);
  if (summary) {
    return (
      <div className="bg-purple-900/20 border border-purple-700/40 rounded-md p-3">
        {ops && (ops.buy || ops.sell || ops.stop || ops.risk) && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3 text-xs">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-gray-300">🟩 買點</span>
              {ops.buy ? (
                <Pill className="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">{ops.buy}</Pill>
              ) : (
                <span className="text-gray-500">—</span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-gray-300">🟥 賣點</span>
              {ops.sell && (<Pill className="bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">目標 {ops.sell}</Pill>)}
              {ops.stop && (<Pill className="bg-rose-500/20 text-rose-300 border border-rose-400/30">停損 {ops.stop}</Pill>)}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-gray-300">💡 風控</span>
              {ops.risk ? (
                <Pill className="bg-secondary/60 text-foreground border border-border">{ops.risk}</Pill>
              ) : (
                <Pill className="bg-secondary/60 text-foreground border border-border">單筆風險 1%~2%</Pill>
              )}
            </div>
          </div>
        )}
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{summary}</p>
        <div className="mt-3 text-[11px] text-gray-400">
          <span className="mr-2">🤖 由 AI 生成</span>
          {ai.model && <span>模型: {ai.model}</span>}
        </div>
      </div>
    );
  }
  return <div className="text-sm text-gray-400">AI 建議不可用</div>;
};

export default function RecommendationResults({ results, onAnalyze }) {
  const [activeTab, setActiveTab] = useState('recommended');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Filters + sorting
  const [onlyBull, setOnlyBull] = useState(false);
  const [maxAtrPct, setMaxAtrPct] = useState('');
  const [minRR, setMinRR] = useState('');
  const [sortKey, setSortKey] = useState('default');
  // Sparkline controls
  const [sparkScale, setSparkScale] = useState('price');
  const [showBaseline, setShowBaseline] = useState(true);

  // simple toast (top-level)
  const [toast, setToast] = useState('');
  const showToast = (msg) => { setToast(msg); setTimeout(()=>setToast(''), 1500); };

  // Saved filters
  useEffect(() => {
    try {
      const raw = typeof window !== 'undefined' && window.localStorage.getItem('recFilters:v1');
      if (raw) {
        const s = JSON.parse(raw);
        if (typeof s.onlyBull === 'boolean') setOnlyBull(s.onlyBull);
        if (typeof s.maxAtrPct === 'string') setMaxAtrPct(s.maxAtrPct);
        if (typeof s.minRR === 'string') setMinRR(s.minRR);
        if (typeof s.sortKey === 'string') setSortKey(s.sortKey);
      }
    } catch (_) {}
  }, []);
  useEffect(() => {
    try {
      const s = { onlyBull, maxAtrPct, minRR, sortKey };
      if (typeof window !== 'undefined') window.localStorage.setItem('recFilters:v1', JSON.stringify(s));
    } catch (_) {}
  }, [onlyBull, maxAtrPct, minRR, sortKey]);

  const summary = useMemo(() => {
    const recs = results?.recommendations || [];
    if (!recs.length) return null;
    let atrSum = 0, atrCount = 0;
    let rrSum = 0, rrCount = 0;
    let bullCount = 0, trendCount = 0;
    let r5Sum = 0, r5Count = 0;
    let r20Sum = 0, r20Count = 0;
    recs.forEach((r) => {
      const rr = Number(r.risk_reward_ratio);
      if (!Number.isNaN(rr)) { rrSum += rr; rrCount += 1; }
      const atrPct = r.insights?.volatility?.atr_pct;
      if (typeof atrPct === 'number' && !Number.isNaN(atrPct)) { atrSum += (atrPct * 100); atrCount += 1; }
      const tState = r.insights?.trend?.state;
      if (tState) { trendCount += 1; if (tState === '多頭排列') bullCount += 1; }
      const p5 = r.insights?.performance?.ret_5d_pct;
      const p20 = r.insights?.performance?.ret_20d_pct;
      if (typeof p5 === 'number' && !Number.isNaN(p5)) { r5Sum += p5; r5Count += 1; }
      if (typeof p20 === 'number' && !Number.isNaN(p20)) { r20Sum += p20; r20Count += 1; }
    });
    const avgAtr = atrCount ? (atrSum / atrCount) : null;
    const avgRR = rrCount ? (rrSum / rrCount) : null;
    const bullPct = trendCount ? (bullCount / trendCount * 100) : null;
    const avgRet5 = r5Count ? (r5Sum / r5Count) : null;
    const avgRet20 = r20Count ? (r20Sum / r20Count) : null;
    return { count: recs.length, avgAtr, avgRR, bullPct, avgRet5, avgRet20 };
  }, [results]);

  const passesFilters = (rec) => {
    if (onlyBull) {
      const t = rec.insights?.trend?.state;
      if (t !== '多頭排列') return false;
    }
    if (maxAtrPct !== '') {
      const atrp = rec.insights?.volatility?.atr_pct;
      if (!(typeof atrp === 'number') || (atrp * 100) > Number(maxAtrPct)) return false;
    }
    if (minRR !== '') {
      const rr = Number(rec.risk_reward_ratio);
      if (Number.isNaN(rr) || rr < Number(minRR)) return false;
    }
    return true;
  };

  const sortRecs = (list) => {
    const arr = [...list];
    switch (sortKey) {
      case 'rr_desc':
        arr.sort((a, b) => Number(b.risk_reward_ratio) - Number(a.risk_reward_ratio));
        break;
      case 'atr_asc': {
        const av = (x) => (typeof x.insights?.volatility?.atr_pct === 'number') ? x.insights.volatility.atr_pct : Number.POSITIVE_INFINITY;
        arr.sort((a, b) => av(a) - av(b));
        break;
      }
      case 'trend_bull':
        arr.sort((a, b) => {
          const ta = a.insights?.trend?.state === '多頭排列' ? 1 : 0;
          const tb = b.insights?.trend?.state === '多頭排列' ? 1 : 0;
          return tb - ta;
        });
        break;
      default:
        break;
    }
    return arr;
  };

  const { recommended, notRecommended } = useMemo(() => {
    const recommended = [];
    const notRecommended = [];
    (results.recommendations || []).forEach(rec => {
      const pushRec = (rec.rating === '不推薦') ? notRecommended : recommended;
      if (passesFilters(rec)) pushRec.push(rec);
    });
    return { recommended: sortRecs(recommended), notRecommended: sortRecs(notRecommended) };
  }, [results.recommendations, onlyBull, maxAtrPct, minRR, sortKey]);

  const activeList = activeTab === 'recommended' ? recommended : notRecommended;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedRecommendations = activeList.slice(startIndex, startIndex + itemsPerPage);
  const totalPages = Math.ceil(activeList.length / itemsPerPage);

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-foreground">推薦結果</h3>
      {results.message && (
        <div className="bg-secondary p-3 rounded-lg">
          <p className="text-sm text-gray-300">{results.message}</p>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" className="rounded border-border bg-background" checked={onlyBull} onChange={(e) => { setOnlyBull(e.target.checked); setCurrentPage(1); }} />
            僅多頭排列
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            最大 ATR%
            <input type="number" min="0" step="0.1" value={maxAtrPct} onChange={(e) => { setMaxAtrPct(e.target.value); setCurrentPage(1); }} className="w-20 bg-secondary border border-border rounded px-2 py-1 text-right" />
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            最小 風報比
            <input type="number" min="0" step="0.1" value={minRR} onChange={(e) => { setMinRR(e.target.value); setCurrentPage(1); }} className="w-24 bg-secondary border border-border rounded px-2 py-1 text-right" />
          </label>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">排序</span>
          <select className="bg-secondary border border-border rounded px-2 py-1 text-sm" value={sortKey} onChange={(e) => { setSortKey(e.target.value); setCurrentPage(1); }}>
            <option value="default">預設</option>
            <option value="rr_desc">風報比（高→低）</option>
            <option value="atr_asc">ATR%（低→高）</option>
            <option value="trend_bull">多頭優先</option>
          </select>
          <span className="ml-3 text-sm text-gray-400">圖表</span>
          <select className="bg-secondary border border-border rounded px-2 py-1 text-sm" value={sparkScale} onChange={(e) => setSparkScale(e.target.value)}>
            <option value="price">價格</option>
            <option value="pct">百分比</option>
          </select>
          <label className="inline-flex items-center gap-1 text-sm text-gray-300 ml-2">
            <input type="checkbox" className="rounded border-border bg-background" checked={showBaseline} onChange={(e) => setShowBaseline(e.target.checked)} />
            基準線
          </label>
          <button
            type="button"
            onClick={() => { setOnlyBull(false); setMaxAtrPct(''); setMinRR(''); setSortKey('default'); setCurrentPage(1); try { if (typeof window !== 'undefined') window.localStorage.removeItem('recFilters:v1'); } catch (_) {} }}
            className="ml-2 text-xs text-gray-300 underline hover:text-gray-100"
          >
            重置篩選
          </button>
        </div>
      </div>

      {/* KPI badges row (compact) */}
      {summary && (
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <Pill className="bg-secondary/70 text-foreground border border-border" title="平均真實波幅（ATR）相對於價格的比例">
            平均 ATR%：{summary.avgAtr !== null ? summary.avgAtr.toFixed(1) + '%' : '—'}
          </Pill>
          <Pill className="bg-secondary/70 text-foreground border border-border" title="均線多頭排列（MA5>MA20>MA60）的比例">
            多頭占比：{summary.bullPct !== null ? summary.bullPct.toFixed(0) + '%' : '—'}
          </Pill>
          <Pill className="bg-secondary/70 text-foreground border border-border" title="近 5 / 20 日平均報酬（不代表未來績效）">
            平均 5日：{summary.avgRet5 !== null ? summary.avgRet5.toFixed(1) + '%' : '—'}｜20日：{summary.avgRet20 !== null ? summary.avgRet20.toFixed(1) + '%' : '—'}
          </Pill>
        </div>
      )}

      <div className="flex space-x-4 border-b border-gray-700">
        <button
          onClick={() => { setActiveTab('recommended'); setCurrentPage(1); }}
          className={`py-2 px-4 ${activeTab === 'recommended' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-200'}`}
        >
          推薦 ({recommended.length})
        </button>
        <button
          onClick={() => { setActiveTab('not-recommended'); setCurrentPage(1); }}
          className={`py-2 px-4 ${activeTab === 'not-recommended' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-200'}`}
        >
          不推薦 ({notRecommended.length})
        </button>
      </div>

      {paginatedRecommendations.length > 0 ? (
        <div className="space-y-4 pt-4">
          {paginatedRecommendations.map((rec, index) => (
            <div key={index} className="glass-card p-4 rounded-lg space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-bold text-lg text-foreground">{rec.name}</h4>
                  <p className="text-sm text-gray-400">{rec.ticker}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRatingClass(rec.rating)}`}>
                    系統: {rec.rating}
                  </span>
                  {rec.ai_summary?.result?.ai_rating && (
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-500/20 text-purple-300">
                      AI: {rec.ai_summary.result.ai_rating}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await fetch('/api/watchlist', {
                          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: rec.ticker })
                        });
                        showToast('已加入自選');
                      } catch (_) {
                        showToast('加入失敗');
                      }
                    }}
                    className="px-2 py-0.5 rounded text-xs bg-secondary hover:bg-secondary/80 border border-border text-foreground"
                    title="加入自選清單"
                  >加入自選</button>
                  <button
                    type="button"
                    onClick={() => onAnalyze && onAnalyze(rec.ticker)}
                    className="px-2 py-0.5 rounded text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
                    title="分析此標的"
                  >分析</button>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await fetch('/api/daytrade/analyze', {
                          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: rec.ticker })
                        });
                        if (!res.ok) throw new Error('HTTP ' + res.status);
                        const json = await res.json();
                        // attach to record for inline view
                        rec._daytrade = json;
                        showToast(`即時：${json.decision}`);
                      } catch (e) {
                        showToast('即時分析失敗');
                      }
                    }}
                    className="px-2 py-0.5 rounded text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                    title="即時當沖分析（5m）"
                  >即時</button>
                </div>
              </div>

              {(() => {
                const aiHL = rec.ai_summary?.result?.highlights;
                const hl = (aiHL && aiHL.length > 0) ? aiHL : deriveHighlightsFromInsights(rec.insights);
                if (!hl || hl.length === 0) return null;
                const source = (aiHL && aiHL.length > 0) ? 'AI' : '量化推導';
                return (
                  <div className="flex items-center flex-wrap gap-2">
                    <span className="inline-flex items-center text-xs text-gray-400" title={`來源：${source}`}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-1">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
                        <path d="M12 8.5h.01M11 11h2v6h-2z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                      亮點
                    </span>
                    {hl.map((h, i) => (
                      <Pill key={i} className="bg-purple-500/20 text-purple-300 border border-purple-400/30">{h}</Pill>
                    ))}
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><p className="text-gray-400">現價</p><p>{rec.current_price}</p></div>
                <div><p className="text-gray-400">進場區間</p><p>{rec.entry_price_range}</p></div>
                <div><p className="text-gray-400">目標價</p><p className="text-green-400">{rec.target_profit}</p></div>
                <div><p className="text-gray-400">停損點</p><p className="text-red-400">{rec.stop_loss}</p></div>
                <div><p className="text-gray-400">風險收益比</p><p>{rec.risk_reward_ratio}:1</p></div>
                <div><p className="text-gray-400">潛在報酬</p><p className="text-green-400">{rec.potential_return}</p></div>
              </div>

              {/* 核心操作建議（買點｜賣點｜提醒） */}
              {(() => {
                // parse entry range like "123.45 - 128.90"
                const rng = (rec.entry_price_range || '').split('-').map(s => s.trim());
                const eLow = rng.length === 2 ? rng[0] : null;
                const eHigh = rng.length === 2 ? rng[1] : null;
                const tgt = rec.target_profit || null;
                const stp = rec.stop_loss || null;
                const trend = rec.insights?.trend?.state || null;
                const tipText = trend ? `趨勢：${trend}` : null;
                return (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="glass-card p-3 rounded">
                      <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">🟩 買點</div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {(eLow && eHigh) ? (
                          <Pill className="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">買區 {eLow} ~ {eHigh}</Pill>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                        <Pill className="bg-secondary/60 text-foreground border border-border">靠近買區分批進場，不追高</Pill>
                      </div>
                    </div>
                    <div className="glass-card p-3 rounded">
                      <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">🟥 賣點</div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {tgt && (<Pill className="bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">目標 {tgt}</Pill>)}
                        {stp && (<Pill className="bg-rose-500/20 text-rose-300 border border-rose-400/30">停損 {stp}</Pill>)}
                        <Pill className="bg-secondary/60 text-foreground border border-border">靠近目標分批了結</Pill>
                      </div>
                    </div>
                    <div className="glass-card p-3 rounded">
                      <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">💡 提醒</div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {(() => {
                          const tips = [];
                          const ins = rec.insights || {};
                          const vol = ins.volatility || {};
                          const levels = ins.levels || {};
                          const mom = ins.momentum || {};
                          const atrp = typeof vol.atr_pct === 'number' ? vol.atr_pct * 100 : null;
                          if (tipText) tips.push(tipText);
                          if (atrp != null) {
                            if (atrp >= 3.0) tips.push('波動較大，降低部位');
                            else if (atrp <= 1.0) tips.push('波動較小，部位可酌增');
                          }
                          if (mom.rsi_state === '超買') tips.push('RSI 超買，留意短線回檔');
                          if (mom.rsi_state === '超賣') tips.push('RSI 超賣，反彈可觀望');
                          if (mom.macd_state === '黃金交叉') tips.push('MACD 轉強，順勢操作');
                          if (typeof levels.distance_to_resistance_pct === 'number' && levels.distance_to_resistance_pct <= 2.0) tips.push('接近壓力，逢高了結');
                          if (typeof levels.distance_to_support_pct === 'number' && levels.distance_to_support_pct <= 2.0) tips.push('靠近支撐，逢低分批');
                          tips.push('單筆風險控制於 1%~2%');
                          return (tips.slice(0, 3).map((t, i) => (
                            <Pill key={i} className="bg-secondary/60 text-foreground border border-border">{t}</Pill>
                          )));
                        })()}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {rec.chart_data && rec.chart_data.length > 1 && (() => {
                const data = rec.chart_data;
                const start = data[0]?.close;
                const end = data[data.length - 1]?.close;
                const minClose = Math.min(...data.map(d => d.close));
                const maxClose = Math.max(...data.map(d => d.close));
                const changePct = (start && end) ? ((end - start) / start) * 100 : 0;
                const up = changePct >= 0;
                const strokeColor = up ? '#22c55e' : '#ef4444';
                const isPct = sparkScale === 'pct';
                const series = isPct && start
                  ? data.map(d => ({ ...d, v: ((d.close - start) / start) * 100 }))
                  : data;
                const yKey = isPct ? 'v' : 'close';
                const yMin = isPct ? Math.min(...series.map(d => d.v)) : minClose;
                const yMax = isPct ? Math.max(...series.map(d => d.v)) : maxClose;

                const ChangeBadge = () => (
                  <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${up ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30' : 'bg-rose-500/20 text-rose-300 border-rose-400/30'}`}>
                    {up ? '▲' : '▼'} {Math.abs(changePct).toFixed(1)}%
                  </span>
                );

                const CustomTooltip = ({ active, payload, label }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const val = payload[0].value;
                  const delta = isPct
                    ? val
                    : (start && typeof val === 'number') ? ((val - start) / start) * 100 : 0;
                  const pos = typeof delta === 'number' ? delta >= 0 : true;
                  const fmt = (v) => (typeof v === 'number' ? (isPct ? v.toFixed(2) + '%' : v.toFixed(2)) : '—');
                  return (
                    <div className="bg-background/95 border border-border rounded-md shadow-lg p-3 text-xs min-w-[160px]">
                      <div className="text-gray-300 mb-1">{label}</div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">{isPct ? '變化' : '收盤'}</span>
                        <span className="text-foreground font-medium">{fmt(val)}</span>
                      </div>
                      <div className={`flex items-center justify-between mt-1 ${pos ? 'text-emerald-300' : 'text-rose-300'}`}>
                        <span>Δ</span>
                        <span>{pos ? '▲' : '▼'} {typeof delta === 'number' ? Math.abs(delta).toFixed(2) : '—'}%</span>
                      </div>
                    </div>
                  );
                };

                return (
                  <div>
                    <p className="text-gray-400 text-sm mb-2 flex items-center">📈 五日走勢 <ChangeBadge /></p>
                    <ResponsiveContainer width="100%" height={160}>
                      <LineChart data={series} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                        <XAxis dataKey="date" hide />
                        <YAxis domain={isPct ? ['auto', 'auto'] : [yMin * 0.98, yMax * 1.02]} hide />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine y={isPct ? 0 : start} stroke="#94a3b8" strokeDasharray="3 3" />
                        <Line type="monotone" dataKey={yKey} stroke={strokeColor} strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                    <div className="mt-1 text-[11px] text-gray-400">
                      {isPct
                        ? `範圍 ${yMin.toFixed(1)}% ~ ${yMax.toFixed(1)}%`
                        : `範圍 ${yMin.toFixed(2)} ~ ${yMax.toFixed(2)}（${(((maxClose - minClose) / start) * 100).toFixed(1)}%）`}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-gray-300">
                      <span className="inline-flex items-center gap-1">
                        <span style={{ backgroundColor: strokeColor }} className="inline-block w-4 h-0.5 rounded" />
                        {isPct ? '變化線' : '收盤線'}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <span className="inline-block w-4 border-b border-dashed border-slate-400" />
                        基準線
                      </span>
                    </div>
                  </div>
                );
              })()}

              {/* 即時當沖結果（若有） */}
              {rec._daytrade && (
                <div className="border-t border-gray-700 pt-3">
                  <div className="flex items-center gap-2 text-xs mb-1 flex-wrap">
                    <span className={
                      `px-2 py-0.5 rounded-full border ` +
                      (rec._daytrade.decision === '買進' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30'
                       : rec._daytrade.decision === '回避' ? 'bg-rose-500/20 text-rose-300 border-rose-400/30'
                       : 'bg-amber-500/20 text-amber-300 border-amber-400/30')
                    }>
                      即時：{rec._daytrade.decision}
                    </span>
                    {rec._daytrade.interval && (
                      <span className="px-2 py-0.5 rounded-full border bg-secondary/60 text-foreground">{rec._daytrade.interval}</span>
                    )}
                    {rec._daytrade.interval_used && rec._daytrade.interval_used !== rec._daytrade.interval && (
                      <span className="px-2 py-0.5 rounded-full border bg-amber-500/20 text-amber-300 border-amber-400/30">已改用 {rec._daytrade.interval_used}</span>
                    )}
                    {rec._daytrade.data_source && (
                      <span className={`px-2 py-0.5 rounded-full border ${rec._daytrade.data_source === 'direct' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-400/30' : 'bg-secondary/60 text-foreground'}`}>
                        來源：{rec._daytrade.data_source === 'direct' ? '直接' : 'DB'}{typeof rec._daytrade.bars === 'number' ? ` · ${rec._daytrade.bars}筆` : ''}
                      </span>
                    )}
                    <span className="text-gray-400">現價</span><span className="text-foreground">{rec._daytrade.now_price?.toFixed ? rec._daytrade.now_price.toFixed(2) : rec._daytrade.now_price}</span>
                    {rec._daytrade.entry && (<><span className="text-gray-400">買</span><span className="text-foreground">{rec._daytrade.entry?.toFixed ? rec._daytrade.entry.toFixed(2) : rec._daytrade.entry}</span></>)}
                    {rec._daytrade.target && (<><span className="text-gray-400">目標</span><span className="text-green-300">{rec._daytrade.target?.toFixed ? rec._daytrade.target.toFixed(2) : rec._daytrade.target}</span></>)}
                    {rec._daytrade.stop && (<><span className="text-gray-400">停損</span><span className="text-rose-300">{rec._daytrade.stop?.toFixed ? rec._daytrade.stop.toFixed(2) : rec._daytrade.stop}</span></>)}
                  </div>
                  {rec._daytrade.signals && rec._daytrade.signals.length > 0 && (
                    <div className="flex flex-wrap gap-2 text-xs">
                      {rec._daytrade.signals.map((s, i)=>(<Pill key={i} className="bg-secondary/60 text-foreground border border-border">{s}</Pill>))}
                    </div>
                  )}
                </div>
              )}

              {rec.ai_summary && (
                <div className="border-t border-gray-700 pt-3">
                  <p className="text-gray-400 text-sm mb-2">🤖 AI 文字建議</p>
                  <AiSummary ai={rec.ai_summary} />
                </div>
              )}
            </div>
          ))}

        </div>
      ) : (
        <p className="text-gray-400 pt-4">此分類中沒有標的。</p>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-4 pt-4">
          <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-4 py-2 bg-secondary rounded-md disabled:opacity-50">上一頁</button>
          <span className="text-sm text-gray-400">第 {currentPage} 頁 / 共 {totalPages} 頁</span>
          <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-4 py-2 bg-secondary rounded-md disabled:opacity-50">下一頁</button>
        </div>
      )}
      {toast && (
        <div className="fixed bottom-4 right-4 bg-background/95 border border-border rounded-md shadow-lg px-3 py-2 text-xs text-foreground">
          {toast}
        </div>
      )}
    </div>
  );
}
