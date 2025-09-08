'use client';

import React, { useState } from 'react';
import { apiFetch } from '../lib/api';
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';

const Pill = ({ children, className = '' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>{children}</span>
);

export default function StockAnalysis() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [sparkScale, setSparkScale] = useState('pct'); // 'pct' | 'price'
  const [showBaseline, setShowBaseline] = useState(true);
  const [showDrawdown, setShowDrawdown] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      let t = ticker.trim();
      if (/^\d+$/.test(t) && !t.endsWith('.TW')) t = `${t}.TW`;
      const res = await apiFetch('/stock/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: t.toUpperCase() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const Metric = ({ label, value }) => (
    <div className="glass-card p-3 rounded">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-foreground mt-1 text-sm">{value ?? '—'}</div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="glass-card p-4 rounded-lg">
        <h3 className="text-md font-semibold text-foreground mb-2">股票分析（波段/投資）</h3>
        <form onSubmit={onSubmit} className="flex gap-2">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="flex-1 bg-secondary border border-border rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-primary focus:border-primary"
            placeholder="輸入代碼，例如：2330 或 2317.TW"
          />
          <button type="submit" disabled={loading || !ticker.trim()} className="px-4 py-2 rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50">
            {loading ? '分析中...' : '分析'}
          </button>
        </form>
        {error && <p className="mt-2 text-sm text-danger">Error: {error}</p>}
      </div>

      {data && data.type === 'stock_analysis' && (
        <div className="glass-card p-4 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-foreground font-semibold">{data.ticker}</div>
            <Pill className="bg-secondary/70 text-foreground border border-border">波段/長短混合</Pill>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Metric label="ATR%" value={data.metrics?.atr_pct != null ? `${data.metrics.atr_pct.toFixed(1)}%` : '—'} />
            <Metric label="趨勢" value={data.metrics?.trend || '—'} />
            <Metric label="距52週高" value={data.metrics?.from_52w_high_pct != null ? `${data.metrics.from_52w_high_pct.toFixed(1)}%` : '—'} />
            <Metric label="距52週低" value={data.metrics?.from_52w_low_pct != null ? `${data.metrics.from_52w_low_pct.toFixed(1)}%` : '—'} />
            <Metric label="1個月報酬" value={data.metrics?.ret_1m_pct != null ? `${data.metrics.ret_1m_pct.toFixed(1)}%` : '—'} />
            <Metric label="3個月報酬" value={data.metrics?.ret_3m_pct != null ? `${data.metrics.ret_3m_pct.toFixed(1)}%` : '—'} />
            <Metric label="6個月報酬" value={data.metrics?.ret_6m_pct != null ? `${data.metrics.ret_6m_pct.toFixed(1)}%` : '—'} />
          </div>

          {/* Compact summary from spark_stats */}
          {data.spark_stats && (
            (() => {
              const st = data.spark_stats || {};
              const change = typeof st.change_pct === 'number' ? st.change_pct : null;
              const rmin = typeof st.range_min === 'number' ? st.range_min : null;
              const rmax = typeof st.range_max === 'number' ? st.range_max : null;
              const slope = typeof st.trend_slope_pct_per_day === 'number' ? st.trend_slope_pct_per_day : null;

              const fmtPct = (v) => (v == null ? '—' : `${v.toFixed(2)}%`);
              const fmtPrice = (v) => (v == null ? '—' : `${v.toFixed(2)}`);

              const pos = (v) => v != null && v > 0;
              const neg = (v) => v != null && v < 0;

              const strongThreshold = 0.1; // %/day threshold for stronger slope styling
              const badgeClass = (v, isSlope = false) => {
                const abs = v != null ? Math.abs(v) : 0;
                const strong = isSlope && abs > strongThreshold;
                if (pos(v)) return strong ? 'bg-emerald-600/30 text-emerald-200 border-emerald-400' : 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30';
                if (neg(v)) return strong ? 'bg-rose-600/30 text-rose-200 border-rose-400' : 'bg-rose-500/20 text-rose-300 border-rose-400/30';
                return 'bg-secondary/70 text-foreground border-border';
              };

              return (
                <div className="flex flex-wrap items-center gap-2">
                  <Pill className={`${badgeClass(change)} border`}>
                    區間變化 {change != null ? (change >= 0 ? '▲' : '▼') : ''} {fmtPct(Math.abs(change ?? NaN))}
                  </Pill>
                  <Pill className="bg-secondary/70 text-foreground border border-border">
                    價格範圍 {fmtPrice(rmin)} ~ {fmtPrice(rmax)}
                  </Pill>
                  <Pill className={`${badgeClass(slope, true)} border`}>
                    趨勢斜率 {slope != null ? (slope >= 0 ? '↗' : '↘') : ''} {slope != null ? `${Math.abs(slope).toFixed(2)}%/日` : '—'}
                    <span
                      className="ml-1 text-xs text-gray-400 inline-flex items-center"
                      title="以近 30 日百分比變化序列做最小平方法線性擬合所得的斜率，單位為每日日均變動（%/日）。"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
                        <path d="M12 8.5h.01M11 11h2v6h-2z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                    </span>
                  </Pill>
                </div>
              );
            })()
          )}

          {/* Sparkline (30D) with switchable scale, MA20 overlay, BB shading, and drawdown */}
          {data.spark && data.spark.length > 1 && (() => {
            const s = data.spark;
            const start = s[0]?.close;
            const end = s[s.length - 1]?.close;
            const up = start && end ? (end >= start) : true;
            const stroke = up ? '#22c55e' : '#ef4444';

            const isPct = sparkScale === 'pct';
            // Build series based on selected scale
            const series = s.map(d => {
              const pct = d.pct != null ? d.pct : (start ? ((d.close - start) / start) * 100 : null);
              const ma20_pct = (d.ma20 != null && start) ? ((d.ma20 - start) / start) * 100 : null;
              const bb_upper_pct = (d.bb_upper != null && start) ? ((d.bb_upper - start) / start) * 100 : null;
              const bb_lower_pct = (d.bb_lower != null && start) ? ((d.bb_lower - start) / start) * 100 : null;
              return {
                ...d,
                pct,
                ma20_pct,
                bb_upper_pct,
                bb_lower_pct,
                bb_band_width_pct: (bb_upper_pct != null && bb_lower_pct != null) ? (bb_upper_pct - bb_lower_pct) : null,
              };
            });
            const hasBB = isPct
              ? series.some(d => d.bb_upper_pct != null && d.bb_lower_pct != null)
              : series.some(d => d.bb_upper != null && d.bb_lower != null);
            const yVals = (isPct ? series.map(d => d.pct) : series.map(d => d.close)).filter(v => v != null);
            const yMin = yVals.length ? Math.min(...yVals) : 0;
            const yMax = yVals.length ? Math.max(...yVals) : 0;

            // Max drawdown within window
            const ddVals = s.map(d => d.dd_pct).filter(v => v != null);
            const maxDrawdown = ddVals.length ? Math.min(...ddVals) : null;
            return (
              <div>
                <div className="text-sm text-gray-400 mb-2 flex items-center gap-2">
                  📈 近 30 日走勢（{isPct ? '%' : '價格'}）
                  {maxDrawdown != null && (
                    <Pill className="bg-rose-500/20 text-rose-300 border border-rose-400/30">最大回撤 {Math.abs(maxDrawdown).toFixed(1)}%</Pill>
                  )}
                  <span className="ml-auto inline-flex items-center gap-2">
                    <span>圖表</span>
                    <select className="bg-secondary border border-border rounded px-2 py-1 text-xs" value={sparkScale} onChange={(e) => setSparkScale(e.target.value)}>
                      <option value="pct">百分比</option>
                      <option value="price">價格</option>
                    </select>
                    <label className="inline-flex items-center gap-1">
                      <input type="checkbox" className="rounded border-border bg-background" checked={showDrawdown} onChange={(e) => setShowDrawdown(e.target.checked)} />
                      回撤
                    </label>
                    <label className="inline-flex items-center gap-1">
                      <input type="checkbox" className="rounded border-border bg-background" checked={showBaseline} onChange={(e) => setShowBaseline(e.target.checked)} />
                      基準線
                    </label>
                  </span>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <ComposedChart data={series} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <XAxis dataKey="date" hide />
                    <YAxis domain={showDrawdown ? ['auto', 0] : ['auto', 'auto']} hide />
                    {(() => {
                      const CustomTooltip = ({ active, payload, label }) => {
                        if (!active || !payload || payload.length === 0) return null;
                        // Determine primary value by mode
                        const findVal = (key) => {
                          const p = payload.find((it) => it.dataKey === key);
                          return p ? p.value : null;
                        };
                        const val = showDrawdown
                          ? findVal('dd_pct')
                          : (isPct ? findVal('pct') : findVal('close'));
                        const ma = !showDrawdown ? (isPct ? findVal('ma20_pct') : findVal('ma20')) : null;
                        const bbU = !showDrawdown ? (isPct ? findVal('bb_upper_pct') : findVal('bb_upper')) : null;
                        const bbL = !showDrawdown ? (isPct ? findVal('bb_lower_pct') : findVal('bb_lower')) : null;
                        const fmt = (v) => (typeof v === 'number' ? (isPct || showDrawdown ? v.toFixed(2) + '%' : v.toFixed(2)) : '—');

                        return (
                          <div className="bg-background/95 border border-border rounded-md shadow-lg p-3 text-xs min-w-[160px]">
                            <div className="text-gray-300 mb-1">{label}</div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-400">{showDrawdown ? '回撤' : (isPct ? '變化' : '收盤')}</span>
                              <span className="text-foreground font-medium">{fmt(val)}</span>
                            </div>
                            {!showDrawdown && (
                              <>
                                <div className="flex items-center justify-between mt-1">
                                  <span className="text-gray-400">MA20</span>
                                  <span className="text-foreground">{fmt(ma)}</span>
                                </div>
                                {(bbU != null || bbL != null) && (
                                  <div className="flex items-center justify-between mt-1">
                                    <span className="text-gray-400">布林上/下</span>
                                    <span className="text-foreground">{fmt(bbU)} / {fmt(bbL)}</span>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        );
                      };
                      return <Tooltip content={<CustomTooltip />} />;
                    })()}
                    {showBaseline && !showDrawdown && (
                      <ReferenceLine y={isPct ? 0 : start} stroke="#94a3b8" strokeDasharray="3 3" />
                    )}
                    {!showDrawdown && hasBB && isPct && (
                      <>
                        {/* BB shading via stacked areas: lower (transparent) + width (filled) */}
                        <Area dataKey="bb_lower_pct" stackId="bb" stroke="none" fill="transparent" />
                        <Area dataKey="bb_band_width_pct" stackId="bb" stroke="none" fill="#64748b" fillOpacity={0.2} />
                        <Line type="monotone" dataKey="bb_upper_pct" stroke="#64748b" strokeDasharray="4 2" dot={false} />
                        <Line type="monotone" dataKey="bb_lower_pct" stroke="#64748b" strokeDasharray="4 2" dot={false} />
                      </>
                    )}
                    {!showDrawdown && !isPct && hasBB && (
                      <>
                        {/* For price mode, simple band lines */}
                        <Line type="monotone" dataKey="bb_upper" stroke="#64748b" strokeDasharray="4 2" dot={false} />
                        <Line type="monotone" dataKey="bb_lower" stroke="#64748b" strokeDasharray="4 2" dot={false} />
                      </>
                    )}
                    {!showDrawdown && (
                      <>
                        <Line type="monotone" dataKey={isPct ? 'ma20_pct' : 'ma20'} stroke="#60a5fa" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey={isPct ? 'pct' : 'close'} stroke={stroke} strokeWidth={2} dot={false} />
                      </>
                    )}
                    {showDrawdown && (
                      <>
                        <Area type="monotone" dataKey="dd_pct" stroke="#ef4444" fill="#ef4444" fillOpacity={0.25} />
                        <Line type="monotone" dataKey="dd_pct" stroke="#ef4444" strokeWidth={2} dot={false} />
                      </>
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            );
          })()}

          {/* AI summary */}
          {data.ai_summary && (
            <div className="rounded-md bg-purple-950/30 border border-purple-700/30 p-3">
              <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{data.ai_summary}</p>
              <div className="text-[11px] text-gray-400 mt-1">🤖 由 AI 生成</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
