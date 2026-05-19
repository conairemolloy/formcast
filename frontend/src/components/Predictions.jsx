import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

function ProbCell({ value }) {
  const pct = (value * 100).toFixed(1)
  return (
    <span className={value >= 0.5 ? 'text-emerald-400 font-medium' : 'text-gray-400'}>
      {pct}%
    </span>
  )
}

export default function Predictions() {
  const [data, setData]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [league, setLeague]   = useState('ALL')

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
    if (league === 'ALL') return data
    return data.filter(d => d.league === league)
  }, [data, league])

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading predictions…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Predictions</h1>
        <span className="text-sm text-gray-500">{filtered.length} matches</span>
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

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Date</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">League</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Home</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Away</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">P(H)</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">P(D)</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">P(A)</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Pred</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Actual</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">✓</th>
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
                  <span className="font-mono font-semibold text-blue-400">{row.predicted_result}</span>
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
