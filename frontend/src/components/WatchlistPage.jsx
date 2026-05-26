import { useState, useEffect } from 'react'
import { Bookmark, Search, X, Loader2, Plus } from 'lucide-react'
import api from '../api'

const FORM_COLOR = { W: 'bg-emerald-500', D: 'bg-gray-500', L: 'bg-red-500' }

function FormDots({ form }) {
  return (
    <div className="flex items-center gap-1">
      {form.slice(0, 5).map((r, i) => (
        <div
          key={i}
          className={`w-2.5 h-2.5 rounded-full ${FORM_COLOR[r] || 'bg-gray-700'}`}
          title={r === 'W' ? 'Win' : r === 'D' ? 'Draw' : 'Loss'}
        />
      ))}
    </div>
  )
}

function TeamCard({ teamName, elo, league, form, onRemove }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start justify-between gap-4 hover:border-gray-700 transition-colors">
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-white truncate">{teamName}</h3>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          {league && (
            <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{league}</span>
          )}
          {elo != null && (
            <span className="text-xs text-emerald-400 font-mono tabular-nums">{Math.round(elo)} Elo</span>
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
        className="shrink-0 p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
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
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">My Watchlist</h1>
        <button
          onClick={() => setShowSearch(s => !s)}
          className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Team
        </button>
      </div>

      {/* Search */}
      {showSearch && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            autoFocus
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search for a team…"
            className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
          {searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-10 overflow-hidden">
              {searchResults.map(t => (
                <button
                  key={t.team}
                  onClick={() => addTeam(t.team)}
                  className="w-full text-left px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800 hover:text-white flex items-center justify-between transition-colors"
                >
                  <span>{t.team}</span>
                  <span className="text-xs text-gray-500">{leagueMap[t.team]}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {loadingData && (
        <div className="flex items-center justify-center h-32 gap-3 text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading…
        </div>
      )}

      {!loadingData && watchlist.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <Bookmark className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Save your favourite teams to track them here</p>
          <p className="text-xs text-gray-600 mt-1">Use the star icon on any team in Ratings</p>
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
