import { useState, useEffect, useRef, useMemo } from 'react'
import api from '../api'
import { Loader2, ArrowRight } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'

// ---------------------------------------------------------------------------
// Searchable combobox
// ---------------------------------------------------------------------------

function TeamSelect({ label, teams, value, onChange }) {
  const [query, setQuery]   = useState(value)
  const [open, setOpen]     = useState(false)
  const containerRef        = useRef(null)

  // Sync display when parent changes value (e.g. swap)
  useEffect(() => { setQuery(value) }, [value])

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
    return q.length < 1 ? teams : teams.filter(t => t.toLowerCase().includes(q))
  }, [query, teams])

  function select(team) {
    onChange(team)
    setQuery(team)
    setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative flex-1 min-w-0">
      <label className="block text-xs text-gray-500 mb-1.5 font-medium">{label}</label>
      <input
        type="text"
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onKeyDown={e => {
          if (e.key === 'Escape') setOpen(false)
          if (e.key === 'Enter' && filtered.length > 0) select(filtered[0])
        }}
        placeholder="Search team…"
        className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors"
      />
      {open && filtered.length > 0 && (
        <div className="absolute z-30 top-full mt-1 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
          <div className="max-h-52 overflow-y-auto">
            {filtered.slice(0, 12).map(team => (
              <button
                key={team}
                onMouseDown={e => { e.preventDefault(); select(team) }}
                className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                  team === value
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                {team}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Probability bar
// ---------------------------------------------------------------------------

function ProbBar({ homeTeam, awayTeam, pHome, pDraw, pAway }) {
  const ph = Math.round(pHome * 100)
  const pd = Math.round(pDraw * 100)
  const pa = Math.round(pAway * 100)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-5">
      <h2 className="text-sm font-semibold text-white mb-4">Win Probability</h2>

      <div className="flex items-center justify-between text-sm mb-2">
        <span className="font-medium text-emerald-400 truncate max-w-[35%]">{homeTeam}</span>
        <span className="text-gray-500 text-xs">Draw</span>
        <span className="font-medium text-blue-400 truncate max-w-[35%] text-right">{awayTeam}</span>
      </div>

      <div className="flex h-3 rounded-full overflow-hidden gap-px">
        <div className="bg-emerald-500 transition-all duration-700 rounded-l-full" style={{ width: `${ph}%` }} />
        <div className="bg-gray-600 transition-all duration-700" style={{ width: `${pd}%` }} />
        <div className="bg-blue-500 transition-all duration-700 rounded-r-full" style={{ width: `${pa}%` }} />
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-lg font-bold tabular-nums text-emerald-400">{ph}%</span>
        <span className="text-sm tabular-nums text-gray-500">{pd}%</span>
        <span className="text-lg font-bold tabular-nums text-blue-400">{pa}%</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Elo history chart
// ---------------------------------------------------------------------------

function EloHistoryChart({ homeTeam, awayTeam, homeHistory, awayHistory }) {
  const merged = useMemo(() => {
    const map = {}
    for (const { season, elo_rating } of homeHistory) {
      map[season] = { season, home: elo_rating }
    }
    for (const { season, elo_rating } of awayHistory) {
      map[season] = { ...map[season], season, away: elo_rating }
    }
    return Object.values(map).sort((a, b) => a.season.localeCompare(b.season))
  }, [homeHistory, awayHistory])

  const allElos = merged.flatMap(d => [d.home, d.away]).filter(Boolean)
  const minElo  = Math.floor((Math.min(...allElos) - 50) / 50) * 50
  const maxElo  = Math.ceil((Math.max(...allElos) + 50) / 50) * 50

  const ChartTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs space-y-1">
        <p className="text-gray-400 font-medium">{label}</p>
        {payload.map(p => (
          <p key={p.dataKey} style={{ color: p.color }}>
            {p.name}: {p.value?.toFixed(0)}
          </p>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-5">
      <h2 className="text-sm font-semibold text-white mb-1">Elo Rating History</h2>
      <p className="text-xs text-gray-500 mb-4">End-of-season Elo rating per team</p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={merged} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <XAxis
            dataKey="season"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minElo, maxElo]}
            tick={{ fill: '#6b7280', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.06)' }} />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="plainline"
            wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
            formatter={(value) => (
              <span style={{ color: value === 'home' ? '#10b981' : '#3b82f6' }}>
                {value === 'home' ? homeTeam : awayTeam}
              </span>
            )}
          />
          <Line
            name="home"
            type="monotone"
            dataKey="home"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#10b981' }}
            connectNulls
          />
          <Line
            name="away"
            type="monotone"
            dataKey="away"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3b82f6' }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// H2H record
// ---------------------------------------------------------------------------

function H2HRecord({ homeTeam, awayTeam, h2h }) {
  const total = h2h.home_wins + h2h.draws + h2h.away_wins

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-5">
      <h2 className="text-sm font-semibold text-white mb-4">
        Head to Head Record
        {total > 0 && <span className="text-gray-500 font-normal ml-2 text-xs">(last {total} meetings)</span>}
      </h2>

      {/* Summary bar */}
      <div className="flex items-center justify-between text-xs mb-2">
        <span className="text-emerald-400 font-medium">{homeTeam}</span>
        <span className="text-gray-500">Draws</span>
        <span className="text-blue-400 font-medium">{awayTeam}</span>
      </div>

      {total > 0 ? (
        <>
          <div className="flex h-2.5 rounded-full overflow-hidden gap-px mb-2">
            <div className="bg-emerald-500 rounded-l-full" style={{ width: `${(h2h.home_wins / total) * 100}%` }} />
            <div className="bg-gray-600" style={{ width: `${(h2h.draws / total) * 100}%` }} />
            <div className="bg-blue-500 rounded-r-full" style={{ width: `${(h2h.away_wins / total) * 100}%` }} />
          </div>

          <div className="flex items-center justify-between text-sm font-bold mb-5">
            <span className="text-emerald-400 tabular-nums">{h2h.home_wins}</span>
            <span className="text-gray-500 tabular-nums">{h2h.draws}</span>
            <span className="text-blue-400 tabular-nums">{h2h.away_wins}</span>
          </div>
        </>
      ) : (
        <p className="text-gray-500 text-sm text-center py-4">No H2H data found</p>
      )}

      {/* Recent matches */}
      {h2h.matches?.length > 0 && (
        <>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Recent meetings</h3>
          <div className="space-y-1.5">
            {h2h.matches.map((m, i) => {
              const hWin = m.home_goals != null && m.away_goals != null && m.home_goals > m.away_goals
              const aWin = m.home_goals != null && m.away_goals != null && m.away_goals > m.home_goals
              const isHomeTeamHome = m.home_team === homeTeam
              const teamWon = isHomeTeamHome ? hWin : aWin
              const teamLost = isHomeTeamHome ? aWin : hWin
              const resultColor = teamWon ? 'text-emerald-400' : teamLost ? 'text-red-400' : 'text-gray-500'

              return (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-gray-950 border border-gray-800/60"
                >
                  <span className="text-gray-500 tabular-nums w-20 shrink-0">{m.date}</span>
                  <div className="flex items-center gap-2 flex-1 justify-center">
                    <span className={`font-medium truncate max-w-[90px] text-right ${m.home_team === homeTeam ? 'text-emerald-400' : 'text-blue-400'}`}>
                      {m.home_team}
                    </span>
                    <span className={`font-bold tabular-nums shrink-0 ${resultColor}`}>
                      {m.home_goals ?? '?'}–{m.away_goals ?? '?'}
                    </span>
                    <span className={`font-medium truncate max-w-[90px] ${m.away_team === awayTeam ? 'text-blue-400' : 'text-emerald-400'}`}>
                      {m.away_team}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Season stats comparison
// ---------------------------------------------------------------------------

function StatRow({ label, homeVal, awayVal, higherIsBetter = true }) {
  const h = homeVal ?? 0
  const a = awayVal ?? 0
  const homeLeads = higherIsBetter ? h > a : h < a
  const awayLeads = higherIsBetter ? a > h : a < h

  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-800/50 last:border-0">
      <span className={`w-10 text-right tabular-nums font-semibold text-sm ${homeLeads ? 'text-emerald-400' : 'text-gray-300'}`}>
        {homeVal ?? '—'}
      </span>
      <span className="flex-1 text-center text-xs text-gray-500">{label}</span>
      <span className={`w-10 text-left tabular-nums font-semibold text-sm ${awayLeads ? 'text-blue-400' : 'text-gray-300'}`}>
        {awayVal ?? '—'}
      </span>
    </div>
  )
}

function SeasonStats({ homeTeam, awayTeam, homeProfile, awayProfile }) {
  const hs = homeProfile?.stats
  const as_ = awayProfile?.stats

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-5">
      <h2 className="text-sm font-semibold text-white mb-1">
        {homeProfile?.season ?? '2025-26'} Season Stats
      </h2>
      <p className="text-xs text-gray-500 mb-4">Highlighted values show the leading team</p>

      {/* Column headers */}
      <div className="flex items-center gap-3 mb-1 pb-2 border-b border-gray-800">
        <span className="w-10 text-right text-xs font-semibold text-emerald-400 truncate">{homeTeam}</span>
        <span className="flex-1" />
        <span className="w-10 text-left text-xs font-semibold text-blue-400 truncate">{awayTeam}</span>
      </div>

      <StatRow label="Played"       homeVal={hs?.played}        awayVal={as_?.played}       />
      <StatRow label="Wins"         homeVal={hs?.wins}          awayVal={as_?.wins}         />
      <StatRow label="Draws"        homeVal={hs?.draws}         awayVal={as_?.draws}        />
      <StatRow label="Losses"       homeVal={hs?.losses}        awayVal={as_?.losses}       higherIsBetter={false} />
      <StatRow label="Goals For"    homeVal={hs?.goals_for}     awayVal={as_?.goals_for}    />
      <StatRow label="Goals Against" homeVal={hs?.goals_against} awayVal={as_?.goals_against} higherIsBetter={false} />
      <StatRow
        label="Goal Diff"
        homeVal={hs?.goal_diff != null ? (hs.goal_diff > 0 ? `+${hs.goal_diff}` : hs.goal_diff) : null}
        awayVal={as_?.goal_diff != null ? (as_.goal_diff > 0 ? `+${as_.goal_diff}` : as_.goal_diff) : null}
        higherIsBetter={true}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function H2H() {
  const [teams, setTeams]           = useState([])
  const [homeTeam, setHomeTeam]     = useState('Arsenal')
  const [awayTeam, setAwayTeam]     = useState('Man City')
  const [preview, setPreview]       = useState(null)
  const [homeHistory, setHomeHistory] = useState(null)
  const [awayHistory, setAwayHistory] = useState(null)
  const [homeProfile, setHomeProfile] = useState(null)
  const [awayProfile, setAwayProfile] = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [compared, setCompared]     = useState(false)

  // Load team list on mount
  useEffect(() => {
    api.get('/api/ratings')
      .then(res => setTeams(res.data.data.map(t => t.team).sort()))
      .catch(() => {})
  }, [])

  // Auto-compare defaults on first load
  useEffect(() => {
    if (teams.length > 0 && !compared) compare()
  }, [teams]) // eslint-disable-line react-hooks/exhaustive-deps

  async function compare() {
    if (!homeTeam.trim() || !awayTeam.trim()) return
    setLoading(true)
    setError(null)
    setCompared(true)
    try {
      const [prevRes, homeHistRes, awayHistRes, homeProRes, awayProRes] = await Promise.all([
        api.get(`/api/match/preview?home_team=${encodeURIComponent(homeTeam)}&away_team=${encodeURIComponent(awayTeam)}`),
        api.get(`/api/ratings/history?team=${encodeURIComponent(homeTeam)}`),
        api.get(`/api/ratings/history?team=${encodeURIComponent(awayTeam)}`),
        api.get(`/api/team/profile?team=${encodeURIComponent(homeTeam)}`),
        api.get(`/api/team/profile?team=${encodeURIComponent(awayTeam)}`),
      ])
      setPreview(prevRes.data.data)
      setHomeHistory(homeHistRes.data.data)
      setAwayHistory(awayHistRes.data.data)
      setHomeProfile(homeProRes.data.data)
      setAwayProfile(awayProRes.data.data)
    } catch (e) {
      setError(e?.response?.data?.error ?? 'Failed to load comparison data')
    } finally {
      setLoading(false)
    }
  }

  const hasData = preview && homeHistory && awayHistory && homeProfile && awayProfile

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-white mb-0.5">Head to Head</h1>
        <p className="text-sm text-gray-500">Compare any two teams across Elo ratings, H2H record, and season form</p>
      </div>

      {/* Section 1 — Team selector */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-5">
        <div className="flex flex-col sm:flex-row items-end gap-3">
          <TeamSelect
            label="Home Team"
            teams={teams}
            value={homeTeam}
            onChange={setHomeTeam}
          />

          <div className="shrink-0 pb-0 sm:pb-0.5">
            <span className="flex items-center justify-center w-8 h-10 text-gray-600">
              <ArrowRight className="w-4 h-4" />
            </span>
          </div>

          <TeamSelect
            label="Away Team"
            teams={teams}
            value={awayTeam}
            onChange={setAwayTeam}
          />

          <button
            onClick={compare}
            disabled={loading}
            className="shrink-0 px-5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Compare'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {loading && !hasData && (
        <div className="flex justify-center py-16">
          <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
        </div>
      )}

      {hasData && !loading && (
        <div className="space-y-4">
          {/* Section 2 — Win probability */}
          <ProbBar
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            pHome={preview.p_home}
            pDraw={preview.p_draw}
            pAway={preview.p_away}
          />

          {/* Elo badges */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">{homeTeam} Elo</p>
              <p className="text-2xl font-black font-mono text-emerald-400 tabular-nums">{preview.home_elo}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">{awayTeam} Elo</p>
              <p className="text-2xl font-black font-mono text-blue-400 tabular-nums">{preview.away_elo}</p>
            </div>
          </div>

          {/* Section 3 — Elo history */}
          <EloHistoryChart
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            homeHistory={homeHistory}
            awayHistory={awayHistory}
          />

          {/* Sections 4 & 5 — H2H + season stats side by side on wide screens */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <H2HRecord
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              h2h={preview.h2h}
            />
            <SeasonStats
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              homeProfile={homeProfile}
              awayProfile={awayProfile}
            />
          </div>
        </div>
      )}
    </div>
  )
}
