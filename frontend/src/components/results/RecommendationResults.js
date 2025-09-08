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
  if (summary) {
    return (
      <div className="bg-purple-900/20 border border-purple-700/40 rounded-md p-3">
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

export default function RecommendationResults({ results }) {
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
                  if (active && payload && payload.length) {
                    const val = payload[0].value;
                    const delta = isPct ? val : (start && typeof val === 'number') ? ((val - start) / start) * 100 : 0;
                    const pos = delta >= 0;
                    return (
                      <div className="bg-background/90 border border-border rounded p-2 text-xs">
                        <div className="text-gray-300">{label}</div>
                        <div className="text-foreground">{isPct ? '變化' : '收盤'} {Number(val).toFixed(isPct ? 1 : 2)}{isPct ? '%' : ''}</div>
                        <div className={pos ? 'text-emerald-300' : 'text-rose-300'}>{pos ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%</div>
                      </div>
                    );
                  }
                  return null;
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
                  </div>
                );
              })()}

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
    </div>
  );
}

