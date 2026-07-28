import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import Tooltip from './Tooltip'

function ProbCell({ value }) {
  const pct = (value * 100).toFixed(1)
  return (
    <span className={value >= 0.5 ? 'text-emerald-400 font-medium' : 'text-gray-400'}>
      {pct}%
    </span>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold tabular-nums text-white">{value ?? '—'}</p>
    </div>
  )
}

export default function Predictions() {
  const [data, setData]                     = useState([])
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState(null)
  const [league, setLeague]                 = useState('ALL')
  const [dateFrom, setDateFrom]             = useState('')
  const [dateTo, setDateTo]                 = useState('')
  const [correctFilter, setCorrectFilter]   = useState('ALL')
  const [sortDir, setSortDir]               = useState('desc')

  useEffect(() => {
    api.get('/api/predictions')
      .then(r => setData(r.data.data))
      .catch(() => setError('Failed to load predictions'))
      .finally(() => setLoading(false))
  }, [])

  const leagues = useMemo(() => {
    const s = new Set(data.map(d => d.league))
    return ['ALL', ...Array.from(s).sort()]
  }, [data])

  const filtered = useMemo(() => {
    let rows = data
    if (league !== 'ALL') rows = rows.filter(d => d.league === league)
    if (dateFrom) rows = rows.filter(d => d.match_date >= dateFrom)
    if (dateTo)   rows = rows.filter(d => d.match_date <= dateTo)
    if (correctFilter === 'CORRECT')   rows = rows.filter(d => d.correct === 1)
    if (correctFilter === 'INCORRECT') rows = rows.filter(d => d.correct === 0)
    return [...rows].sort((a, b) =>
      sortDir === 'desc'
        ? b.match_date.localeCompare(a.match_date)
        : a.match_date.localeCompare(b.match_date)
    )
  }, [data, league, dateFrom, dateTo, correctFilter, sortDir])

  const stats = useMemo(() => {
    const withResult = filtered.filter(d => d.correct !== null && d.correct !== undefined)
    const correct = withResult.filter(d => d.correct === 1).length
    return {
      total: filtered.length,
      correct,
      hitRate: withResult.length > 0 ? `${(correct / withResult.length * 100).toFixed(1)}%` : null,
    }
  }, [filtered])

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading predictions…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-white">Predictions</h1>

      <div className="flex items-start gap-2 text-xs text-gray-500 bg-gray-900/40 border border-gray-800 rounded-lg px-3 py-2.5">
        <span className="text-[var(--brand)] shrink-0">ℹ</span>
        <span>Predictions shown from 2019 onwards — earlier data was used to train the models.</span>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Shown"    value={stats.total} />
        <StatCard label="Correct"  value={stats.correct} />
        <StatCard label="Hit Rate" value={stats.hitRate} />
      </div>

      {/* League filter */}
      <div className="flex gap-2 flex-wrap">
        {leagues.map(l => (
          <button
            key={l}
            onClick={() => setLeague(l)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              league === l
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {/* Secondary controls */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Date range */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">From</span>
          <input
            type="date"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500 [color-scheme:dark]"
          />
          <span className="text-xs text-gray-500">To</span>
          <input
            type="date"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500 [color-scheme:dark]"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => { setDateFrom(''); setDateTo('') }}
              className="text-xs text-gray-500 hover:text-white px-1"
            >
              ✕
            </button>
          )}
        </div>

        {/* Correct / Incorrect filter */}
        <div className="flex gap-1">
          {[['ALL', 'All'], ['CORRECT', 'Correct'], ['INCORRECT', 'Incorrect']].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setCorrectFilter(val)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                correctFilter === val
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-sm text-gray-500 tabular-nums">
            Showing{' '}
            <span className="text-white font-medium">{filtered.length}</span>
            {filtered.length !== data.length && ` of ${data.length}`}
            {' '}results
          </span>
          <button
            onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
            className="px-3 py-1.5 rounded text-sm font-medium bg-gray-900 text-gray-400 border border-gray-700 hover:text-white transition-colors"
          >
            Date {sortDir === 'desc' ? '↓ Newest' : '↑ Oldest'}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Date</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">League</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Home</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Away</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">P(H)<Tooltip text="Probability of Home Win — model's predicted chance the home team wins (0–100%)" /></span>
              </th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">P(D)<Tooltip text="Probability of Draw — model's predicted chance the match ends level" /></span>
              </th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">P(A)<Tooltip text="Probability of Away Win — model's predicted chance the away team wins" /></span>
              </th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">
                <span className="inline-flex items-center justify-center">Pred<Tooltip text="Predicted Result — H=Home Win, D=Draw, A=Away Win based on highest probability" /></span>
              </th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">
                <span className="inline-flex items-center justify-center">Actual<Tooltip text="Actual Result — what really happened (H/D/A)" /></span>
              </th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">
                <span className="inline-flex items-center justify-center">✓<Tooltip text="Correct — whether the model's prediction matched the actual result" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, i) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors">
                <td className="px-4 py-2.5 text-gray-500 font-mono text-xs">{row.match_date}</td>
                <td className="px-4 py-2.5">
                  <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{row.league}</span>
                </td>
                <td className="px-4 py-2.5 text-white font-medium">{row.home_team}</td>
                <td className="px-4 py-2.5 text-white font-medium">{row.away_team}</td>
                <td className="px-4 py-2.5 text-right tabular-nums"><ProbCell value={row.p_home} /></td>
                <td className="px-4 py-2.5 text-right tabular-nums"><ProbCell value={row.p_draw} /></td>
                <td className="px-4 py-2.5 text-right tabular-nums"><ProbCell value={row.p_away} /></td>
                <td className="px-4 py-2.5 text-center">
                  <span className="font-mono font-semibold text-[var(--text-secondary)]">{row.predicted_result}</span>
                </td>
                <td className="px-4 py-2.5 text-center">
                  <span className="font-mono font-semibold text-gray-300">{row.actual_result}</span>
                </td>
                <td className="px-4 py-2.5 text-center">
                  {row.correct === 1
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-400 mx-auto" />
                    : <XCircle className="w-4 h-4 text-red-500 mx-auto" />
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
