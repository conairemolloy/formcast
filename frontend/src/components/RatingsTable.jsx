import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Search, Loader2, Bookmark } from 'lucide-react'

const MEDAL = ['🥇', '🥈', '🥉']
const MAX_RATING = 1900
const LEAGUE_IDS = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1']

export default function RatingsTable({ onTeamClick, user, onWatchlistUpdate, onShowAuth }) {
  const [data, setData]               = useState([])
  const [teamLeague, setTeamLeague]   = useState({})
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [search, setSearch]           = useState('')
  const [sortDir, setSortDir]         = useState('desc')
  const [league, setLeague]           = useState('ALL')
  const [pending, setPending]         = useState(null)

  const watchlist = user?.watchlist || []

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

  async function toggleWatchlist(e, teamName) {
    e.stopPropagation()
    if (!user) {
      onShowAuth?.()
      return
    }
    if (pending === teamName) return
    setPending(teamName)
    try {
      const inList = watchlist.includes(teamName)
      const endpoint = inList ? '/api/auth/watchlist/remove' : '/api/auth/watchlist/add'
      const res = await api.post(endpoint, { team_name: teamName })
      onWatchlistUpdate?.(res.data.watchlist)
    } catch (err) {
      console.error(err)
    } finally {
      setPending(null)
    }
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
    <div className="flex items-center justify-center h-64 gap-3 text-[var(--muted-foreground)]">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading ratings…
    </div>
  )
  if (error) return <div className="text-[var(--chart-5)] p-6">{error}</div>

  return (
    <div className="fc-page">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-[var(--foreground)]">Team Ratings</h1>
        <span className="text-sm text-[var(--muted-foreground)]">{filtered.length} teams</span>
      </div>

      {/* League filter */}
      <div className="flex gap-2 flex-wrap mb-4">
        {['ALL', ...LEAGUE_IDS].map(l => (
          <button
            key={l}
            onClick={() => setLeague(l)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              league === l
                ? 'bg-[var(--primary)]/12 text-[var(--primary)] border border-[var(--primary)]/30'
                : 'bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:text-[var(--foreground)]'
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
      <div className="relative mb-4 w-full sm:max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted-foreground)]" />
        <input
          type="text"
          placeholder="Search team…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="fc-input w-full rounded-lg pl-9 pr-3 py-2 text-sm"
        />
      </div>

      {/* Table */}
      <div className="fc-card overflow-x-auto">
        <table className="w-full text-sm min-w-[520px]">
          <thead>
            <tr className="bg-[var(--card)] border-b border-[var(--border)]">
              <th className="px-3 py-3 w-10" aria-label="Save" />
              <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium w-16">Rank</th>
              <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium">Team</th>
              <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium">League</th>
              <th
                className="px-4 py-3 text-right text-[var(--muted-foreground)] font-medium cursor-pointer select-none hover:text-[var(--foreground)] transition-colors"
                onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
              >
                Elo Rating {sortDir === 'desc' ? '↓' : '↑'}
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((team, i) => {
              const globalRank = sortedAll.findIndex(t => t.team === team.team)
              const pct        = Math.min((team.elo_rating / MAX_RATING) * 100, 100)
              const isMedal    = globalRank < 3 && !search && league === 'ALL'
              const saved      = watchlist.includes(team.team)

              return (
                <tr
                  key={team.team}
                  onClick={() => handleRowClick(team)}
                  className={`border-b border-[var(--border)] transition-colors hover:bg-[var(--secondary)] ${
                    isMedal ? 'bg-[var(--primary)]/5' : ''
                  } ${onTeamClick ? 'cursor-pointer' : ''}`}
                >
                  {/* Bookmark */}
                  <td className="px-3 py-3 text-center" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={e => toggleWatchlist(e, team.team)}
                      className={`p-1 rounded transition-colors ${
                        saved
                          ? 'text-[var(--primary)] hover:text-[var(--ring)]'
                          : 'text-[var(--muted-foreground)]/60 hover:text-[var(--muted-foreground)]'
                      } ${pending === team.team ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title={
                        !user
                          ? 'Sign in to save teams'
                          : saved
                          ? 'Remove from watchlist'
                          : 'Add to watchlist'
                      }
                      disabled={pending === team.team}
                    >
                      <Bookmark
                        className="w-4 h-4"
                        fill={saved ? 'currentColor' : 'none'}
                      />
                    </button>
                  </td>

                  <td className="px-4 py-3 text-[var(--muted-foreground)] font-mono">
                    {isMedal ? MEDAL[globalRank] : `#${i + 1}`}
                  </td>
                  <td className="px-4 py-3 font-medium">
                    <span className={onTeamClick ? 'text-[var(--foreground)] hover:text-[var(--primary)] transition-colors' : 'text-[var(--foreground)]'}>
                      {team.team}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {teamLeague[team.team] && (
                      <span className="text-xs bg-[var(--muted)] text-[var(--muted-foreground)] px-2 py-0.5 rounded">
                        {teamLeague[team.team]}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-3">
                      <div className="hidden sm:block w-32 h-1.5 bg-[var(--muted)] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isMedal ? 'bg-[var(--primary)]' : 'bg-[var(--muted-foreground)]'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className={`font-mono tabular-nums ${isMedal ? 'text-[var(--primary)] font-semibold' : 'text-[var(--foreground)]'}`}>
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
