import { useState, useEffect, useRef, useMemo } from 'react'
import api from '../api'
import { Loader2, Search, FlaskConical } from 'lucide-react'
import MatchPreview from './MatchPreview'

// ---------------------------------------------------------------------------
// League badge colours
// ---------------------------------------------------------------------------

const LEAGUE_CLASSES = {
  EPL:         'bg-violet-500/20 text-violet-300',
  LaLiga:      'bg-orange-500/20 text-orange-300',
  Bundesliga:  'bg-yellow-500/20 text-yellow-300',
  SerieA:      'bg-blue-500/20 text-blue-300',
  Ligue1:      'bg-sky-500/20 text-sky-300',
  Championship:'bg-purple-500/20 text-purple-300',
  Ligue2:      'bg-cyan-500/20 text-cyan-300',
  SerieB:      'bg-indigo-500/20 text-indigo-300',
  Bundesliga2: 'bg-amber-500/20 text-amber-300',
  ScottishPrem:'bg-teal-500/20 text-teal-300',
  Segunda:     'bg-rose-500/20 text-rose-300',
}

function LeagueBadge({ league }) {
  const cls = LEAGUE_CLASSES[league] ?? 'bg-gray-700/60 text-gray-400'
  return (
    <span className={`shrink-0 text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${cls}`}>
      {league}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Searchable team combobox
// ---------------------------------------------------------------------------

function TeamSelect({ label, teams, value, onChange }) {
  const [query, setQuery] = useState('')
  const [open, setOpen]   = useState(false)
  const containerRef      = useRef(null)

  // Sync display text when value changes externally
  useEffect(() => {
    setQuery(value ? value.team : '')
  }, [value])

  // Close on outside click
  useEffect(() => {
    function onDown(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return teams
    return teams.filter(t =>
      t.team.toLowerCase().includes(q) || t.league.toLowerCase().includes(q)
    )
  }, [query, teams])

  function select(item) {
    onChange(item)
    setQuery(item.team)
    setOpen(false)
  }

  function handleChange(e) {
    setQuery(e.target.value)
    setOpen(true)
    if (value && e.target.value !== value.team) onChange(null)
  }

  return (
    <div ref={containerRef} className="relative flex-1 min-w-0">
      <label className="block text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={handleChange}
          onFocus={() => setOpen(true)}
          onKeyDown={e => {
            if (e.key === 'Escape') setOpen(false)
            if (e.key === 'Enter' && filtered.length > 0) select(filtered[0])
          }}
          placeholder="Search team…"
          className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-8 pr-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors"
        />
      </div>

      {open && filtered.length > 0 && (
        <div className="absolute z-30 top-full mt-1 w-full bg-gray-900 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
          <div className="max-h-56 overflow-y-auto">
            {filtered.slice(0, 20).map(item => (
              <button
                key={`${item.team}-${item.league}`}
                onMouseDown={e => { e.preventDefault(); select(item) }}
                className={`w-full text-left flex items-center justify-between gap-2 px-3 py-2 text-sm transition-colors ${
                  value?.team === item.team
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <span className="truncate">{item.team}</span>
                <LeagueBadge league={item.league} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const PREVIEW_FEATURES = [
  'Win Probabilities', 'Goals Markets',
  'Correct Scores',   'Corners & Cards',
  'Recent Form',      'Head to Head',
  'Team Profiles',
]

export default function MatchResearch() {
  const [teams, setTeams]         = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [homeTeam, setHomeTeam]   = useState(null)
  const [awayTeam, setAwayTeam]   = useState(null)
  const [previewMatch, setPreviewMatch] = useState(null)

  useEffect(() => {
    Promise.all([api.get('/api/ratings'), api.get('/api/predictions')])
      .then(([ratingsRes, predictionsRes]) => {
        const leagueMap = {}
        for (const row of (predictionsRes.data.data ?? [])) {
          if (row.home_team) leagueMap[row.home_team] = row.league
          if (row.away_team) leagueMap[row.away_team] = row.league
        }
        const sorted = (ratingsRes.data.data ?? [])
          .filter(r => r.team)
          .map(r => ({ team: r.team, league: leagueMap[r.team] || 'Other', elo_rating: r.elo_rating }))
          .sort((a, b) => a.league.localeCompare(b.league) || a.team.localeCompare(b.team))
        setTeams(sorted)
      })
      .catch(() => {})
      .finally(() => setTeamsLoading(false))
  }, [])

  const canAnalyse = !!homeTeam && !!awayTeam && homeTeam.team !== awayTeam.team
  const sameTeam   = !!homeTeam && !!awayTeam && homeTeam.team === awayTeam.team

  function handleAnalyse() {
    if (!canAnalyse) return
    const competition = homeTeam.league === awayTeam.league
      ? homeTeam.league
      : `${homeTeam.league} / ${awayTeam.league}`
    setPreviewMatch({
      home_team:   homeTeam.team,
      away_team:   awayTeam.team,
      competition,
      match_date:  new Date().toISOString().slice(0, 10),
    })
  }

  return (
    <div className="max-w-xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2.5 mb-1">
          <FlaskConical className="w-5 h-5 text-emerald-400" />
          <h1 className="text-xl font-bold text-white">Match Research</h1>
        </div>
        <p className="text-sm text-gray-500">Select any two teams to generate a full match analysis.</p>
      </div>

      {/* Selector card */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
        {teamsLoading ? (
          <div className="flex items-center gap-2.5 py-4">
            <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
            <span className="text-sm text-gray-500">Loading teams…</span>
          </div>
        ) : (
          <>
            <div className="flex gap-3 items-start mb-4">
              <TeamSelect
                label="Home Team"
                teams={teams}
                value={homeTeam}
                onChange={setHomeTeam}
              />
              <div className="flex items-end pb-3 shrink-0 text-gray-600 text-sm font-bold select-none">
                vs
              </div>
              <TeamSelect
                label="Away Team"
                teams={teams}
                value={awayTeam}
                onChange={setAwayTeam}
              />
            </div>

            {sameTeam && (
              <p className="text-xs text-amber-400 mb-3">Teams must be different.</p>
            )}

            {/* Selected summary */}
            {homeTeam && awayTeam && !sameTeam && (
              <div className="flex items-center justify-between bg-gray-800/50 rounded-lg px-3 py-2 mb-4 text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="font-semibold text-white">{homeTeam.team}</span>
                  <LeagueBadge league={homeTeam.league} />
                </span>
                <span className="text-gray-600 font-bold">vs</span>
                <span className="flex items-center gap-1.5">
                  <LeagueBadge league={awayTeam.league} />
                  <span className="font-semibold text-white">{awayTeam.team}</span>
                </span>
              </div>
            )}

            <button
              onClick={handleAnalyse}
              disabled={!canAnalyse}
              className="w-full py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white"
            >
              Analyse Match
            </button>
          </>
        )}
      </div>

      {/* Feature preview tiles (shown when no analysis open) */}
      {!previewMatch && (
        <div className="mt-6 grid grid-cols-2 gap-2.5">
          {PREVIEW_FEATURES.slice(0, 6).map(label => (
            <div
              key={label}
              className="bg-gray-900/50 border border-gray-800/50 rounded-xl py-3 px-3 text-center"
            >
              <p className="text-xs text-gray-600">{label}</p>
            </div>
          ))}
          <div className="col-span-2 bg-gray-900/50 border border-gray-800/50 rounded-xl py-3 px-3 text-center">
            <p className="text-xs text-gray-600">{PREVIEW_FEATURES[6]}</p>
          </div>
        </div>
      )}

      {/* Match preview modal */}
      {previewMatch && (
        <MatchPreview
          match={previewMatch}
          onClose={() => setPreviewMatch(null)}
        />
      )}
    </div>
  )
}
