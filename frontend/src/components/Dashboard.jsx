import { useState, useEffect, useCallback } from 'react'
import api from '../api'
import { Loader2, Zap, ArrowRight, RefreshCw, TrendingUp } from 'lucide-react'
import MatchPreview from './MatchPreview'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

function fmtDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${d} ${months[+m - 1]} ${y}`
}

function fmtTime(t) {
  return t ? t.slice(0, 5) : ''
}

function pct(v) {
  return v == null ? '—' : `${Math.round(v * 100)}%`
}

// ---------------------------------------------------------------------------
// Mini prob bar (used in live + upcoming rows)
// ---------------------------------------------------------------------------

function MiniProbBar({ pHome, pDraw, pAway }) {
  const ph = Math.round((pHome ?? 0) * 100)
  const pd = Math.round((pDraw ?? 0) * 100)
  const pa = Math.round((pAway ?? 0) * 100)
  return (
    <div className="w-full">
      <div className="flex h-1.5 rounded-full overflow-hidden">
        <div className="bg-emerald-500" style={{ width: `${ph}%` }} />
        <div className="bg-gray-600"   style={{ width: `${pd}%` }} />
        <div className="bg-red-500"    style={{ width: `${pa}%` }} />
      </div>
      <div className="flex justify-between mt-0.5 text-[10px] tabular-nums text-gray-500">
        <span>{ph}%</span>
        <span>{pd}%</span>
        <span>{pa}%</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({ title, action, actionLabel, children }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {action && (
          <button
            onClick={action}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-emerald-400 transition-colors"
          >
            {actionLabel}
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 1 — Live Now
// ---------------------------------------------------------------------------

function LiveSection({ data, loading, error, lastRefresh, onRefresh, onMatchClick }) {
  const liveMatches = (data ?? []).filter(m =>
    ['IN_PLAY', 'PAUSED', 'LIVE'].includes(m.status)
  )
  const nextUp = (data ?? []).find(m => m.status === 'SCHEDULED' || m.status === 'TIMED')

  if (loading && !data) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <p className="px-4 py-6 text-center text-sm text-gray-600">{error}</p>
    )
  }

  if (liveMatches.length === 0) {
    return (
      <div className="px-4 py-6 text-center">
        <p className="text-sm text-gray-500 mb-1">No matches currently in play</p>
        {nextUp && (
          <p className="text-xs text-gray-600">
            Next: <span className="text-gray-400">{nextUp.home_team} vs {nextUp.away_team}</span>
            {' '}at <span className="text-gray-400">{fmtTime(nextUp.match_time)}</span>
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-800/60">
      {liveMatches.slice(0, 3).map(m => (
        <button
          key={m.match_id}
          onClick={() => onMatchClick(m)}
          className="w-full text-left px-4 py-3 hover:bg-gray-800/40 transition-colors"
        >
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className="flex-1 min-w-0">
              <span className="text-sm text-white font-medium truncate block">{m.home_team}</span>
            </div>
            <div className="text-center shrink-0">
              <span className="text-base font-bold text-emerald-400 tabular-nums">
                {m.home_goals ?? 0} – {m.away_goals ?? 0}
              </span>
              {m.minute != null && (
                <span className="block text-[10px] text-emerald-500 tabular-nums">{m.minute}'</span>
              )}
            </div>
            <div className="flex-1 min-w-0 text-right">
              <span className="text-sm text-white font-medium truncate block">{m.away_team}</span>
            </div>
          </div>
          <MiniProbBar pHome={m.p_home} pDraw={m.p_draw} pAway={m.p_away} />
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 2 — Value Bets
// ---------------------------------------------------------------------------

const OUTCOME_LABEL = { H: 'Home', D: 'Draw', A: 'Away' }
const LEAGUE_SHORT  = {
  EPL: 'EPL', LaLiga: 'La Liga', SerieA: 'Serie A',
  Bundesliga: 'Bundesliga', Ligue1: 'Ligue 1',
  Championship: 'Champ.', SerieB: 'Serie B',
}

function ValueBetCard({ bet }) {
  return (
    <div className="px-4 py-3 border-b border-gray-800/60 last:border-0">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <p className="text-xs text-gray-300 font-medium truncate">
            {bet.home_team} <span className="text-gray-600">vs</span> {bet.away_team}
          </p>
          <p className="text-[10px] text-gray-600 mt-0.5">
            {LEAGUE_SHORT[bet.league] ?? bet.league} · {bet.match_date}
            {bet.match_time ? ` · ${bet.match_time}` : ''}
          </p>
        </div>
        <span className="shrink-0 text-xs font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
          {OUTCOME_LABEL[bet.value_outcome] ?? bet.value_outcome}
        </span>
      </div>
      <div className="flex gap-4 text-[11px] tabular-nums">
        <span className="text-gray-500">Model <span className="text-gray-300">{pct(bet.value_p_model)}</span></span>
        <span className="text-gray-500">Odds <span className="text-gray-300">{bet.value_odds?.toFixed(2)}</span></span>
        <span className="text-gray-500">Edge <span className="text-emerald-400 font-semibold">{pct(bet.value_edge)}</span></span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 3 — Upcoming Fixtures
// ---------------------------------------------------------------------------

function stripSuffix(name) {
  return (name ?? '').replace(/ (United FC|FC|AFC|CF|SC|BC)$/i, '').trim()
}

function UpcomingRow({ match, onClick }) {
  const homeDisplay = stripSuffix(match.home_team)
  const awayDisplay = stripSuffix(match.away_team)
  const cleanMatch  = { ...match, home_team: homeDisplay, away_team: awayDisplay }

  return (
    <button
      onClick={() => onClick(cleanMatch)}
      className="w-full text-left px-4 py-3 border-b border-gray-800/60 last:border-0 hover:bg-gray-800/40 transition-colors"
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="min-w-0 flex-1">
          <p className="text-xs text-gray-300 font-medium truncate">
            {homeDisplay} <span className="text-gray-600">vs</span> {awayDisplay}
          </p>
          <p className="text-[10px] text-gray-600 mt-0.5">
            {match.competition} · {fmtDate(match.match_date)} {fmtTime(match.match_time) && `· ${fmtTime(match.match_time)}`}
          </p>
        </div>
      </div>
      <MiniProbBar pHome={match.p_home} pDraw={match.p_draw} pAway={match.p_away} />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Section 4 — Top Ratings
// ---------------------------------------------------------------------------

const MEDAL = ['🥇', '🥈', '🥉']

function RatingRow({ team, rank }) {
  const isMedal = rank < 3
  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 border-b border-gray-800/60 last:border-0 ${isMedal ? 'bg-gray-900/60' : ''}`}>
      <span className="w-6 text-center text-xs font-mono text-gray-600 shrink-0">
        {isMedal ? MEDAL[rank] : `${rank + 1}`}
      </span>
      <span className={`flex-1 text-sm truncate font-medium ${isMedal ? 'text-white' : 'text-gray-300'}`}>
        {team.team}
      </span>
      <span className={`text-sm font-mono tabular-nums font-semibold shrink-0 ${isMedal ? 'text-emerald-400' : 'text-gray-400'}`}>
        {team.elo_rating?.toFixed(0)}
      </span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 5 — Model Performance
// ---------------------------------------------------------------------------

const MODEL_STATS = [
  { label: 'Hit Rate',   value: '68.7%',    color: 'text-emerald-400' },
  { label: 'Brier',      value: '0.156',    color: 'text-blue-400' },
  { label: 'Mean CLV',   value: '+19.0%',   color: 'text-emerald-400' },
  { label: 'Matches',    value: '128,797',  color: 'text-gray-300' },
]

function ModelPerf({ onNavigate }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          <h2 className="text-sm font-semibold text-white">Model Performance</h2>
        </div>
        <button
          onClick={() => onNavigate('backtest')}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-emerald-400 transition-colors"
        >
          Full backtest <ArrowRight className="w-3 h-3" />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 divide-x-0 sm:divide-x divide-gray-800">
        {MODEL_STATS.map(({ label, value, color }) => (
          <div key={label} className="flex flex-col items-center justify-center py-4 px-3 text-center">
            <span className={`text-xl font-black font-mono tabular-nums ${color}`}>{value}</span>
            <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider mt-1">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export default function Dashboard({ onNavigate }) {
  const [liveData,     setLiveData]     = useState(null)
  const [liveError,    setLiveError]    = useState(null)
  const [liveLoading,  setLiveLoading]  = useState(true)
  const [lastRefresh,  setLastRefresh]  = useState(null)

  const [valueBets,    setValueBets]    = useState(null)
  const [vbTotal,      setVbTotal]      = useState(null)
  const [upcoming,     setUpcoming]     = useState(null)
  const [ratings,      setRatings]      = useState(null)
  const [staticLoading, setStaticLoading] = useState(true)

  const [previewMatch, setPreviewMatch] = useState(null)

  const fetchLive = useCallback(async () => {
    setLiveLoading(true)
    try {
      const { data } = await api.get('/api/live/today')
      setLiveData(Array.isArray(data.data) ? data.data : [])
      setLastRefresh(Date.now())
      setLiveError(null)
    } catch {
      setLiveError('Live data unavailable')
    } finally {
      setLiveLoading(false)
    }
  }, [])

  // Load static data once
  useEffect(() => {
    Promise.all([
      api.get('/api/live/value-bets'),
      api.get('/api/value-bets/summary'),
      api.get('/api/live/upcoming'),
      api.get('/api/ratings'),
    ])
      .then(([vbRes, summRes, upRes, ratRes]) => {
        setValueBets(vbRes.data.data ?? [])
        setVbTotal(summRes.data.data?.total_bets ?? null)
        setUpcoming(upRes.data.data ?? [])
        setRatings(ratRes.data.data ?? [])
      })
      .catch(() => {})
      .finally(() => setStaticLoading(false))
  }, [])

  // Fetch live on mount and every 60s
  useEffect(() => {
    fetchLive()
    const id = setInterval(fetchLive, 60_000)
    return () => clearInterval(id)
  }, [fetchLive])

  const liveCount  = (liveData ?? []).filter(m => ['IN_PLAY', 'PAUSED', 'LIVE'].includes(m.status)).length
  const now        = new Date()
  const dateLabel  = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-1">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            {greeting()}, <span className="text-emerald-400">FormCast</span>
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{dateLabel}</p>
        </div>
        {vbTotal != null && (
          <p className="text-xs text-gray-600 font-mono">
            <span className="text-emerald-500">{vbTotal.toLocaleString()}</span> value bets identified
          </p>
        )}
      </div>

      {/* Section 1 — Live Now (full width) */}
      <Section
        title={
          <span className="flex items-center gap-2">
            {liveCount > 0 && (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </span>
            )}
            {liveCount > 0 ? `${liveCount} Live Now` : 'Live Now'}
          </span>
        }
        action={() => onNavigate('live')}
        actionLabel={
          <span className="flex items-center gap-1">
            {lastRefresh && (
              <span className="text-gray-700 mr-1 flex items-center gap-0.5">
                <RefreshCw className="w-2.5 h-2.5" />
                {Math.round((Date.now() - lastRefresh) / 1000)}s
              </span>
            )}
            All matches
          </span>
        }
      >
        <LiveSection
          data={liveData}
          loading={liveLoading}
          error={liveError}
          lastRefresh={lastRefresh}
          onRefresh={fetchLive}
          onMatchClick={setPreviewMatch}
        />
      </Section>

      {/* Section 2 — Live Value Bets (full width) */}
      <Section
        title="Live Value Bets"
        action={() => onNavigate('value-bets')}
        actionLabel="View all"
      >
        {staticLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 text-gray-600 animate-spin" />
          </div>
        ) : valueBets?.length > 0 ? (
          <div>
            {valueBets.map((bet, i) => <ValueBetCard key={i} bet={bet} />)}
          </div>
        ) : (
          <p className="px-4 py-6 text-sm text-center text-gray-600">
            No value bets this week — refreshes Monday 6am UTC
          </p>
        )}
      </Section>

      {/* Sections 3 + 4 — side by side on large screens */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Section 3 — Upcoming Fixtures */}
        <Section
          title="Upcoming Fixtures"
          action={() => onNavigate('live')}
          actionLabel="View all"
        >
          {staticLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 text-gray-600 animate-spin" />
            </div>
          ) : upcoming?.length > 0 ? (
            <div>
              {upcoming.slice(0, 5).map(m => (
                <UpcomingRow key={m.match_id} match={m} onClick={setPreviewMatch} />
              ))}
            </div>
          ) : (
            <p className="px-4 py-6 text-sm text-center text-gray-600">No upcoming fixtures</p>
          )}
        </Section>

        {/* Section 4 — Top Rated Teams */}
        <Section
          title="Top Rated Teams"
          action={() => onNavigate('ratings')}
          actionLabel="View all"
        >
          {staticLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 text-gray-600 animate-spin" />
            </div>
          ) : ratings?.length > 0 ? (
            <div>
              {ratings.slice(0, 10).map((team, i) => (
                <RatingRow key={team.team} team={team} rank={i} />
              ))}
            </div>
          ) : (
            <p className="px-4 py-6 text-sm text-center text-gray-600">No ratings data</p>
          )}
        </Section>

      </div>

      {/* Section 5 — Model Performance */}
      <ModelPerf onNavigate={onNavigate} />

      {/* Match preview modal */}
      {previewMatch && (
        <MatchPreview match={previewMatch} onClose={() => setPreviewMatch(null)} />
      )}
    </div>
  )
}
