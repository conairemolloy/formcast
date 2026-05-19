import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
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

export default function ValueBets() {
  const [bets, setBets]         = useState([])
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [outcome, setOutcome]   = useState('ALL')

  useEffect(() => {
    Promise.all([
      api.get('/api/value-bets?limit=100'),
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
    if (outcome === 'ALL') return bets
    return bets.filter(b => b.outcome === outcome)
  }, [bets, outcome])

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

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Total Bets"  value={summary.total_bets} />
          <StatCard label="Win Rate"    value={summary.win_rate != null ? `${(summary.win_rate * 100).toFixed(1)}%` : null} />
          <StatCard label="ROI / Bet"   value={summary.roi != null ? `${summary.roi > 0 ? '+' : ''}${summary.roi.toFixed(3)}` : null} />
          <StatCard label="Mean CLV"    value={summary.mean_clv != null ? summary.mean_clv.toFixed(4) : null} sub="Closing line value" />
        </div>
      )}

      {/* Outcome filter */}
      <div className="flex gap-2">
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
        <span className="ml-auto text-sm text-gray-500 self-center">{filtered.length} bets</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Date</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Fixture</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Out</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Model %</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Odds</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Edge</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">EV</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Result</th>
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
                <td className="px-4 py-3 text-right text-gray-300 tabular-nums">{b.odds}</td>
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
