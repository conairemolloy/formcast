import { useState, useEffect } from 'react'
import { Bookmark, Search, X, Loader2, Plus } from 'lucide-react'
import api from '../api'

const FORM_COLOR = { W: 'bg-[var(--chart-2)]', D: 'bg-[var(--muted-foreground)]', L: 'bg-[var(--chart-5)]' }

function FormDots({ form }) {
  return (
    <div className="flex items-center gap-1">
      {form.slice(0, 5).map((r, i) => (
        <div
          key={i}
          className={`w-2.5 h-2.5 rounded-full ${FORM_COLOR[r] || 'bg-[var(--muted)]'}`}
          title={r === 'W' ? 'Win' : r === 'D' ? 'Draw' : 'Loss'}
        />
      ))}
    </div>
  )
}

function TeamCard({ teamName, elo, league, form, onRemove }) {
  return (
    <div className="fc-card p-4 flex items-start justify-between gap-4 hover:border-[var(--input)] transition-colors">
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-[var(--foreground)] truncate">{teamName}</h3>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          {league && (
            <span className="text-xs bg-[var(--muted)] text-[var(--muted-foreground)] px-2 py-0.5 rounded">{league}</span>
          )}
          {elo != null && (
            <span className="text-xs text-[var(--chart-2)] font-mono tabular-nums">{Math.round(elo)} Elo</span>
          )}
        </div>
        {form.length > 0 && (
          <div className="mt-2.5">
            <FormDots form={form} />
          </div>
        )}
      </div>
      <button
        onClick={() => onRemove(teamName)}
        className="shrink-0 p-1.5 text-[var(--muted-foreground)] hover:text-[var(--chart-5)] hover:bg-[var(--chart-5)]/10 rounded-lg transition-colors"
        title="Remove from watchlist"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export default function WatchlistPage({ user, onWatchlistUpdate }) {
  const [ratingsMap, setRatingsMap]   = useState({})
  const [leagueMap, setLeagueMap]     = useState({})
  const [formMap, setFormMap]         = useState({})
  const [allTeams, setAllTeams]       = useState([])
  const [search, setSearch]           = useState('')
  const [showSearch, setShowSearch]   = useState(false)
  const [loadingData, setLoadingData] = useState(true)

  const watchlist = user?.watchlist || []

  // Load ratings + league map
  useEffect(() => {
    Promise.all([
      api.get('/api/ratings'),
      api.get('/api/predictions'),
    ]).then(([rRes, pRes]) => {
      const teams = rRes.data.data || []
      setAllTeams(teams)
      const rMap = {}
      for (const t of teams) rMap[t.team] = t
      setRatingsMap(rMap)

      const lMap = {}
      for (const row of pRes.data.data || []) {
        if (row.home_team) lMap[row.home_team] = row.league
        if (row.away_team) lMap[row.away_team] = row.league
      }
      setLeagueMap(lMap)
    }).finally(() => setLoadingData(false))
  }, [])

  // Fetch form for each watched team
  useEffect(() => {
    if (watchlist.length === 0) return
    Promise.all(
      watchlist.map(name =>
        api.get(`/api/team/profile?team=${encodeURIComponent(name)}`)
          .then(r => ({ name, data: r.data.data }))
          .catch(() => ({ name, data: null }))
      )
    ).then(results => {
      const map = {}
      for (const { name, data } of results) {
        if (data?.last_10) {
          map[name] = data.last_10.map(m => m.result).filter(Boolean).slice(0, 5)
        }
      }
      setFormMap(map)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchlist.join(',')])

  async function removeTeam(teamName) {
    try {
      const res = await api.post('/api/auth/watchlist/remove', { team_name: teamName })
      onWatchlistUpdate(res.data.watchlist)
    } catch (e) {
      console.error(e)
    }
  }

  async function addTeam(teamName) {
    if (watchlist.includes(teamName)) return
    try {
      const res = await api.post('/api/auth/watchlist/add', { team_name: teamName })
      onWatchlistUpdate(res.data.watchlist)
      setSearch('')
      setShowSearch(false)
    } catch (e) {
      console.error(e)
    }
  }

  const searchResults = search.length >= 2
    ? allTeams
        .filter(t =>
          t.team.toLowerCase().includes(search.toLowerCase()) &&
          !watchlist.includes(t.team)
        )
        .slice(0, 8)
    : []

  return (
    <div className="fc-page max-w-2xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-[var(--foreground)]">My Watchlist</h1>
        <button
          onClick={() => setShowSearch(s => !s)}
          className="fc-primary-btn flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Team
        </button>
      </div>

      {/* Search */}
      {showSearch && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted-foreground)]" />
          <input
            autoFocus
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search for a team…"
            className="fc-input w-full rounded-xl pl-10 pr-4 py-3 text-sm text-[var(--foreground)] placeholder-[var(--muted-foreground)] transition-colors"
          />
          {searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 fc-card shadow-2xl z-10 overflow-hidden">
              {searchResults.map(t => (
                <button
                  key={t.team}
                  onClick={() => addTeam(t.team)}
                  className="w-full text-left px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)] flex items-center justify-between transition-colors"
                >
                  <span>{t.team}</span>
                  <span className="text-xs text-[var(--muted-foreground)]">{leagueMap[t.team]}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {loadingData && (
        <div className="flex items-center justify-center h-32 gap-3 text-[var(--muted-foreground)]">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading…
        </div>
      )}

      {!loadingData && watchlist.length === 0 && (
        <div className="text-center py-20 text-[var(--muted-foreground)]">
          <Bookmark className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Save your favourite teams to track them here</p>
          <p className="text-xs text-[var(--muted-foreground)]/60 mt-1">Use the star icon on any team in Ratings</p>
        </div>
      )}

      {!loadingData && watchlist.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {watchlist.map(name => (
            <TeamCard
              key={name}
              teamName={name}
              elo={ratingsMap[name]?.elo_rating}
              league={leagueMap[name]}
              form={formMap[name] || []}
              onRemove={removeTeam}
            />
          ))}
        </div>
      )}
    </div>
  )
}
