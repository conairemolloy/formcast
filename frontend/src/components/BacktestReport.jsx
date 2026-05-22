import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, ReferenceLine,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts'

const LEAGUE_COLORS = {
  EPL:        '#10b981',
  LaLiga:     '#3b82f6',
  Bundesliga: '#f59e0b',
  SerieA:     '#8b5cf6',
  Ligue1:     '#ef4444',
}

const MODEL_COMPARISON = [
  { model: 'Ensemble v2',   hitRate: 49.35, brier: 0.177, predictions: 10099 },
  { model: 'XGBoost',       hitRate: 49.07, brier: 0.178, predictions: 10099 },
  { model: 'Elo (baseline)',hitRate: 49.05, brier: 0.162, predictions: 10099 },
  { model: 'Glicko-2',      hitRate: 47.55, brier: 0.174, predictions: 10099 },
  { model: 'Dixon-Coles',   hitRate: 46.95, brier: 0.191, predictions: 10099 },
]

const BEST_HIT_RATE = Math.max(...MODEL_COMPARISON.map(m => m.hitRate))
const BEST_BRIER    = Math.min(...MODEL_COMPARISON.map(m => m.brier))

function StatCard({ label, value, color, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  )
}

const BarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
      <p className="text-gray-300 font-medium">{label}</p>
      <p className="text-emerald-400">{(payload[0].value * 100).toFixed(1)}% hit rate</p>
    </div>
  )
}

const CalibTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm space-y-0.5">
      <p className="text-gray-400 font-medium">{d.bin_label}</p>
      <p className="text-emerald-400">Actual: {d.model?.toFixed(1)}%</p>
      <p className="text-gray-500">Expected: {d.perfect?.toFixed(1)}%</p>
      <p className="text-gray-600">{d.count?.toLocaleString()} predictions</p>
    </div>
  )
}

const PnlTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm space-y-0.5">
      <p className="text-gray-400">Match {d.match_number}</p>
      <p className={d.cumulative_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
        £{d.cumulative_pnl >= 0 ? '+' : ''}{d.cumulative_pnl.toFixed(2)}
      </p>
    </div>
  )
}

export default function BacktestReport() {
  const [data, setData]           = useState(null)
  const [calibData, setCalibData] = useState(null)
  const [pnlData, setPnlData]     = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  useEffect(() => {
    Promise.all([
      api.get('/api/backtest'),
      api.get('/api/backtest/calibration'),
      api.get('/api/backtest/pnl'),
    ])
      .then(([backtestRes, calibRes, pnlRes]) => {
        setData(backtestRes.data.data)
        setCalibData(calibRes.data.data)
        setPnlData(pnlRes.data.data)
      })
      .catch(() => setError('Failed to load backtest data'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading backtest report…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  const leagueData = data.by_league.map(l => ({
    ...l,
    hit_rate_pct: +(l.hit_rate * 100).toFixed(1),
  }))

  const seasonData = data.by_season.map(s => ({
    ...s,
    hit_rate_pct: +(s.hit_rate * 100).toFixed(1),
  }))

  const maxCount = Math.max(...(calibData ?? []).map(d => d.count))
  const chartData = (calibData ?? []).map(d => ({
    bin_label: d.bin_label,
    x:       +(d.mean_predicted * 100).toFixed(1),
    model:   +(d.actual_rate    * 100).toFixed(1),
    perfect: +(d.mean_predicted * 100).toFixed(1),
    count:   d.count,
  }))

  const ModelDot = (props) => {
    const { cx, cy, payload } = props
    if (!payload?.count) return null
    const r = 3 + (payload.count / maxCount) * 9
    return (
      <circle
        key={`calib-dot-${payload.bin_label}`}
        cx={cx}
        cy={cy}
        r={r}
        fill="#10b981"
        fillOpacity={0.75}
        stroke="#10b981"
        strokeWidth={1}
      />
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-white">Backtest Report</h1>

      <div className="flex items-start gap-2 text-xs text-gray-500 bg-gray-900/40 border border-gray-800 rounded-lg px-3 py-2.5">
        <span className="text-blue-400 shrink-0">ℹ</span>
        <span>Walk-forward backtest evaluated on predictions from 2019 onwards. Data from 1993–2019 was used for model training and is excluded from these results to avoid lookahead bias.</span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Elo Hit Rate (non-draw)"
          value={`${(data.overall.hit_rate * 100).toFixed(1)}%`}
          color="text-emerald-400"
          sub="Binary accuracy — excludes draws"
        />
        <StatCard
          label="Brier Score"
          value={data.overall.brier_score.toFixed(4)}
          color="text-blue-400"
          sub="Lower is better"
        />
        <StatCard
          label="Total Matches"
          value={data.overall.total_matches.toLocaleString()}
          color="text-gray-300"
          sub="Evaluated predictions"
        />
      </div>

      {/* Hit rate by league */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-1">Elo Walk-Forward Hit Rate by League (non-draw matches)</h2>
        <p className="text-xs text-gray-500 mb-4">Excludes drawn matches — binary home/away prediction only</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={leagueData} barCategoryGap="30%">
            <XAxis dataKey="league" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis
              domain={[0, 100]}
              tickFormatter={v => `${v}%`}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="hit_rate_pct" radius={[4, 4, 0, 0]}>
              {leagueData.map(entry => (
                <Cell key={entry.league} fill={LEAGUE_COLORS[entry.league] ?? '#6366f1'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Brier per league table */}
        <div className="mt-4 grid grid-cols-5 gap-2">
          {leagueData.map(l => (
            <div key={l.league} className="text-center">
              <p className="text-xs text-gray-500">{l.league}</p>
              <p className="text-sm font-medium text-gray-300">{l.brier?.toFixed(4) ?? '—'}</p>
              <p className="text-xs text-gray-600">Brier</p>
            </div>
          ))}
        </div>
      </div>

      {/* Hit rate by season */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-4">Elo Walk-Forward Hit Rate by Season (non-draw matches)</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={seasonData} barCategoryGap="30%">
            <XAxis dataKey="season" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis
              domain={[0, 100]}
              tickFormatter={v => `${v}%`}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="hit_rate_pct" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Calibration curve */}
      {calibData && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-1">
            Calibration Curve — Home Win Predictions
          </h2>
          <p className="text-xs text-gray-500 mb-4">
            A well-calibrated model follows the diagonal. Dot size reflects number of predictions in each bin.
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <XAxis
                dataKey="x"
                type="number"
                domain={[0, 100]}
                tickFormatter={v => `${v}%`}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={40}
                label={{ value: 'Predicted Probability', position: 'insideBottom', offset: -4, fill: '#6b7280', fontSize: 11 }}
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={v => `${v}%`}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={44}
                label={{ value: 'Actual Win Rate', angle: -90, position: 'insideLeft', offset: 10, fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip content={<CalibTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="plainline"
                wrapperStyle={{ fontSize: 12, color: '#9ca3af', paddingBottom: 8 }}
              />
              <Line
                name="Perfect"
                type="linear"
                dataKey="perfect"
                stroke="#6b7280"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                dot={false}
                activeDot={false}
              />
              <Line
                name="Model"
                type="monotone"
                dataKey="model"
                stroke="#10b981"
                strokeWidth={2}
                dot={<ModelDot />}
                activeDot={{ r: 6, fill: '#34d399', stroke: '#10b981' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Model comparison table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-1">Model Comparison</h2>
        <p className="text-xs text-gray-500 mb-1">
          Hit rates below are 3-outcome (H/D/A) on the ensemble holdout. Elo binary hit rate (non-draw only) is 68.7% — see charts above.
        </p>
        <p className="text-xs text-gray-600 mb-4">
          Evaluated on 2024–2026 holdout (10,099 matches)
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-gray-800">
              <th className="text-left pb-2 font-medium">Model</th>
              <th className="text-right pb-2 font-medium">Hit Rate</th>
              <th className="text-right pb-2 font-medium">Brier Score</th>
              <th className="text-right pb-2 font-medium">Predictions</th>
            </tr>
          </thead>
          <tbody>
            {MODEL_COMPARISON.map((row, i) => (
              <tr key={row.model} className={i < MODEL_COMPARISON.length - 1 ? 'border-b border-gray-800/50' : ''}>
                <td className="py-2.5 text-gray-300">{row.model}</td>
                <td className={`py-2.5 text-right tabular-nums font-medium ${row.hitRate === BEST_HIT_RATE ? 'text-emerald-400' : 'text-gray-400'}`}>
                  {row.hitRate.toFixed(2)}%
                </td>
                <td className={`py-2.5 text-right tabular-nums font-medium ${row.brier === BEST_BRIER ? 'text-emerald-400' : 'text-gray-400'}`}>
                  {row.brier.toFixed(3)}
                </td>
                <td className="py-2.5 text-right tabular-nums text-gray-500">
                  {row.predictions.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Flat Stake P&L */}
      {pnlData && (() => {
        const positive = pnlData.final_pnl >= 0
        const lineColor = positive ? '#10b981' : '#ef4444'
        return (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-base font-semibold text-white mb-1">Flat Stake P&amp;L Simulation</h2>
            <p className="text-xs text-gray-500 mb-4">£1 stake on model's top prediction each match</p>

            <div className="grid grid-cols-4 gap-3 mb-5">
              <StatCard
                label="Final P&L"
                value={`${positive ? '+' : ''}£${pnlData.final_pnl.toFixed(2)}`}
                color={positive ? 'text-emerald-400' : 'text-red-400'}
                sub={`on £${pnlData.total_bets.toLocaleString()} staked`}
              />
              <StatCard
                label="Total Bets"
                value={pnlData.total_bets.toLocaleString()}
                color="text-gray-300"
                sub="Flat £1 per match"
              />
              <StatCard
                label="ROI"
                value={`${pnlData.roi >= 0 ? '+' : ''}${pnlData.roi.toFixed(2)}%`}
                color={pnlData.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}
                sub="Return on investment"
              />
              <StatCard
                label="Win Rate"
                value={`${pnlData.win_rate.toFixed(1)}%`}
                color="text-blue-400"
                sub="Correct predictions"
              />
            </div>

            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={pnlData.chart} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <XAxis
                  dataKey="match_number"
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => v.toLocaleString()}
                  label={{ value: 'Match number', position: 'insideBottom', offset: -4, fill: '#6b7280', fontSize: 11 }}
                />
                <YAxis
                  tickFormatter={v => `£${v}`}
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={56}
                />
                <Tooltip content={<PnlTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)' }} />
                <ReferenceLine y={0} stroke="#4b5563" strokeDasharray="5 4" />
                <Line
                  type="monotone"
                  dataKey="cumulative_pnl"
                  stroke={lineColor}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: lineColor, stroke: lineColor }}
                />
              </LineChart>
            </ResponsiveContainer>

            <p className="mt-3 text-xs text-gray-600 text-center">
              Historical simulation only — past performance does not guarantee future results
            </p>
          </div>
        )
      })()}
    </div>
  )
}
