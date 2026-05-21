import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'

const LEAGUES = [
  { id: null,           label: 'ALL' },
  { id: 'EPL',          label: 'EPL' },
  { id: 'Championship', label: 'Championship' },
  { id: 'LaLiga',       label: 'La Liga' },
  { id: 'Segunda',      label: 'Segunda' },
  { id: 'SerieA',       label: 'Serie A' },
  { id: 'SerieB',       label: 'Serie B' },
  { id: 'Bundesliga',   label: 'Bundesliga' },
  { id: 'Bundesliga2',  label: 'Bundesliga 2' },
  { id: 'Ligue1',       label: 'Ligue 1' },
  { id: 'Ligue2',       label: 'Ligue 2' },
  { id: 'ScottishPrem', label: 'Scottish' },
  { id: 'CL',           label: 'Champions League' },
  { id: 'DED',          label: 'Eredivisie' },
  { id: 'EC',           label: 'Euros' },
]

const SEASONS = [
  { id: null,      label: 'All' },
  { id: '2025-26', label: '2025-26' },
  { id: '2024-25', label: '2024-25' },
  { id: '2023-24', label: '2023-24' },
]

function fmt(val) {
  return val == null ? '—' : val
}

function pair(h, a) {
  if (h == null && a == null) return '—'
  return `${h ?? '?'}-${a ?? '?'}`
}

function Cards({ yellows, reds }) {
  if (yellows == null && reds == null) return <span className="text-gray-600">—</span>
  const y = yellows ?? 0
  const r = reds ?? 0
  return (
    <span>
      {y > 0 && <span>{y}🟨</span>}
      {y === 0 && <span className="text-gray-500">0🟨</span>}
      {' '}
      {r > 0 && <span>{r}🟥</span>}
      {r === 0 && <span className="text-gray-600">0🟥</span>}
    </span>
  )
}

function rowBorderStyle(result) {
  if (result === 'H') return { borderLeft: '3px solid rgba(16, 185, 129, 0.5)' }
  if (result === 'A') return { borderLeft: '3px solid rgba(239, 68, 68, 0.4)' }
  return { borderLeft: '3px solid transparent' }
}

export default function Matches() {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [league, setLeague]   = useState(null)
  const [season, setSeason]   = useState(null)
  const [teamSearch, setTeamSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ limit: 50 })
    if (league) params.set('league', league)
    if (season) params.set('season', season)
    api.get(`/api/matches?${params}`)
      .then(res => setRows(res.data.data))
      .catch(() => setError('Failed to load match data'))
      .finally(() => setLoading(false))
  }, [league, season])

  const filtered = useMemo(() => {
    if (!teamSearch.trim()) return rows
    const q = teamSearch.trim().toLowerCase()
    return rows.filter(r =>
      r.home_team?.toLowerCase().includes(q) ||
      r.away_team?.toLowerCase().includes(q)
    )
  }, [rows, teamSearch])

  const hasStats = (r) =>
    r.home_shots != null || r.away_shots != null ||
    r.home_shots_target != null || r.away_shots_target != null ||
    r.home_corners != null || r.away_corners != null ||
    r.home_yellows != null || r.away_yellows != null ||
    r.home_reds != null || r.away_reds != null

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex gap-1 flex-wrap">
          {LEAGUES.map(({ id, label }) => (
            <button
              key={label}
              onClick={() => setLeague(id)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                league === id
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <select
          value={season ?? ''}
          onChange={e => setSeason(e.target.value || null)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
        >
          {SEASONS.map(({ id, label }) => (
            <option key={label} value={id ?? ''}>{label}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search team…"
          value={teamSearch}
          onChange={e => setTeamSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 w-48"
        />
      </div>

      {loading && (
        <div className="flex justify-center py-16 text-gray-500">
          <Loader2 className="animate-spin w-6 h-6" />
        </div>
      )}

      {error && (
        <div className="text-red-400 text-sm py-4">{error}</div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/60">
                <th className="text-left px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">Date</th>
                <th className="text-right px-3 py-2.5 text-gray-400 font-medium">Home</th>
                <th className="text-center px-3 py-2.5 text-gray-400 font-medium">Score</th>
                <th className="text-left px-3 py-2.5 text-gray-400 font-medium">Away</th>
                <th className="text-center px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">Shots H-A</th>
                <th className="text-center px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">On Target H-A</th>
                <th className="text-center px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">Corners H-A</th>
                <th className="text-center px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">Cards H / A</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-gray-500">No matches found</td>
                </tr>
              )}
              {filtered.map((r, i) => (
                <tr
                  key={i}
                  style={rowBorderStyle(r.result)}
                  className="border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="px-3 py-2.5 text-gray-400 whitespace-nowrap tabular-nums">
                    {r.match_date ?? '—'}
                  </td>
                  <td className="px-3 py-2.5 text-right text-white font-medium">{r.home_team}</td>
                  <td className="px-3 py-2.5 text-center font-bold text-white tabular-nums whitespace-nowrap">
                    {r.home_goals != null && r.away_goals != null
                      ? `${r.home_goals}-${r.away_goals}`
                      : '—'}
                  </td>
                  <td className="px-3 py-2.5 text-left text-white font-medium">{r.away_team}</td>
                  {hasStats(r) ? (
                    <>
                      <td className="px-3 py-2.5 text-center text-gray-300 tabular-nums">{pair(r.home_shots, r.away_shots)}</td>
                      <td className="px-3 py-2.5 text-center text-gray-300 tabular-nums">{pair(r.home_shots_target, r.away_shots_target)}</td>
                      <td className="px-3 py-2.5 text-center text-gray-300 tabular-nums">{pair(r.home_corners, r.away_corners)}</td>
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        <Cards yellows={r.home_yellows} reds={r.home_reds} />
                        <span className="text-gray-600 mx-1">-</span>
                        <Cards yellows={r.away_yellows} reds={r.away_reds} />
                      </td>
                    </>
                  ) : (
                    <td colSpan={4} className="px-3 py-2.5 text-center text-gray-600 text-xs">
                      No stats available
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
