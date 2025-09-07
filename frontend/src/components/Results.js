'use client';

import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer
} from 'recharts';

const StatCard = ({ label, value, icon }) => (
  <div className="glass-card p-4 rounded-lg">
    <div className="flex items-center">
      <div className="flex-shrink-0 bg-secondary rounded-md p-3">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="ml-4">
        <p className="text-sm font-medium text-gray-400 truncate">{label}</p>
        <p className="text-lg font-semibold text-foreground">{value}</p>
      </div>
    </div>
  </div>
);

const renderBacktestResults = (results) => (
  <div className="space-y-6">
    <h3 className="text-lg font-semibold text-foreground">回測結果: {results.symbol}</h3>
    <p className="text-sm text-gray-400">{results.period}</p>
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard label="總回報" value={`${results.totalReturn?.toFixed(2) ?? 'N/A'}%`} icon="💰" />
      <StatCard label="勝率" value={`${results.winRate?.toFixed(2) ?? 'N/A'}%`} icon="🎯" />
      <StatCard label="夏普比率" value={results.sharpeRatio?.toFixed(2) ?? 'N/A'} icon="📈" />
      <StatCard label="最大回撤" value={`${results.maxDrawdown?.toFixed(2) ?? 'N/A'}%`} icon="📉" />
      <StatCard label="交易次數" value={results.trades} icon="🔄" />
      <StatCard label="獲利交易" value={results.profitableTrades} icon="👍" />
    </div>
  </div>
);

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];



const getRatingClass = (rating) => {
  switch (rating) {
    case '強烈推薦': return 'bg-green-500/20 text-green-400';
    case '推薦': return 'bg-blue-500/20 text-blue-400';
    case '謹慎推薦': return 'bg-yellow-500/20 text-yellow-400';
    case '不推薦': return 'bg-red-500/20 text-red-400';
    default: return 'bg-gray-500/20 text-gray-400';
  }
};

// Helpers for AI summary styling
const getActionClass = (action) => {
  switch (action) {
    case '買進區間': return 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30';
    case '觀望': return 'bg-amber-500/20 text-amber-300 border border-amber-400/30';
    case '回避': return 'bg-rose-500/20 text-rose-300 border border-rose-400/30';
    case '逢高了結': return 'bg-indigo-500/20 text-indigo-300 border border-indigo-400/30';
    default: return 'bg-gray-600/20 text-gray-300 border border-gray-400/20';
  }
};

const Pill = ({ children, className = '' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>{children}</span>
);

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
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">
          {summary}
        </p>
        <div className="mt-3 text-[11px] text-gray-400">
          <span className="mr-2">🤖 由 AI 生成</span>
          {ai.model && <span>模型: {ai.model}</span>}
        </div>
      </div>
    );
  }

  return <div className="text-sm text-gray-400">AI 建議不可用</div>;
};



const RecommendationResults = ({ results }) => {
  const [activeTab, setActiveTab] = useState('recommended');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  const Insights = ({ results }) => {
  const insights = results.insights;
  const recommendations = results.recommendations;
  if (!insights) return null;

  const industryData = Object.entries(insights.industry_distribution || {})
    .map(([name, value]) => ({ name, value }));

  // 計算平均收盤價趨勢
  const lineChartData = [];
  if (recommendations && recommendations.length > 0) {
    const dates = recommendations[0].chart_data?.map(d => d.date) || [];
    dates.forEach((date, idx) => {
      let sum = 0, count = 0;
      recommendations.forEach(rec => {
        if (rec.chart_data && rec.chart_data[idx] && rec.chart_data[idx].date === date) {
          sum += rec.chart_data[idx].close;
          count++;
        }
      });
      if (count > 0) {
        lineChartData.push({ date, averageClose: sum / count });
      }
    });
  }


    const generateInsightsText = () => {
      const riskReward = insights.avg_risk_reward;
      let riskRewardInsight = '';
      if (riskReward >= 2.0) {
        riskRewardInsight = '您的平均風險報酬比高於2.0，這表示您的推薦標的在承擔每單位風險時，預期能獲得兩倍以上的報酬，顯示出較高的潛在獲利能力。';
      } else if (riskReward >= 1.0) {
        riskRewardInsight = '您的平均風險報酬比介於1.0到2.0之間，這是一個相對平衡的區間，表示您的推薦標的在風險與報酬之間取得了合理的平衡。';
      } else {
        riskRewardInsight = '您的平均風險報酬比低於1.0，這可能意味著您的推薦標的在承擔每單位風險時，預期報酬相對較低，建議您重新評估風險偏好或尋找更高潛力的標的。';
      }

      const uniqueIndustries = industryData.length;
      let diversificationInsight = '';
      if (uniqueIndustries <= 2) {
        diversificationInsight = `您的投資組合目前集中在 ${uniqueIndustries} 個產業，這可能導致較高的產業特定風險。建議考慮增加不同產業的配置以分散風險。`;
      } else if (uniqueIndustries <= 5) {
        diversificationInsight = `您的投資組合分佈於 ${uniqueIndustries} 個產業，具備一定的分散性。您可以進一步評估各產業的權重，確保沒有過度集中於單一產業。`;
      } else {
        diversificationInsight = `您的投資組合涵蓋了 ${uniqueIndustries} 個產業，顯示出良好的多元化。這有助於降低單一產業波動對整體組合的影響。`;
      }

      // Check for dominance by a single industry
      if (industryData.length > 0) {
        const sortedIndustries = [...industryData].sort((a, b) => b.value - a.value);
        const topIndustry = sortedIndustries[0];
        const topIndustryPercentage = (topIndustry.value / industryData.reduce((sum, item) => sum + item.value, 0)) * 100;
        if (topIndustryPercentage > 70 && industryData.length > 1) {
          diversificationInsight += ` 儘管產業數量較多，但有約 ${topIndustryPercentage.toFixed(0)}% 的資金集中在 ${topIndustry.name}，這仍可能存在集中風險。`;
        }
      }

      return (
        <>
          <p className="text-sm text-gray-300">{riskRewardInsight}</p>
          <p className="text-sm text-gray-300">{diversificationInsight}</p>
          <p className="text-sm text-gray-300 mt-2">
            **建議:** 根據上述洞察，您可以考慮調整投資策略，例如：深入研究特定產業、重新平衡各產業權重，或探索新的高潛力標的。
          </p>
        </>
      );
    };

    return (
      <div className="glass-card p-6 rounded-lg space-y-4 mt-6">
        <h3 className="text-lg font-semibold text-foreground">投資組合洞察</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={industryData} dataKey="value" outerRadius={80} label>
                {industryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-col justify-center space-y-2">
            <p className="text-sm text-gray-400">平均風報比</p>
            <p className="text-xl font-bold text-foreground">{insights.avg_risk_reward.toFixed(2)} : 1</p>
            <p className="text-sm text-gray-400">推薦標的數量: {insights.count}</p>
          </div>
        </div>

        {/* Line Chart */}
        {lineChartData.length > 0 && (
          <div className="mt-6">
            <h4 className="text-md font-semibold text-foreground mb-2">推薦標的平均收盤價趨勢</h4>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={lineChartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#999" />
                <YAxis stroke="#999" />
                <Tooltip />
                <Line type="monotone" dataKey="averageClose" stroke="#8884d8" activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="mt-4 space-y-2">
          {generateInsightsText()}
        </div>
      </div>
    );
  };

  const { recommended, notRecommended } = useMemo(() => {
    const recommended = [];
    const notRecommended = [];
    (results.recommendations || []).forEach(rec => {
      if (rec.rating === '不推薦') notRecommended.push(rec);
      else recommended.push(rec);
    });
    return { recommended, notRecommended };
  }, [results.recommendations]);

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

      

      {results.insights && <Insights results={results} />}

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
    {/* 股票基本資訊 */}
    <div className="flex justify-between items-center">
      <div>
        <h4 className="font-bold text-lg text-foreground">{rec.name}</h4>
        <p className="text-sm text-gray-400">{rec.ticker}</p>
      </div>
      <div className="flex items-center gap-2">
        {/* 系統評等 */}
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRatingClass(rec.rating)}`}>
          系統: {rec.rating}
        </span>
        {/* AI 評等（若有） */}
        {rec.ai_summary?.result?.ai_rating && (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-500/20 text-purple-300">
            AI: {rec.ai_summary.result.ai_rating}
          </span>
        )}
      </div>
    </div>

    {/* 指標數據 */}
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
      <div><p className="text-gray-400">現價</p><p>{rec.current_price}</p></div>
      <div><p className="text-gray-400">進場區間</p><p>{rec.entry_price_range}</p></div>
      <div><p className="text-gray-400">目標價</p><p className="text-green-400">{rec.target_profit}</p></div>
      <div><p className="text-gray-400">停損點</p><p className="text-red-400">{rec.stop_loss}</p></div>
      <div><p className="text-gray-400">風險收益比</p><p>{rec.risk_reward_ratio}:1</p></div>
      <div><p className="text-gray-400">潛在報酬</p><p className="text-green-400">{rec.potential_return}</p></div>
    </div>

    {/* 新增的 5日走勢圖 */}
    {rec.chart_data && (
      <div>
        <p className="text-gray-400 text-sm mb-2">📈 五日走勢</p>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={rec.chart_data}>
            <XAxis dataKey="date" hide />
            <YAxis domain={['auto', 'auto']} hide />
            <Tooltip />
            <Line type="monotone" dataKey="close" stroke="#4F46E5" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )}

    {/* 新增的 技術分析建議 */}
    {rec.ta_signals && rec.ta_signals.length > 0 && (
      <div>
        <p className="text-gray-400 text-sm mb-2">📝 技術分析建議</p>
        <ul className="list-disc list-inside text-sm text-foreground">
          {rec.ta_signals.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      </div>
    )}

    {/* AI 文字建議 */}
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
};

export default function Results({ data }) {
  if (!data) return null;

  const AiSingleAnalysis = ({ payload }) => {
    if (!payload) return null;
    const ai = payload.ai_insights || {};
    const ticker = payload.ticker;
    const summary = payload.summary ?? ai.summary;
    const model = payload.model ?? ai.model;
    const error = payload.error ?? ai.error;
    const qi = payload.insights || null; // quantitative insights

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
  };

  return (
    <div className="w-full space-y-6">
      {data.type === 'backtest' && renderBacktestResults(data)}
      {data.type === 'recommendation' && <RecommendationResults results={data} />}
      {data.type === 'ai_recommendation' && <AiSingleAnalysis payload={data} />}
      
    </div>
  );
}
