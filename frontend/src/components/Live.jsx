import { useState, useEffect, useCallback } from 'react'
import api from '../api'
import { Loader2, RefreshCw, Zap } from 'lucide-react'
import MatchPreview from './MatchPreview'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(v) {
  return v == null ? '—' : `${(v * 100).toFixed(0)}%`
}

function fmtTime(t) {
  if (!t) return ''
  return t.slice(0, 5)
}

function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

function groupBy(arr, key) {
  return arr.reduce((acc, item) => {
    const k = item[key] ?? 'Unknown'
    if (!acc[k]) acc[k] = []
    acc[k].push(item)
    return acc
  }, {})
}

// ---------------------------------------------------------------------------
// Probability bar — green | gray | red
// ---------------------------------------------------------------------------

function ProbBar({ pHome, pDraw, pAway }) {
  const ph = Math.round((pHome ?? 0) * 100)
  const pd = Math.round((pDraw ?? 0) * 100)
  const pa = Math.round((pAway ?? 0) * 100)

  return (
    <div className="w-full">
      <div className="flex h-2 rounded-full overflow-hidden bg-gray-800">
        <div className="bg-emerald-500 transition-all duration-700" style={{ width: `${ph}%` }} />
        <div className="bg-gray-500 transition-all duration-700"   style={{ width: `${pd}%` }} />
        <div className="bg-red-500 transition-all duration-700"    style={{ width: `${pa}%` }} />
      </div>
      <div className="flex justify-between mt-0.5 text-[11px] tabular-nums">
        <span className="text-emerald-400">{ph}%</span>
        <span className="text-gray-400">{pd}%</span>
        <span className="text-red-400">{pa}%</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Score / status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }) {
  const map = {
    IN_PLAY:   { cls: 'bg-emerald-500/20 text-emerald-400', label: 'Live' },
    PAUSED:    { cls: 'bg-yellow-500/20 text-yellow-400',   label: 'HT' },
    LIVE:      { cls: 'bg-emerald-500/20 text-emerald-400', label: 'Live' },
    FINISHED:  { cls: 'bg-gray-700 text-gray-400',          label: 'FT' },
    SCHEDULED: { cls: 'bg-blue-500/20 text-blue-400',       label: 'Soon' },
    TIMED:     { cls: 'bg-blue-500/20 text-blue-400',       label: 'Fixture' },
    POSTPONED: { cls: 'bg-gray-700 text-gray-500',          label: 'PPD' },
    CANCELLED: { cls: 'bg-gray-700 text-gray-500',          label: 'Canc.' },
  }
  const { cls, label } = map[status] ?? { cls: 'bg-gray-700 text-gray-400', label: status }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{label}</span>
  )
}

// ---------------------------------------------------------------------------
// Single match row
// ---------------------------------------------------------------------------

function MatchRow({ match, showProbs = true, onClick }) {
  const isLive    = ['IN_PLAY', 'PAUSED', 'LIVE'].includes(match.status)
  const isFinished = match.status === 'FINISHED'
  const hasScore  = match.home_goals != null && match.away_goals != null

  return (
    <div
      onClick={() => onClick?.(match)}
      className={`flex flex-col gap-2 p-3 rounded-lg border transition-colors cursor-pointer ${
        isLive
          ? 'border-emerald-800/60 bg-emerald-950/20 hover:bg-emerald-950/30'
          : 'border-gray-800 bg-gray-900/50 hover:bg-gray-800/60'
      }`}
    >
      {/* Top row: teams + score/time */}
      <div className="flex items-center justify-between gap-4">
        {/* Home team */}
        <div className="flex-1 min-w-0">
          <span className={`text-sm font-medium truncate block ${
            isFinished && hasScore && match.home_goals > match.away_goals
              ? 'text-white'
              : isLive
              ? 'text-white'
              : 'text-gray-200'
          }`}>
            {match.home_team}
          </span>
          <span className="text-[11px] text-gray-500">
            Elo {match.home_elo}
          </span>
        </div>

        {/* Score / kickoff */}
        <div className="flex flex-col items-center gap-0.5 shrink-0 w-24">
          {hasScore ? (
            <span className={`text-lg font-bold tabular-nums ${isLive ? 'text-emerald-400' : 'text-white'}`}>
              {match.home_goals} – {match.away_goals}
            </span>
          ) : (
            <span className="text-sm text-gray-400 tabular-nums">
              {fmtTime(match.match_time)}
            </span>
          )}
          <div className="flex items-center gap-1">
            <StatusBadge status={match.status} />
            {isLive && match.minute != null && (
              <span className="text-xs text-emerald-400 tabular-nums">{match.minute}'</span>
            )}
          </div>
        </div>

        {/* Away team */}
        <div className="flex-1 min-w-0 text-right">
          <span className={`text-sm font-medium truncate block ${
            isFinished && hasScore && match.away_goals > match.home_goals
              ? 'text-white'
              : isLive
              ? 'text-white'
              : 'text-gray-200'
          }`}>
            {match.away_team}
          </span>
          <span className="text-[11px] text-gray-500">
            Elo {match.away_elo}
          </span>
        </div>
      </div>

      {/* Probability bar */}
      {showProbs && !['POSTPONED', 'CANCELLED'].includes(match.status) && (
        <ProbBar pHome={match.p_home} pDraw={match.p_draw} pAway={match.p_away} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Competition section
// ---------------------------------------------------------------------------

function CompSection({ competition, matches, showProbs, onMatchClick }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2 px-1">
        {competition}
      </h3>
      <div className="flex flex-col gap-2">
        {matches.map(m => (
          <MatchRow key={m.match_id} match={m} showProbs={showProbs} onClick={onMatchClick} />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Competition filter dropdown
// ---------------------------------------------------------------------------

function CompFilter({ competitions, value, onChange }) {
  if (competitions.length <= 2) return null
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
    >
      {competitions.map(c => <option key={c} value={c}>{c}</option>)}
    </select>
  )
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

const TABS = [
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'today',    label: 'Today' },
  { id: 'live',     label: 'Live Now' },
]

// ---------------------------------------------------------------------------
// Live Now panel
// ---------------------------------------------------------------------------

function LiveNowPanel({ data, loading, error, lastRefresh, onRefresh, onMatchClick }) {
  if (loading) return <Spinner />
  if (error)   return <ErrorMsg msg={error} />
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-500 py-16">
        No matches currently in play.
      </div>
    )
  }

  const grouped = groupBy(data, 'competition')

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span className="text-sm text-emerald-400 font-medium">{data.length} live match{data.length !== 1 ? 'es' : ''}</span>
        </div>
        <RefreshButton lastRefresh={lastRefresh} onRefresh={onRefresh} />
      </div>
      {Object.entries(grouped).map(([comp, matches]) => (
        <CompSection key={comp} competition={comp} matches={matches} showProbs onMatchClick={onMatchClick} />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Today panel
// ---------------------------------------------------------------------------

function TodayPanel({ data, loading, error, selectedComp, setSelectedComp, onMatchClick }) {
  if (loading) return <Spinner />
  if (error)   return <ErrorMsg msg={error} />
  if (!data || data.length === 0) {
    return <div className="text-center text-gray-500 py-16">No matches today.</div>
  }

  const competitions = ['ALL', ...Array.from(new Set(data.map(m => m.competition))).sort()]
  const visible = selectedComp === 'ALL' ? data : data.filter(m => m.competition === selectedComp)
  const grouped = groupBy(visible, 'competition')

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          <span className="text-white font-medium">{visible.length}</span>
          {visible.length !== data.length && ` of ${data.length}`}
          {' '}matches today
        </p>
        <CompFilter competitions={competitions} value={selectedComp} onChange={setSelectedComp} />
      </div>
      {Object.entries(grouped).map(([comp, matches]) => (
        <CompSection key={comp} competition={comp} matches={matches} showProbs onMatchClick={onMatchClick} />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Upcoming panel — grouped by date then competition
// ---------------------------------------------------------------------------

function UpcomingPanel({ data, loading, error, selectedComp, setSelectedComp, onMatchClick }) {
  if (loading) return <Spinner />
  if (error)   return <ErrorMsg msg={error} />
  if (!data || data.length === 0) {
    return <div className="text-center text-gray-500 py-16">No upcoming fixtures found.</div>
  }

  const competitions = ['ALL', ...Array.from(new Set(data.map(m => m.competition))).sort()]
  const visible = selectedComp === 'ALL' ? data : data.filter(m => m.competition === selectedComp)
  const byDate = groupBy(visible, 'match_date')

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          <span className="text-white font-medium">{visible.length}</span>
          {visible.length !== data.length && ` of ${data.length}`}
          {' '}fixtures
        </p>
        <CompFilter competitions={competitions} value={selectedComp} onChange={setSelectedComp} />
      </div>
      {Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b)).map(([d, dayMatches]) => {
        const byComp = groupBy(dayMatches, 'competition')
        return (
          <div key={d}>
            <h2 className="text-sm font-semibold text-white mb-3 border-b border-gray-800 pb-1">
              {fmtDate(d)}
              <span className="text-gray-500 font-normal ml-2 text-xs">{dayMatches.length} match{dayMatches.length !== 1 ? 'es' : ''}</span>
            </h2>
            <div className="flex flex-col gap-4">
              {Object.entries(byComp).map(([comp, matches]) => (
                <CompSection key={comp} competition={comp} matches={matches} showProbs onMatchClick={onMatchClick} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared small components
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
    </div>
  )
}

function ErrorMsg({ msg }) {
  return (
    <div className="text-center text-red-400 py-16 text-sm">
      {msg ?? 'Failed to load data'}
    </div>
  )
}

function RefreshButton({ lastRefresh, onRefresh }) {
  const ago = lastRefresh ? Math.round((Date.now() - lastRefresh) / 1000) : null
  return (
    <button
      onClick={onRefresh}
      className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
    >
      <RefreshCw className="w-3.5 h-3.5" />
      {ago != null ? `${ago}s ago` : 'Refresh'}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Live() {
  const [tab, setTab]             = useState('upcoming')
  const [selectedComp, setSelectedComp] = useState('ALL')
  const [previewMatch, setPreviewMatch] = useState(null)

  const [liveData, setLiveData]       = useState(null)
  const [todayData, setTodayData]     = useState(null)
  const [upcomingData, setUpcomingData] = useState(null)

  const [liveLoading, setLiveLoading]       = useState(false)
  const [todayLoading, setTodayLoading]     = useState(false)
  const [upcomingLoading, setUpcomingLoading] = useState(false)

  const [liveError, setLiveError]       = useState(null)
  const [todayError, setTodayError]     = useState(null)
  const [upcomingError, setUpcomingError] = useState(null)

  const [liveLastRefresh, setLiveLastRefresh] = useState(null)

  const fetchLive = useCallback(async () => {
    setLiveLoading(true)
    setLiveError(null)
    try {
      const { data } = await api.get('/api/live/now')
      setLiveData(data.data)
      setLiveLastRefresh(Date.now())
    } catch (e) {
      setLiveError(e?.response?.data?.error ?? 'Network error')
    } finally {
      setLiveLoading(false)
    }
  }, [])

  const fetchToday = useCallback(async () => {
    setTodayLoading(true)
    setTodayError(null)
    try {
      const { data } = await api.get('/api/live/today')
      setTodayData(data.data)
    } catch (e) {
      setTodayError(e?.response?.data?.error ?? 'Network error')
    } finally {
      setTodayLoading(false)
    }
  }, [])

  const fetchUpcoming = useCallback(async () => {
    setUpcomingLoading(true)
    setUpcomingError(null)
    try {
      const { data } = await api.get('/api/live/upcoming')
      setUpcomingData(data.data)
    } catch (e) {
      setUpcomingError(e?.response?.data?.error ?? 'Network error')
    } finally {
      setUpcomingLoading(false)
    }
  }, [])

  useEffect(() => { setSelectedComp('ALL') }, [tab])

  // Initial fetch per tab
  useEffect(() => {
    if (tab === 'live'     && liveData === null)     fetchLive()
    if (tab === 'today'    && todayData === null)    fetchToday()
    if (tab === 'upcoming' && upcomingData === null) fetchUpcoming()
  }, [tab]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh Live Now every 60s
  useEffect(() => {
    if (tab !== 'live') return
    const id = setInterval(fetchLive, 60_000)
    return () => clearInterval(id)
  }, [tab, fetchLive])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Live & Upcoming</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Powered by football-data.org · Elo win probabilities · 60s cache
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 rounded-lg p-1 w-fit">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === id
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {id === 'live' && liveData?.length > 0 && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5 align-middle" />
            )}
            {label}
          </button>
        ))}
      </div>

      {/* Panel */}
      <div>
        {tab === 'live' && (
          <LiveNowPanel
            data={liveData}
            loading={liveLoading}
            error={liveError}
            lastRefresh={liveLastRefresh}
            onRefresh={fetchLive}
            onMatchClick={setPreviewMatch}
          />
        )}
        {tab === 'today' && (
          <TodayPanel
            data={todayData}
            loading={todayLoading}
            error={todayError}
            selectedComp={selectedComp}
            setSelectedComp={setSelectedComp}
            onMatchClick={setPreviewMatch}
          />
        )}
        {tab === 'upcoming' && (
          <UpcomingPanel
            data={upcomingData}
            loading={upcomingLoading}
            error={upcomingError}
            selectedComp={selectedComp}
            setSelectedComp={setSelectedComp}
            onMatchClick={setPreviewMatch}
          />
        )}
      </div>

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
