import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const LEAGUE_COLORS = {
  EPL:        '#10b981',
  LaLiga:     '#3b82f6',
  Bundesliga: '#f59e0b',
  SerieA:     '#8b5cf6',
  Ligue1:     '#ef4444',
}

function StatCard({ label, value, color, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
      <p className="text-gray-300 font-medium">{label}</p>
      <p className="text-emerald-400">{(payload[0].value * 100).toFixed(1)}% hit rate</p>
    </div>
  )
}

export default function BacktestReport() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    api.get('/api/backtest')
      .then(r => setData(r.data.data))
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
          label="Overall Hit Rate"
          value={`${(data.overall.hit_rate * 100).toFixed(1)}%`}
          color="text-emerald-400"
          sub="Match outcome accuracy"
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
        <h2 className="text-base font-semibold text-white mb-4">Hit Rate by League</h2>
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
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
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
        <h2 className="text-base font-semibold text-white mb-4">Hit Rate by Season</h2>
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
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="hit_rate_pct" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
