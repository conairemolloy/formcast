import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'

const LEAGUES = [
  { id: 'EPL',        label: 'EPL' },
  { id: 'LaLiga',     label: 'LaLiga' },
  { id: 'SerieA',     label: 'Serie A' },
  { id: 'Bundesliga', label: 'Bundesliga' },
  { id: 'Ligue1',     label: 'Ligue 1' },
]

function PctBadge({ value, highColor, threshold = 50 }) {
  if (value === 0) return <span className="text-gray-600 tabular-nums">{value.toFixed(1)}%</span>
  const active = value > threshold
  const colors = {
    green: 'bg-emerald-500/20 text-emerald-400',
    blue:  'bg-blue-500/20 text-blue-400',
    red:   'bg-red-500/20 text-red-400',
  }
  if (active) {
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium tabular-nums ${colors[highColor]}`}>
        {value.toFixed(1)}%
      </span>
    )
  }
  return <span className="text-gray-400 tabular-nums text-xs">{value.toFixed(1)}%</span>
}

export default function Tournament() {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [league, setLeague]   = useState('EPL')

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.get(`/api/tournament?league=${league}`)
      .then(res => setRows(res.data.data))
      .catch(() => setError('Failed to load tournament data'))
      .finally(() => setLoading(false))
  }, [league])

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-white">Tournament Simulator</h1>

      <div className="flex gap-2">
        {LEAGUES.map(l => (
          <button
            key={l.id}
            onClick={() => setLeague(l.id)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              league === l.id
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading simulation…
        </div>
      )}
      {error && <div className="text-red-400 p-6">{error}</div>}

      {!loading && !error && (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-gray-400 font-medium w-10">Pos</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">Team</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Pts</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">GD</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Win%</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Top 4%</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Top 6%</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Relegation%</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const isChampion   = row.win_pct === 100
                const isRelegated  = row.relegation_pct === 100
                const rowBg = isChampion
                  ? 'bg-yellow-500/5 border-yellow-500/10'
                  : isRelegated
                  ? 'bg-red-500/5 border-red-500/10'
                  : ''

                return (
                  <tr
                    key={row.team}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors ${rowBg}`}
                  >
                    <td className="px-4 py-3 text-gray-500 tabular-nums">{i + 1}</td>
                    <td className="px-4 py-3 text-white font-medium">{row.team}</td>
                    <td className="px-4 py-3 text-right text-white font-semibold tabular-nums">{row.current_pts}</td>
                    <td className="px-4 py-3 text-right text-gray-300 tabular-nums">
                      {row.current_gd > 0 ? `+${row.current_gd}` : row.current_gd}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <PctBadge value={row.win_pct} highColor="green" />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <PctBadge value={row.top4_pct} highColor="blue" />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <PctBadge value={row.top6_pct} highColor="blue" />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <PctBadge value={row.relegation_pct} highColor="red" />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
