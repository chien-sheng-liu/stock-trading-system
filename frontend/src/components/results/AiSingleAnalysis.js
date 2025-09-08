'use client';

import React from 'react';

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

export default function AiSingleAnalysis({ payload }) {
  if (!payload) return null;
  const ai = payload.ai_insights || {};
  const ticker = payload.ticker;
  const summary = payload.summary ?? ai.summary;
  const model = payload.model ?? ai.model;
  const error = payload.error ?? ai.error;
  const qi = payload.insights || null;

  const fmt = (v, d = 2, suffix = '') => (v === null || v === undefined) ? '—' : `${Number(v).toFixed(d)}${suffix}`;
  const pct = (v) => (v === null || v === undefined) ? '—' : `${Number(v).toFixed(1)}%`;

  return (
    <div className="glass-card p-6 rounded-lg space-y-3">
      <h3 className="text-lg font-semibold text-foreground">AI 推薦</h3>
      <p className="text-sm text-gray-400">{ticker}</p>
      {error ? (
        <div className="bg-rose-900/20 border border-rose-700/40 rounded-md p-3 text-sm text-rose-300">AI 錯誤：{String(error)}</div>
      ) : (
        <>
          {summary && (
            <div className="rounded-md bg-purple-950/30 border border-purple-700/30 p-3">
              <p className="text-sm text-foreground leading-relaxed">{summary}</p>
            </div>
          )}
          <div className="text-[11px] text-gray-400">🤖 由 AI 生成 {model ? `（模型: ${model}）` : ''}</div>

          {(() => {
            const aiHL = ai?.result?.highlights;
            const hl = (aiHL && aiHL.length > 0) ? aiHL : deriveHighlightsFromInsights(qi);
            if (!hl || hl.length === 0) return null;
            const source = (aiHL && aiHL.length > 0) ? 'AI' : '量化推導';
            return (
              <div className="flex items-center flex-wrap gap-2 mt-2">
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

          {qi && !qi.error && (
            <div className="mt-4 space-y-3">
              <h4 className="text-sm font-semibold text-foreground">量化洞察</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">趨勢</div>
                  <div className="text-foreground mt-1">{qi.trend?.state || '—'}</div>
                  <div className="text-xs text-gray-400 mt-1">MA5 {fmt(qi.trend?.ma5)} / MA20 {fmt(qi.trend?.ma20)} / MA60 {fmt(qi.trend?.ma60)}</div>
                </div>
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">動能</div>
                  <div className="text-foreground mt-1">RSI {fmt(qi.momentum?.rsi)}（{qi.momentum?.rsi_state || '—'}）</div>
                  <div className="text-xs text-gray-400 mt-1">MACD {fmt(qi.momentum?.macd)} / Signal {fmt(qi.momentum?.macd_signal)}（{qi.momentum?.macd_state || '—'}）</div>
                </div>
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">波動</div>
                  <div className="text-foreground mt-1">{qi.volatility?.label || '—'}</div>
                  <div className="text-xs text-gray-400 mt-1">ATR {fmt(qi.volatility?.atr)}（{pct(qi.volatility?.atr_pct * 100)}）</div>
                </div>
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">量能</div>
                  <div className="text-foreground mt-1">{qi.volume?.state || '—'}</div>
                  <div className="text-xs text-gray-400 mt-1">當日 {fmt(qi.volume?.current, 0)} / 均量20 {fmt(qi.volume?.avg20, 0)}（{fmt(qi.volume?.ratio, 2, 'x')}）</div>
                </div>
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">支撐 / 壓力</div>
                  <div className="text-foreground mt-1">{fmt(qi.levels?.support)} / {fmt(qi.levels?.resistance)}</div>
                  <div className="text-xs text-gray-400 mt-1">距支撐 {pct(qi.levels?.distance_to_support_pct)}，距壓力 {pct(qi.levels?.distance_to_resistance_pct)}</div>
                </div>
                <div className="glass-card p-3 rounded">
                  <div className="text-gray-400">表現</div>
                  <div className="text-foreground mt-1">5日 {pct(qi.performance?.ret_5d_pct)}，20日 {pct(qi.performance?.ret_20d_pct)}，60日 {pct(qi.performance?.ret_60d_pct)}</div>
                  <div className="text-xs text-gray-400 mt-1">距近高 {pct(qi.range_position?.from_high_pct)}；距近低 {pct(qi.range_position?.from_low_pct)}</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

