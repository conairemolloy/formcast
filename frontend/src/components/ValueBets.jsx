import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import Tooltip from './Tooltip'

function gcd(a, b) { return b === 0 ? a : gcd(b, a % b) }

function decimalToFractional(decimal) {
  if (!decimal || decimal <= 1) return '—'
  const num = Math.round((decimal - 1) * 100)
  const den = 100
  const g = gcd(num, den)
  return `${num / g}/${den / g}`
}

function StatCard({ label, value, sub, tip }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-0.5">
        {label}{tip && <Tooltip text={tip} />}
      </p>
      <p className="text-2xl font-bold tabular-nums text-white">{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

function EdgeBadge({ edge }) {
  if (edge > 0.10)
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400">{(edge * 100).toFixed(1)}%</span>
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-500/20 text-yellow-400">{(edge * 100).toFixed(1)}%</span>
}

const OUTCOME_LABELS = { H: 'Home', D: 'Draw', A: 'Away' }
const SORT_OPTIONS = [
  { value: 'edge', label: 'Edge' },
  { value: 'ev',   label: 'EV' },
  { value: 'odds', label: 'Odds' },
  { value: 'date', label: 'Date' },
]

export default function ValueBets() {
  const [bets, setBets]         = useState([])
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [outcome, setOutcome]   = useState('ALL')
  const [wonFilter, setWonFilter] = useState('ALL')
  const [sortBy, setSortBy]     = useState('edge')
  const [minEdge, setMinEdge]   = useState(0.05)

  useEffect(() => {
    Promise.all([
      api.get('/api/value-bets?limit=200'),
      api.get('/api/value-bets/summary'),
    ])
      .then(([betsRes, sumRes]) => {
        setBets(betsRes.data.data)
        setSummary(sumRes.data.data)
      })
      .catch(() => setError('Failed to load value bets'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let rows = bets
    if (outcome !== 'ALL') rows = rows.filter(b => b.outcome === outcome)
    if (wonFilter === 'WON')  rows = rows.filter(b => b.won === 1)
    if (wonFilter === 'LOST') rows = rows.filter(b => b.won !== 1)
    rows = rows.filter(b => b.edge >= minEdge)
    return [...rows].sort((a, b) => {
      if (sortBy === 'edge') return b.edge - a.edge
      if (sortBy === 'ev')   return b.EV - a.EV
      if (sortBy === 'odds') return b.odds - a.odds
      if (sortBy === 'date') return b.match_date.localeCompare(a.match_date)
      return 0
    })
  }, [bets, outcome, wonFilter, sortBy, minEdge])

  const filteredStats = useMemo(() => {
    const withResult = filtered.filter(b => b.won !== null && b.won !== undefined)
    const won = withResult.filter(b => b.won === 1).length
    const meanEdge = filtered.length > 0
      ? filtered.reduce((s, b) => s + b.edge, 0) / filtered.length
      : null
    return {
      count: filtered.length,
      winRate: withResult.length > 0 ? (won / withResult.length * 100).toFixed(1) + '%' : null,
      meanEdge: meanEdge != null ? (meanEdge * 100).toFixed(1) + '%' : null,
    }
  }, [filtered])

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading value bets…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-white">Value Bets</h1>

      {/* Overall summary */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Total Bets" value={summary.total_bets} />
          <StatCard label="Win Rate"   value={summary.win_rate != null ? `${(summary.win_rate * 100).toFixed(1)}%` : null} />
          <StatCard label="ROI / Bet"  value={summary.roi != null ? `${summary.roi > 0 ? '+' : ''}${summary.roi.toFixed(3)}` : null} />
          <StatCard label="Mean CLV"   value={summary.mean_clv != null ? summary.mean_clv.toFixed(4) : null} sub="Closing line value" tip="Closing Line Value — how much better our odds were than the final bookmaker price before kickoff. Positive CLV is the strongest indicator of a profitable betting model." />
        </div>
      )}

      {/* Filters row */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Outcome filter */}
        <div className="flex gap-1">
          {['ALL', 'H', 'D', 'A'].map(o => (
            <button
              key={o}
              onClick={() => setOutcome(o)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                outcome === o
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
              }`}
            >
              {o === 'ALL' ? 'All' : OUTCOME_LABELS[o]}
            </button>
          ))}
        </div>

        {/* Won / Lost filter */}
        <div className="flex gap-1">
          {[['ALL', 'All'], ['WON', 'Won'], ['LOST', 'Lost']].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setWonFilter(val)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                wonFilter === val
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Sort by */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-gray-500">Sort</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
          >
            {SORT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Min edge */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 shrink-0">Min Edge</span>
        <input
          type="range"
          min={0.05}
          max={0.30}
          step={0.01}
          value={minEdge}
          onChange={e => setMinEdge(parseFloat(e.target.value))}
          className="w-40 accent-emerald-500"
        />
        <span className="text-sm font-mono text-emerald-400 w-12">{(minEdge * 100).toFixed(0)}%</span>
        <span className="ml-auto text-sm text-gray-500">
          Showing{' '}
          <span className="text-white font-medium">{filteredStats.count}</span>
          {filteredStats.count !== bets.length && ` of ${bets.length}`}
          {' '}bets
          {filteredStats.winRate && <span className="mx-2 text-gray-600">·</span>}
          {filteredStats.winRate && <span>Win rate: <span className="text-white">{filteredStats.winRate}</span></span>}
          {filteredStats.meanEdge && <span className="mx-2 text-gray-600">·</span>}
          {filteredStats.meanEdge && <span>Mean edge: <span className="text-white">{filteredStats.meanEdge}</span></span>}
        </span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Date</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Fixture</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Out</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">Model %<Tooltip text="Model Probability — the ensemble's estimated probability of this outcome" /></span>
              </th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">Odds<Tooltip text="Bookmaker Odds — decimal odds offered by the market (e.g. 2.50 = 3/2)" /></span>
              </th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">Edge<Tooltip text="Edge — difference between model probability and implied bookmaker probability. Positive edge means the model thinks this outcome is underpriced." /></span>
              </th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">
                <span className="inline-flex items-center justify-end">EV<Tooltip text="Expected Value — average profit per £1 staked if this edge is real. EV > 0 means positive expectation over many bets." /></span>
              </th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">
                <span className="inline-flex items-center justify-center">Result<Tooltip text="Whether this bet won or lost" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((b, i) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors">
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{b.match_date}</td>
                <td className="px-4 py-3 text-white">
                  <span className="font-medium">{b.home_team}</span>
                  <span className="text-gray-500 mx-1">vs</span>
                  <span className="font-medium">{b.away_team}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 text-xs font-mono">{b.outcome}</span>
                </td>
                <td className="px-4 py-3 text-right text-gray-300 tabular-nums">
                  {(b.p_model * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right text-gray-300 tabular-nums">
                  {Number(b.odds).toFixed(2)}{' '}
                  <span className="text-gray-600 text-xs">({decimalToFractional(b.odds)})</span>
                </td>
                <td className="px-4 py-3 text-right"><EdgeBadge edge={b.edge} /></td>
                <td className="px-4 py-3 text-right text-gray-300 tabular-nums">
                  {b.EV > 0
                    ? <span className="text-emerald-400">+{b.EV.toFixed(3)}</span>
                    : <span className="text-red-400">{b.EV.toFixed(3)}</span>
                  }
                </td>
                <td className="px-4 py-3 text-center">
                  {b.won === 1
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
