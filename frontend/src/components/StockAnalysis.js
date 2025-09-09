'use client';

import React, { useState, useEffect } from 'react';
import { apiFetch } from '../lib/api';
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';
import StockIndustryResults from './results/StockIndustryResults';
// Watchlist compact nav is embedded in header (dropdown)

const Pill = ({ children, className = '' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>{children}</span>
);

export default function StockAnalysis({ onOpenDaytrade }) {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [sparkScale, setSparkScale] = useState('pct'); // 'pct' | 'price'
  const [showBaseline, setShowBaseline] = useState(true);
  const [showDrawdown, setShowDrawdown] = useState(false);
  const [showMoreTips, setShowMoreTips] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  // Buyer-side controls
  const [lookbackDays, setLookbackDays] = useState(20);
  const [entryFrac, setEntryFrac] = useState(0.4); // 0~1
  const [targetFrac, setTargetFrac] = useState(0.1); // 0~1
  const [stopAtrMult, setStopAtrMult] = useState(1.0);
  const [stopFloorPct, setStopFloorPct] = useState(5.0);
  const [accountSize, setAccountSize] = useState('500000');
  const [riskPct, setRiskPct] = useState('1.0');
  // watchlist UI moved to global header
  const [industries, setIndustries] = useState([]);
  const [selectedIndustry, setSelectedIndustry] = useState('');
  const [indLoading, setIndLoading] = useState(false);
  const [indResults, setIndResults] = useState(null);

  // Load persisted tuning params
  useEffect(() => {
    try {
      const raw = typeof window !== 'undefined' && window.localStorage.getItem('stockAnalysis:tuning:v1');
      if (raw) {
        const s = JSON.parse(raw);
        if (s && typeof s === 'object') {
          if (s.lookbackDays != null) setLookbackDays(s.lookbackDays);
          if (s.entryFrac != null) setEntryFrac(s.entryFrac);
          if (s.targetFrac != null) setTargetFrac(s.targetFrac);
          if (s.stopAtrMult != null) setStopAtrMult(s.stopAtrMult);
          if (s.stopFloorPct != null) setStopFloorPct(s.stopFloorPct);
          if (s.accountSize != null) setAccountSize(String(s.accountSize));
          if (s.riskPct != null) setRiskPct(String(s.riskPct));
        }
      }
    } catch (_) {}
  }, []);

  // Persist tuning params on change
  useEffect(() => {
    try {
      const s = {
        lookbackDays,
        entryFrac,
        targetFrac,
        stopAtrMult,
        stopFloorPct,
        accountSize,
        riskPct,
      };
      if (typeof window !== 'undefined') window.localStorage.setItem('stockAnalysis:tuning:v1', JSON.stringify(s));
    } catch (_) {}
  }, [lookbackDays, entryFrac, targetFrac, stopAtrMult, stopFloorPct, accountSize, riskPct]);

  // watchlist data managed in global header
  // Load industries from backend (DB-driven)
  useEffect(() => {
    const loadIndustries = async () => {
      try {
        const res = await apiFetch('/industries');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const json = await res.json();
        setIndustries(json.industries || []);
      } catch (_) {}
    };
    loadIndustries();
  }, []);

  const runIndustryAnalysis = async () => {
    if (!selectedIndustry) return;
    setIndLoading(true);
    setIndResults(null);
    try {
      const res = await apiFetch('/stock/analyze_by_industry', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ industry: selectedIndustry })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      setIndResults(json);
    } catch (_) {
      // ignore
    } finally {
      setIndLoading(false);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      let t = ticker.trim();
      if (/^\d+$/.test(t) && !t.endsWith('.TW')) t = `${t}.TW`;
      const payload = {
        ticker: t.toUpperCase(),
        lookback_days: Number(lookbackDays) || 20,
        entry_frac: Number(entryFrac),
        target_frac: Number(targetFrac),
        stop_atr_mult: Number(stopAtrMult),
        stop_floor_pct: Number(stopFloorPct),
        account_size: accountSize ? Number(accountSize) : null,
        risk_pct: riskPct ? Number(riskPct) : null,
      };
      const res = await apiFetch('/stock/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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

  // Helper components (defined inside to access state/setters if needed)
  const SparkStats = ({ stats }) => {
    if (!stats) return null;
    const st = stats || {};
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
  };

  const SparkChart = ({ spark }) => {
    if (!spark || spark.length <= 1) return null;
    const s = spark;
    const start = s[0]?.close;
    const end = s[s.length - 1]?.close;
    const up = start && end ? (end >= start) : true;
    const stroke = up ? '#22c55e' : '#ef4444';
    const isPct = sparkScale === 'pct';
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

    const CustomTooltip = ({ active, payload, label }) => {
      if (!active || !payload || payload.length === 0) return null;
      const findVal = (key) => {
        const p = payload.find((it) => it.dataKey === key);
        return p ? p.value : null;
      };
      const val = showDrawdown ? findVal('dd_pct') : (isPct ? findVal('pct') : findVal('close'));
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

    return (
      <div>
        <div className="text-sm text-gray-400 mb-2 flex items-center gap-2">
          📈 近 30 日走勢（{isPct ? '%' : '價格'}）
          {(() => {
            const ddVals = s.map(d => d.dd_pct).filter(v => v != null);
            const maxDrawdown = ddVals.length ? Math.min(...ddVals) : null;
            return maxDrawdown != null ? (
              <Pill className="bg-rose-500/20 text-rose-300 border border-rose-400/30">最大回撤 {Math.abs(maxDrawdown).toFixed(1)}%</Pill>
            ) : null;
          })()}
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
            <Tooltip content={<CustomTooltip />} />
            {showBaseline && !showDrawdown && (
              <ReferenceLine y={isPct ? 0 : start} stroke="#94a3b8" strokeDasharray="3 3" />
            )}
            {!showDrawdown && hasBB && isPct && (
              <>
                <Area dataKey="bb_lower_pct" stackId="bb" stroke="none" fill="transparent" />
                <Area dataKey="bb_band_width_pct" stackId="bb" stroke="none" fill="#64748b" fillOpacity={0.2} />
                <Line type="monotone" dataKey="bb_upper_pct" stroke="#64748b" strokeDasharray="4 2" dot={false} />
                <Line type="monotone" dataKey="bb_lower_pct" stroke="#64748b" strokeDasharray="4 2" dot={false} />
              </>
            )}
            {!showDrawdown && !isPct && hasBB && (
              <>
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
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-gray-300">
          {!showDrawdown && (
            <span className="inline-flex items-center gap-1">
              <span style={{ backgroundColor: stroke }} className="inline-block w-4 h-0.5 rounded" />
              {isPct ? '變化線' : '價格線'}
            </span>
          )}
          {!showDrawdown && (
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-4 h-0.5 rounded" style={{ backgroundColor: '#60a5fa' }} />
              MA20
            </span>
          )}
          {!showDrawdown && hasBB && (
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded bg-slate-400/30 border border-slate-500/40" />
              布林帶
            </span>
          )}
          {!showDrawdown && showBaseline && (
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-4 border-b border-dashed border-slate-400" />
              基準線
            </span>
          )}
          {showDrawdown && (
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded bg-rose-500/30 border border-rose-400/30" />
              回撤
            </span>
          )}
        </div>
      </div>
    );
  };

  const SimpleChips = ({ simple, d }) => {
    if (!simple) return null;
    const buyAll = Array.isArray(simple.buy_when) ? simple.buy_when : [];
    const sellAll = Array.isArray(simple.sell_when) ? simple.sell_when : [];
    const buy = showMoreTips ? buyAll : buyAll.slice(0, 2);
    const sell = showMoreTips ? sellAll : sellAll.slice(0, 2);
    return (
      <div className="mt-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="glass-card p-3 rounded">
            <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">🟩 買點</div>
            <div className="flex flex-wrap gap-2">
              {simple.entry_range && (
                <Pill className="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">買區 {simple.entry_range}</Pill>
              )}
              {buy.length === 0 && <span className="text-xs text-gray-500">—</span>}
              {buy.map((t, i) => (
                <Pill key={i} className="bg-secondary/60 text-foreground border border-border">{t}</Pill>
              ))}
              {buyAll.length > buy.length && (
                <button type="button" onClick={()=>setShowMoreTips(true)} className="px-2 py-0.5 rounded text-xs bg-secondary/40 border border-border text-gray-300">更多</button>
              )}
            </div>
          </div>
          <div className="glass-card p-3 rounded">
            <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">🟥 賣點</div>
            <div className="flex flex-wrap gap-2">
              {d?.suggestion?.target != null && (
                <Pill className="bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">目標 {d.suggestion.target.toFixed ? d.suggestion.target.toFixed(2) : d.suggestion.target}</Pill>
              )}
              {d?.suggestion?.stop != null && (
                <Pill className="bg-rose-500/20 text-rose-300 border border-rose-400/30">停損 {d.suggestion.stop.toFixed ? d.suggestion.stop.toFixed(2) : d.suggestion.stop}</Pill>
              )}
              {sell.length === 0 && <span className="text-xs text-gray-500">—</span>}
              {sell.map((t, i) => (
                <Pill key={i} className="bg-secondary/60 text-foreground border border-border">{t}</Pill>
              ))}
              {sellAll.length > sell.length && !showMoreTips && (
                <button type="button" onClick={()=>setShowMoreTips(true)} className="px-2 py-0.5 rounded text-xs bg-secondary/40 border border-border text-gray-300">更多</button>
              )}
            </div>
          </div>
          <div className="glass-card p-3 rounded">
            <div className="flex items-center gap-2 text-gray-300 text-sm mb-2">💡 提醒</div>
            <div className="flex flex-wrap gap-2">
              {d?.suggestion?.risk_reward != null && (
                <Pill className="bg-purple-500/20 text-purple-300 border border-purple-400/30">風報比 {d.suggestion.risk_reward.toFixed ? d.suggestion.risk_reward.toFixed(2) : d.suggestion.risk_reward}</Pill>
              )}
              {d?.suggestion?.position?.shares != null && (
                <Pill className="bg-amber-500/20 text-amber-300 border border-amber-400/30">股數 {d.suggestion.position.shares}</Pill>
              )}
              {simple?.tip ? (
                <Pill className="bg-secondary/60 text-foreground border border-border">{simple.tip}</Pill>
              ) : (
                <span className="text-xs text-gray-500">—</span>
              )}
            </div>
            {showMoreTips && (buyAll.length > 2 || sellAll.length > 2) && (
              <div className="mt-2">
                <button type="button" onClick={()=>setShowMoreTips(false)} className="px-2 py-0.5 rounded text-xs bg-secondary/40 border border-border text-gray-300">收合</button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-4 rounded-lg space-y-3">
        <div className="flex items-center justify-between relative">
          <div>
            <h3 className="text-md font-semibold text-foreground">股票分析（波段/投資）</h3>
            <p className="text-xs text-gray-400">輸入代碼，並可調整下方買方參數（會自動保存）。</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={async () => {
                const t = ticker.trim().toUpperCase();
                if (!t) return;
                try {
                  const res = await apiFetch('/watchlist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker: t }),
                  });
                  if (!res.ok) throw new Error('HTTP ' + res.status);
                  setSavedMsg('已加入自選（已存到資料庫）');
                } catch (e) {
                  // 後備：仍寫入本地，以免全失敗
                  try {
                    const key = 'watchlist:v1';
                    const raw = typeof window !== 'undefined' && window.localStorage.getItem(key);
                    const list = raw ? JSON.parse(raw) : [];
                    if (!list.includes(t)) list.push(t);
                    if (typeof window !== 'undefined') window.localStorage.setItem(key, JSON.stringify(list));
                    setSavedMsg('已加入自選（離線保存）');
                  } catch (_) {}
                } finally {
                  setTimeout(()=>setSavedMsg(''), 1500);
                }
              }}
              className="px-3 py-1 rounded-md text-xs font-medium bg-secondary hover:bg-secondary/80 border border-border text-foreground"
              title="加入自選清單（儲存到資料庫，失敗則存本地）"
            >加入自選</button>
            {savedMsg && <span className="text-[11px] text-emerald-300">{savedMsg}</span>}
          </div>
        </div>
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
        {/* Buyer-side tuning controls (簡化：預設收合進階設定) */}
        <details className="rounded border border-border/60" open={false}>
          <summary className="cursor-pointer select-none px-3 py-1.5 text-xs text-gray-300">進階設定</summary>
          <div className="p-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block text-gray-400 mb-1">觀察天數（Lookback）</label>
            <input type="number" min="5" max="60" value={lookbackDays} onChange={(e)=>setLookbackDays(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" />
            <div className="text-[10px] text-gray-500 mt-1">用於找支撐/壓力（預設 20）</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">進場比例（Entry frac）</label>
            <input type="number" min="0" max="1" step="0.05" value={entryFrac} onChange={(e)=>setEntryFrac(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" />
            <div className="text-[10px] text-gray-500 mt-1">越小越貼近支撐（預設 0.4）</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">目標折扣（Target frac）</label>
            <input type="number" min="0" max="1" step="0.05" value={targetFrac} onChange={(e)=>setTargetFrac(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" />
            <div className="text-[10px] text-gray-500 mt-1">越大越保守（預設 0.1）</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">停損緩衝 ATR×</label>
            <input type="number" min="0" step="0.1" value={stopAtrMult} onChange={(e)=>setStopAtrMult(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" />
            <div className="text-[10px] text-gray-500 mt-1">ATR 倍數（預設 1.0）</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">停損下限 %</label>
            <input type="number" min="0" max="20" step="0.5" value={stopFloorPct} onChange={(e)=>setStopFloorPct(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" />
            <div className="text-[10px] text-gray-500 mt-1">至少距今價的下跌百分比（預設 5%）</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">總資金（Account）</label>
            <input type="number" min="0" step="1000" value={accountSize} onChange={(e)=>setAccountSize(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" placeholder="500000" />
            <div className="text-[10px] text-gray-500 mt-1">用於估算股數與風險金額</div>
          </div>
          <div>
            <label className="block text-gray-400 mb-1">單筆風險 %</label>
            <input type="number" min="0" max="10" step="0.1" value={riskPct} onChange={(e)=>setRiskPct(e.target.value)} className="w-full bg-secondary border border-border rounded px-2 py-1 text-right" placeholder="1.0" />
            <div className="text-[10px] text-gray-500 mt-1">建議 1% ~ 2%</div>
          </div>
          </div>
        </details>
        {error && <p className="mt-2 text-sm text-danger">Error: {error}</p>}
      </div>

      {/* Watchlist moved to top dropdown nav */}

      {/* Industry analysis */}
      <div className="glass-card p-4 rounded-lg space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-foreground">依產業分析（波段/投資）</h4>
            <p className="text-xs text-gray-400">從資料庫載入產業，逐檔執行股票分析（不含 AI）。</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <label className="inline-flex items-center gap-2">顯示
              <select className="bg-secondary border border-border rounded px-2 py-1" value={selectedIndustry} onChange={(e)=>setSelectedIndustry(e.target.value)}>
                <option value="">選擇產業</option>
                {industries.map((ind) => (<option key={ind} value={ind}>{ind}</option>))}
              </select>
            </label>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <button
            type="button"
            onClick={runIndustryAnalysis}
            disabled={!selectedIndustry || indLoading}
            className="px-3 py-1.5 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50"
          >{indLoading ? '分析中…' : '分析此產業'}</button>
          <span className="ml-4 text-gray-400">篩選</span>
          <label className="inline-flex items-center gap-1">
            <input type="checkbox" className="rounded border-border bg-background" onChange={(e)=> setIndResults(r => r ? { ...r, _filterDecision: e.target.checked ? 'buy' : 'all' } : r)} />
            只看「買進」
          </label>
          <label className="inline-flex items-center gap-1">
            RR ≥
            <input type="number" min="0" step="0.1" defaultValue={0} className="w-16 bg-secondary border border-border rounded px-2 py-1 text-right" onBlur={(e)=>{
              const v = parseFloat(e.target.value || '0');
              setIndResults(r => r ? { ...r, _minRR: isFinite(v) ? v : 0 } : r);
            }} />
          </label>
        </div>
        {indLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[...Array(4)].map((_,i)=>(
              <div key={i} className="glass-card p-4 rounded-lg animate-pulse">
                <div className="h-4 bg-secondary/60 rounded w-1/4 mb-3"></div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="h-16 bg-secondary/50 rounded"></div>
                  <div className="h-16 bg-secondary/50 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        )}
        {indResults && indResults.type === 'stock_analysis_by_industry' && !indLoading && (
          <div className="pt-3 border-t border-border">
            <StockIndustryResults
              data={indResults}
              onOpenDaytrade={onOpenDaytrade}
              onOpenStock={(t)=>{ setTicker(t); }}
              filter={{ decision: indResults._filterDecision || 'all', minRR: indResults._minRR || 0 }}
              sortBy="rr_desc"
            />
          </div>
        )}
      </div>

      {data && data.type === 'stock_analysis' && (
        <div className="glass-card p-4 rounded-lg space-y-4">
          {/* Header: Ticker + Decision */}
          <div className="flex items-center justify-between">
            <div className="text-foreground font-semibold text-lg">{data.name ? `${data.name}（${data.ticker}）` : data.ticker}</div>
            <Pill className={`border ${
              data.suggestion?.decision === '買進'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30'
                : data.suggestion?.decision === '回避'
                ? 'bg-rose-500/20 text-rose-300 border-rose-400/30'
                : 'bg-amber-500/20 text-amber-300 border-amber-400/30'
            }`}>
              建議：{data.suggestion?.decision || '觀望'}
            </Pill>
          </div>

          {/* 重點摘要 */}
          {data.suggestion && (() => {
            const s = data.suggestion;
            const entryStr = (s.entry_low != null && s.entry_high != null) ? `${s.entry_low.toFixed(2)} ~ ${s.entry_high.toFixed(2)}` : null;
            const targetStr = (s.target != null) ? s.target.toFixed(2) : null;
            const stopStr = (s.stop != null) ? s.stop.toFixed(2) : null;
            const simple = s.simple || {};
            const defaultTip = '單筆風險 1%~2%';
            const buyWhen = (simple.buy_when && simple.buy_when[0]) || null;
            const sellWhen = (simple.sell_when && simple.sell_when[0]) || null;
            const tipStrBase = simple.tip || defaultTip;

            // Parse AI summary for core ops to surface at top
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
            const aiOps = parseOps(data.ai_summary);

            const buyDisplay = entryStr || buyWhen || (aiOps?.buy ? `AI：${aiOps.buy}` : null) || '—';
            const sellDisplay = targetStr ? `目標 ${targetStr}` : (sellWhen || (aiOps?.sell ? `AI：${aiOps.sell}` : null) || '—');
            const stopDisplay = stopStr || (aiOps?.stop ? `AI：${aiOps.stop}` : null) || null;
            const tipDisplay = aiOps?.risk ? `${tipStrBase}｜${aiOps.risk}` : tipStrBase;

            return (
              <div className="rounded-md bg-secondary/60 border border-border p-3 mb-3">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                    s.decision === '買進' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30'
                    : s.decision === '回避' ? 'bg-rose-500/20 text-rose-300 border-rose-400/30'
                    : 'bg-amber-500/20 text-amber-300 border-amber-400/30'
                  }`}>
                    建議：{s.decision}
                  </span>
                  {data.ai_summary && (
                    <span className="text-[10px] text-gray-400">（含 AI 建議）</span>
                  )}
                  <span className="ml-auto"></span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="text-[11px] px-2 py-1 rounded bg-secondary hover:bg-secondary/80 border border-border text-foreground"
                      onClick={() => { const t = (data.ticker||'').toString(); if (t && onOpenDaytrade) onOpenDaytrade(t); }}
                    >切到當沖</button>
                    <button
                      type="button"
                      className="text-[11px] px-2 py-1 rounded bg-secondary hover:bg-secondary/80 border border-border text-foreground"
                      onClick={async ()=>{
                        try {
                          const t = (data.ticker||'').toString();
                          if (!t) return;
                          const res = await apiFetch('/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: t }) });
                          // ignore status toast here; header已有提示邏輯
                        } catch (_) {}
                      }}
                    >加入自選</button>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                  <div className="glass-card p-3 rounded">
                    <div className="text-gray-400 text-xs">買點</div>
                    <div className="text-foreground mt-1">{buyDisplay}</div>
                  </div>
                  <div className="glass-card p-3 rounded">
                    <div className="text-gray-400 text-xs">賣點</div>
                    <div className="text-foreground mt-1">
                      {sellDisplay}
                      {stopDisplay && <span className="ml-2 text-rose-300">{stopDisplay.startsWith('AI：') ? stopDisplay : `停損 ${stopDisplay}`}</span>}
                    </div>
                  </div>
                  <div className="glass-card p-3 rounded">
                    <div className="text-gray-400 text-xs">提醒</div>
                    <div className="text-foreground mt-1">{tipDisplay}</div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Key Numbers: Risk/Position */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="風險報酬比" value={data.suggestion?.risk_reward != null ? data.suggestion.risk_reward.toFixed(2) : '—'} />
            <Metric label="股數" value={data.suggestion?.position?.shares != null ? data.suggestion.position.shares : '—'} />
          </div>

          {/* Compact summary from spark_stats */}
          {data.spark_stats && <SparkStats stats={data.spark_stats} />}

          {/* Sparkline (30D) with switchable scale, MA20 overlay, BB shading, and drawdown */}
          {data.spark && data.spark.length > 1 && <SparkChart spark={data.spark} />}

          {/* 下方的重複建議與 AI 摘要移除，專注頂部重點 */}
        </div>
      )}
    </div>
  );
}
