import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Search, Loader2 } from 'lucide-react'

const MEDAL = ['🥇', '🥈', '🥉']
const MAX_RATING = 1900
const LEAGUE_IDS = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1']

export default function RatingsTable({ onTeamClick }) {
  const [data, setData]               = useState([])
  const [teamLeague, setTeamLeague]   = useState({})
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [search, setSearch]           = useState('')
  const [sortDir, setSortDir]         = useState('desc')
  const [league, setLeague]           = useState('ALL')

  useEffect(() => {
    Promise.all([
      api.get('/api/ratings'),
      api.get('/api/predictions'),
    ]).then(([ratingsRes, predsRes]) => {
      setData(ratingsRes.data.data)
      const map = {}
      for (const row of predsRes.data.data) {
        if (row.home_team) map[row.home_team] = row.league
        if (row.away_team) map[row.away_team] = row.league
      }
      setTeamLeague(map)
    })
    .catch(() => setError('Failed to load ratings'))
    .finally(() => setLoading(false))
  }, [])

  const leagueCounts = useMemo(() => {
    const counts = {}
    for (const t of data) {
      const l = teamLeague[t.team]
      if (l) counts[l] = (counts[l] || 0) + 1
    }
    return counts
  }, [data, teamLeague])

  const sortedAll = useMemo(() =>
    [...data].sort((a, b) => b.elo_rating - a.elo_rating),
  [data])

  function getLeagueRank(teamName) {
    const lg = teamLeague[teamName]
    if (!lg) return null
    const ranked = [...data]
      .filter(t => teamLeague[t.team] === lg)
      .sort((a, b) => b.elo_rating - a.elo_rating)
    const idx = ranked.findIndex(t => t.team === teamName)
    return idx >= 0 ? idx + 1 : null
  }

  function handleRowClick(team) {
    if (!onTeamClick) return
    onTeamClick({
      name:   team.team,
      elo:    team.elo_rating,
      league: teamLeague[team.team] ?? null,
      rank:   getLeagueRank(team.team),
    })
  }

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    let rows = q ? data.filter(t => t.team.toLowerCase().includes(q)) : data
    if (league !== 'ALL') rows = rows.filter(t => teamLeague[t.team] === league)
    return [...rows].sort((a, b) =>
      sortDir === 'desc' ? b.elo_rating - a.elo_rating : a.elo_rating - b.elo_rating
    )
  }, [data, search, sortDir, league, teamLeague])

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading ratings…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-white">Team Ratings</h1>
        <span className="text-sm text-gray-500">{filtered.length} teams</span>
      </div>

      {/* League filter */}
      <div className="flex gap-2 flex-wrap mb-4">
        {['ALL', ...LEAGUE_IDS].map(l => (
          <button
            key={l}
            onClick={() => setLeague(l)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              league === l
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
            }`}
          >
            {l === 'ALL' ? 'All' : l}
            {l !== 'ALL' && leagueCounts[l]
              ? <span className="ml-1.5 text-xs opacity-60">({leagueCounts[l]})</span>
              : null
            }
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative mb-4 max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search team…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-800">
              <th className="px-4 py-3 text-left text-gray-400 font-medium w-16">Rank</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Team</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">League</th>
              <th
                className="px-4 py-3 text-right text-gray-400 font-medium cursor-pointer select-none hover:text-white transition-colors"
                onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
              >
                Elo Rating {sortDir === 'desc' ? '↓' : '↑'}
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((team, i) => {
              const globalRank = sortedAll.findIndex(t => t.team === team.team)
              const pct = Math.min((team.elo_rating / MAX_RATING) * 100, 100)
              const isMedal = globalRank < 3 && !search && league === 'ALL'

              return (
                <tr
                  key={team.team}
                  onClick={() => handleRowClick(team)}
                  className={`border-b border-gray-800/50 transition-colors hover:bg-gray-800/50 ${
                    isMedal ? 'bg-gray-900/80' : ''
                  } ${onTeamClick ? 'cursor-pointer' : ''}`}
                >
                  <td className="px-4 py-3 text-gray-500 font-mono">
                    {isMedal ? MEDAL[globalRank] : `#${i + 1}`}
                  </td>
                  <td className="px-4 py-3 font-medium">
                    <span className={onTeamClick ? 'text-white hover:text-emerald-400 transition-colors' : 'text-white'}>
                      {team.team}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {teamLeague[team.team] && (
                      <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">
                        {teamLeague[team.team]}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-3">
                      <div className="w-32 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isMedal ? 'bg-emerald-400' : 'bg-emerald-600'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className={`font-mono tabular-nums ${isMedal ? 'text-emerald-300 font-semibold' : 'text-gray-300'}`}>
                        {team.elo_rating.toFixed(0)}
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
