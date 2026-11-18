import { useState, useEffect, useCallback } from 'react'
import api from '../api'
import {
  Loader2, ArrowRight, RefreshCw,
  Radio, CloudOff, Target, CalendarClock, ListOrdered, LineChart as LineChartIcon,
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import MatchPreview from './MatchPreview'
import InfoTip from './InfoTip'
import { CHART, AXIS, GRID, TOOLTIP_STYLE } from '../chartTheme'

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

// DESIGN.md: percentages 1dp.
function pct1(v) {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function fmtShortDate(iso) {
  if (!iso) return ''
  const [, m, d] = iso.split('-')
  return `${+d} ${MONTHS[+m - 1]}`
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
        <div className="bg-[var(--foreground)]"          style={{ width: `${ph}%` }} />
        <div className="bg-[var(--muted-foreground)]/40" style={{ width: `${pd}%` }} />
        <div className="bg-[var(--muted-foreground)]"    style={{ width: `${pa}%` }} />
      </div>
      <div className="flex justify-between mt-0.5 text-[10px] tabular-nums text-[var(--muted-foreground)]">
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

function Section({ title, intro, action, actionLabel, children }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-[var(--foreground)]">{title}</h2>
          {action && (
            <button
              onClick={action}
              className="shrink-0 flex items-center gap-1 text-xs text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors"
            >
              {actionLabel}
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
        {intro && <p className="fc-explain">{intro}</p>}
      </div>
      {children}
    </div>
  )
}

// Calm, designed empty/unavailable state — faint icon, sage text, optional
// next-step hint. Never error-red, never fake preview data.
function EmptyState({ icon: Icon, title, hint, children }) {
  return (
    <div className="px-4 py-10 flex flex-col items-center text-center">
      {Icon && (
        <span className="mb-3 flex items-center justify-center w-9 h-9 rounded-full bg-[var(--muted)] border border-[var(--border)]">
          <Icon className="w-4 h-4 text-[var(--muted-foreground)]/70" strokeWidth={1.75} />
        </span>
      )}
      <p className="text-sm text-[var(--muted-foreground)]">{title}</p>
      {hint && (
        <p className="mt-1.5 text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--muted-foreground)]/60">
          {hint}
        </p>
      )}
      {children}
    </div>
  )
}

function SectionLoader() {
  return (
    <div className="flex justify-center py-8">
      <Loader2 className="w-5 h-5 text-[var(--muted-foreground)] animate-spin" />
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
    return <SectionLoader />
  }

  if (error) {
    return <EmptyState icon={CloudOff} title={error} hint="Retrying every 60s" />
  }

  if (liveMatches.length === 0) {
    return (
      <EmptyState icon={Radio} title="No matches in play right now">
        {nextUp && (
          <p className="mt-2 text-xs text-[var(--muted-foreground)]/80">
            Next: <span className="text-[var(--foreground)]">{nextUp.home_team} vs {nextUp.away_team}</span>
            {' '}at <span className="text-[var(--foreground)] tabular-nums">{fmtTime(nextUp.match_time)}</span>
          </p>
        )}
      </EmptyState>
    )
  }

  return (
    <div className="divide-y divide-[var(--border)]">
      {liveMatches.slice(0, 3).map(m => (
        <button
          key={m.match_id}
          onClick={() => onMatchClick(m)}
          className="w-full text-left px-4 py-3 hover:bg-[var(--secondary)] transition-colors"
        >
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className="flex-1 min-w-0">
              <span className="text-sm text-[var(--foreground)] font-medium truncate block">{m.home_team}</span>
            </div>
            <div className="text-center shrink-0">
              <span className="text-base font-bold text-[var(--foreground)] tabular-nums">
                {m.home_goals ?? 0} – {m.away_goals ?? 0}
              </span>
              {m.status === 'PAUSED' ? (
                <span className="block text-[10px] font-mono text-[var(--chart-3)]">HT</span>
              ) : m.minute != null && (
                <span className="block text-[10px] text-[var(--primary)] tabular-nums">{m.minute}'</span>
              )}
            </div>
            <div className="flex-1 min-w-0 text-right">
              <span className="text-sm text-[var(--foreground)] font-medium truncate block">{m.away_team}</span>
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

const OUTCOME_LABEL       = { H: 'Home', D: 'Draw', A: 'Away' }
const INTERNATIONAL_LEAGUES = new Set(['FIFA World Cup'])

// Edge meter (DESIGN.md §5) — the book's price as a sage segment, the model's
// extra probability on top of it in coral. The coral segment IS the edge:
// value_edge = value_p_model − 1/value_odds (fetch_live_odds.py). 1/odds still
// contains the bookmaker's margin, so it's labelled "book price", never "true".
function EdgeMeter({ odds, pModel, edge, size = 'sm' }) {
  if (!odds || odds <= 1 || pModel == null) return null
  const book    = 1 / odds
  const bookW   = Math.min(Math.max(book, 0), 1) * 100
  const edgeW   = Math.min(Math.max(edge ?? 0, 0), 1 - bookW / 100) * 100
  return (
    <div
      className={`flex ${size === 'lg' ? 'h-3.5' : 'h-2'} w-full rounded-full overflow-hidden bg-[var(--muted)]`}
      role="img"
      aria-label={`Book price ${pct1(book)}, model ${pct1(pModel)}, edge ${pct1(edge)}`}
    >
      <div className="bg-[var(--muted-foreground)]/45" style={{ width: `${bookW}%` }} />
      <div className="bg-[var(--primary)]"            style={{ width: `${edgeW}%` }} />
    </div>
  )
}

function ValueBetCard({ bet }) {
  const isIntl = INTERNATIONAL_LEAGUES.has(bet.league)
  const book   = bet.value_odds > 1 ? 1 / bet.value_odds : null
  return (
    <div className={`px-4 py-3 border-b border-[var(--border)] last:border-0 border-l-2 ${isIntl ? 'border-l-[var(--chart-4)]' : 'border-l-transparent'}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-xs text-[var(--foreground)] font-medium truncate">
            {bet.home_team} <span className="text-[var(--muted-foreground)]">vs</span> {bet.away_team}
          </p>
          <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5">
            {isIntl && <span className="mr-1">🌍</span>}
            {bet.league} · {bet.match_date}
            {bet.match_time ? ` · ${bet.match_time}` : ''}
          </p>
        </div>
        <span className="shrink-0 text-xs font-bold px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)]">
          {OUTCOME_LABEL[bet.value_outcome] ?? bet.value_outcome}
        </span>
      </div>
      <EdgeMeter odds={bet.value_odds} pModel={bet.value_p_model} edge={bet.value_edge} />
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-[11px] tabular-nums">
        <span className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
          <span className="w-2 h-2 rounded-sm bg-[var(--muted-foreground)]/45" />
          Book price <span className="text-[var(--foreground)]">{pct1(book)}</span>
        </span>
        <span className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
          <span className="w-2 h-2 rounded-sm bg-[var(--primary)]" />
          Edge <span className="text-[var(--chart-2)] font-semibold">+{pct1(bet.value_edge)}</span>
        </span>
        <span className="text-[var(--muted-foreground)]">Model <span className="text-[var(--foreground)]">{pct1(bet.value_p_model)}</span></span>
        <span className="text-[var(--muted-foreground)]">Odds <span className="text-[var(--foreground)]">{bet.value_odds?.toFixed(2)}</span></span>
      </div>
    </div>
  )
}

// What the pick actually backs, in words: "Millwall to win" / "Draw".
function pickLabel(bet) {
  if (bet.value_outcome === 'H') return `${bet.home_team} to win`
  if (bet.value_outcome === 'A') return `${bet.away_team} to win`
  if (bet.value_outcome === 'D') return 'Draw'
  return bet.value_outcome ?? '—'
}

// The lead: the single best-edge value bet, large, with the signature meter.
function HeroPick({ bet }) {
  const isIntl = INTERNATIONAL_LEAGUES.has(bet.league)
  const book   = bet.value_odds > 1 ? 1 / bet.value_odds : null
  return (
    <div className={`px-4 sm:px-6 py-5 sm:py-6 border-b border-[var(--border)] border-l-2 ${isIntl ? 'border-l-[var(--chart-4)]' : 'border-l-[var(--primary)]'}`}>
      <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--primary)] mb-3">
        Top pick · biggest edge
      </p>

      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="text-lg sm:text-xl font-semibold text-[var(--foreground)] leading-tight">
            {bet.home_team} <span className="text-[var(--muted-foreground)] font-normal">vs</span> {bet.away_team}
          </h3>
          <p className="text-xs text-[var(--muted-foreground)] mt-1">
            {isIntl && <span className="mr-1">🌍</span>}
            {bet.league} · {fmtDate(bet.match_date)}
            {bet.match_time ? ` · ${fmtTime(bet.match_time)}` : ''}
          </p>
        </div>
        <span className="self-start shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)]">
          {pickLabel(bet)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--muted-foreground)]">Model<InfoTip term="model" /></p>
          <p className="text-xl sm:text-2xl font-semibold tabular-nums text-[var(--foreground)]">{pct1(bet.value_p_model)}</p>
        </div>
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--muted-foreground)]">Book price<InfoTip term="book-price" /></p>
          <p className="text-xl sm:text-2xl font-semibold tabular-nums text-[var(--muted-foreground)]">{pct1(book)}</p>
        </div>
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--muted-foreground)]">Edge<InfoTip term="edge" /></p>
          <p className="text-xl sm:text-2xl font-semibold tabular-nums text-[var(--chart-2)]">+{pct1(bet.value_edge)}</p>
        </div>
      </div>

      <EdgeMeter odds={bet.value_odds} pModel={bet.value_p_model} edge={bet.value_edge} size="lg" />

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 mt-2 text-[11px] tabular-nums text-[var(--muted-foreground)]">
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-[var(--muted-foreground)]/45" />Book price</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-[var(--primary)]" />Edge</span>
        </span>
        <span className="inline-flex items-center flex-wrap">
          Odds<InfoTip term="odds" />&nbsp;<span className="text-[var(--foreground)]">{bet.value_odds?.toFixed(2)}</span>
          {bet.value_bookmaker && <> · {bet.value_bookmaker}</>}
        </span>
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
      className="w-full text-left px-4 py-2.5 border-b border-[var(--border)] last:border-0 hover:bg-[var(--secondary)] transition-colors"
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="min-w-0 flex-1">
          <p className="text-xs text-[var(--foreground)] font-medium truncate">
            {homeDisplay} <span className="text-[var(--muted-foreground)]">vs</span> {awayDisplay}
          </p>
          <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5">
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
    <div className={`flex items-center gap-3 px-4 py-2 border-b border-[var(--border)] last:border-0 ${isMedal ? 'bg-[var(--muted)]' : ''}`}>
      <span className="w-6 text-center text-xs font-mono text-[var(--muted-foreground)] shrink-0">
        {isMedal ? MEDAL[rank] : `${rank + 1}`}
      </span>
      <span className={`flex-1 text-[13px] truncate font-medium ${isMedal ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'}`}>
        {team.team}
      </span>
      <span className={`text-[13px] font-mono tabular-nums font-semibold shrink-0 ${isMedal ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'}`}>
        {team.elo_rating?.toFixed(0)}
      </span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Track record — verifiable record only. No ROI / CLV / profit / live hit rate.
// ---------------------------------------------------------------------------

// Cumulative count of settled live predictions, by MATCH DATE. Not settled_at:
// every settled row currently shares one settled_at (a one-off backfill on
// 2026-11-11), which would plot as a single vertical step. Count only.
function buildSettledSeries(rows) {
  const perDay = new Map()
  for (const r of rows ?? []) {
    if ((r.correct !== '0' && r.correct !== '1') || !r.match_date) continue
    const day = r.match_date.slice(0, 10)
    perDay.set(day, (perDay.get(day) ?? 0) + 1)
  }
  let total = 0
  return [...perDay.keys()].sort().map(date => {
    total += perDay.get(date)
    return { date, settled: total }
  })
}

function SettledTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { date, settled } = payload[0].payload
  return (
    <div style={TOOLTIP_STYLE}>
      <p style={{ color: CHART.axis, fontSize: 10 }}>{fmtShortDate(date)}</p>
      <p className="tabular-nums">{settled.toLocaleString()} settled</p>
    </div>
  )
}

function SettledChart({ log }) {
  if (log.status === 'loading') return <SectionLoader />
  if (log.status === 'error' || !log.series?.length) {
    return (
      <EmptyState
        icon={LineChartIcon}
        title={log.status === 'error' ? 'Prediction log unavailable' : 'No settled predictions yet'}
        hint="Every prediction is logged — win or lose"
      />
    )
  }
  return (
    <div className="h-44 sm:h-52">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={log.series} margin={{ top: 6, right: 4, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="settledFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={CHART.coral} stopOpacity={0.28} />
              <stop offset="100%" stopColor={CHART.coral} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="date" {...AXIS} tickFormatter={fmtShortDate} minTickGap={32} />
          <YAxis {...AXIS} width={40} allowDecimals={false} />
          <Tooltip content={<SettledTooltip />} cursor={{ stroke: CHART.grid }} />
          <Area
            type="stepAfter"
            dataKey="settled"
            stroke={CHART.coral}
            strokeWidth={1.75}
            fill="url(#settledFill)"
            isAnimationActive
            animationDuration={700}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function Stat({ value, label, tip, color = 'text-[var(--foreground)]', hero = false }) {
  return (
    <div className="py-3">
      <p className={`${hero ? 'text-3xl sm:text-4xl' : 'text-xl'} font-black font-mono tabular-nums leading-none ${color}`}>
        {value}
      </p>
      <p className="text-[10px] font-mono text-[var(--muted-foreground)] uppercase tracking-[0.15em] mt-1.5">
        {label}{tip && <InfoTip term={tip} />}
      </p>
    </div>
  )
}

function TrackRecord({ log, onNavigate }) {
  const settled = log.summary?.settled
  const pending = log.summary?.pending
  return (
    <section className="bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="px-4 sm:px-6 py-3 border-b border-[var(--border)]">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-[var(--foreground)]">Track Record</h2>
          <button
            onClick={() => onNavigate('backtest')}
            className="flex items-center gap-1 text-xs text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors"
          >
            Full backtest <ArrowRight className="w-3 h-3" />
          </button>
        </div>
        <p className="fc-explain">
          Past accuracy: our Elo baseline’s backtest, and the live prediction log. They’re labelled separately — we don’t blend them.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,18rem)_1fr]">
        {/* Stats — two sources, each labelled so they don't read as one set */}
        <div className="px-4 sm:px-6 py-3 lg:border-r border-b lg:border-b-0 border-[var(--border)]">
          <Stat hero value="64.4%" label="Hit rate · Elo model · 26-27 backtest · non-draw" tip="hit-rate" color="text-[var(--primary)]" />
          <div className="grid grid-cols-2 gap-x-4 border-t border-[var(--border)] mt-1">
            <Stat value={settled != null ? settled.toLocaleString() : '—'} label="Settled · live log" tip="settled" />
            <Stat
              value={pending != null ? pending.toLocaleString() : '—'}
              label="Pending · live log"
              tip="pending"
              color={pending > 0 ? 'text-[var(--chart-3)]' : 'text-[var(--foreground)]'}
            />
            <Stat value="128,602" label="Matches in database · ensemble learns from 50,298" tip="matches-modelled" />
            <Stat value="11" label="Leagues covered" />
          </div>
        </div>

        {/* Chart */}
        <div className="px-4 sm:px-6 pt-4 pb-3 min-w-0">
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--muted-foreground)] mb-2">
            Predictions settled over time · live log
          </p>
          <SettledChart log={log} />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 sm:px-6 py-3 border-t border-[var(--border)]">
        <p className="text-xs text-[var(--muted-foreground)]">
          Every settled prediction logged before kick-off — win or lose.
        </p>
        <button
          onClick={() => onNavigate('prediction-log')}
          className="self-start sm:self-auto flex items-center gap-1 text-xs font-medium text-[var(--foreground)] hover:text-[var(--primary)] transition-colors"
        >
          View the full ledger <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

const TOP_PICKS = 5 // 1 hero + 4 compact rows; the rest live behind "View all"

export default function Dashboard({ onNavigate }) {
  const [liveData,     setLiveData]     = useState(null)
  const [liveError,    setLiveError]    = useState(null)
  const [liveLoading,  setLiveLoading]  = useState(true)
  const [lastRefresh,  setLastRefresh]  = useState(null)

  const [valueBets,    setValueBets]    = useState(null)
  const [upcoming,     setUpcoming]     = useState(null)
  const [ratings,      setRatings]      = useState(null)
  const [staticLoading, setStaticLoading] = useState(true)

  // Live prediction log: drives the settled chart + settled/pending stats.
  const [log, setLog] = useState({ status: 'loading', series: null, summary: null })

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
      api.get('/api/live/upcoming'),
      api.get('/api/ratings'),
    ])
      .then(([vbRes, upRes, ratRes]) => {
        setValueBets(vbRes.data.data ?? [])
        setUpcoming(upRes.data.data ?? [])
        setRatings(ratRes.data.data ?? [])
      })
      .catch(() => {})
      .finally(() => setStaticLoading(false))
  }, [])

  // Prediction log — separate so a failure here never blanks the picks.
  useEffect(() => {
    let cancelled = false
    api.get('/api/predictions/log')
      .then(res => {
        if (cancelled) return
        setLog({
          status: 'ready',
          series: buildSettledSeries(res.data?.data),
          // Only the record counts are kept — the summary's hit_rate is not shown.
          summary: {
            settled: res.data?.summary?.settled ?? null,
            pending: res.data?.summary?.pending ?? null,
          },
        })
      })
      .catch(() => { if (!cancelled) setLog({ status: 'error', series: null, summary: null }) })
    return () => { cancelled = true }
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

  // The API already sorts by edge; sort a copy anyway so the hero is always the max.
  const picks      = [...(valueBets ?? [])].sort((a, b) => (b.value_edge ?? 0) - (a.value_edge ?? 0))
  const [hero, ...rest] = picks.slice(0, TOP_PICKS)
  const vbCount    = picks.length
  const settled    = log.summary?.settled

  return (
    <div className="fc-page space-y-6">

      {/* Greeting + one-glance summary */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--foreground)]">
            {greeting()}, FormCast
          </h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-0.5">{dateLabel}</p>
        </div>
        {(vbCount > 0 || settled != null) && (
          <p className="text-xs text-[var(--muted-foreground)] font-mono tabular-nums">
            {vbCount > 0 && (
              <>
                <span className="text-[var(--foreground)]">{vbCount}</span> upcoming value bets
                {' · '}best edge <span className="text-[var(--chart-2)]">+{pct1(hero?.value_edge)}</span>
              </>
            )}
            {vbCount > 0 && settled != null && ' · '}
            {settled != null && (
              <><span className="text-[var(--foreground)]">{settled.toLocaleString()}</span> settled</>
            )}
          </p>
        )}
      </div>

      {/* Lead — best value, curated: 1 hero + 4 rows, the rest behind a click */}
      <Section
        title={<span className="inline-flex items-center">Best Value · Upcoming<InfoTip term="value-bet" /></span>}
        intro="Matches where our model disagrees with the bookmaker — ranked by the size of that gap."
        action={() => onNavigate('value-bets')}
        actionLabel="View all"
      >
        {staticLoading ? (
          <SectionLoader />
        ) : hero ? (
          <div>
            <HeroPick bet={hero} />
            {rest.map((bet, i) => <ValueBetCard key={i} bet={bet} />)}
            {vbCount > TOP_PICKS && (
              <button
                onClick={() => onNavigate('value-bets')}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-3 border-t border-[var(--border)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--primary)] hover:bg-[var(--secondary)] transition-colors"
              >
                View all {vbCount} value bets <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        ) : (
          <EmptyState icon={Target} title="No value bets this week" hint="Refreshes Monday 6am UTC" />
        )}
      </Section>

      {/* Track record — the verifiable record, as a feature */}
      <TrackRecord log={log} onNavigate={onNavigate} />

      {/* Supporting glances — compact, secondary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">

        <Section
          title={
            <span className="flex items-center gap-2">
              {liveCount > 0 && (
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] animate-pulse" />
              )}
              {liveCount > 0 ? `${liveCount} Live Now` : 'Live Now'}
            </span>
          }
          action={() => onNavigate('live')}
          actionLabel={
            <span className="flex items-center gap-1">
              {lastRefresh && (
                <span className="text-[var(--muted-foreground)]/60 mr-1 flex items-center gap-0.5">
                  <RefreshCw className="w-2.5 h-2.5" />
                  {Math.round((Date.now() - lastRefresh) / 1000)}s
                </span>
              )}
              All
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

        <Section
          title="Upcoming Fixtures"
          action={() => onNavigate('live')}
          actionLabel="View all"
        >
          {staticLoading ? (
            <SectionLoader />
          ) : upcoming?.length > 0 ? (
            <div>
              {upcoming.slice(0, 5).map(m => (
                <UpcomingRow key={m.match_id} match={m} onClick={setPreviewMatch} />
              ))}
            </div>
          ) : (
            <EmptyState icon={CalendarClock} title="No upcoming fixtures" hint="Checks the next 7 days" />
          )}
        </Section>

        <Section
          title="Top Rated Teams"
          action={() => onNavigate('ratings')}
          actionLabel="View all"
        >
          {staticLoading ? (
            <SectionLoader />
          ) : ratings?.length > 0 ? (
            <div>
              {ratings.slice(0, 10).map((team, i) => (
                <RatingRow key={team.team} team={team} rank={i} />
              ))}
            </div>
          ) : (
            <EmptyState icon={ListOrdered} title="No ratings data" />
          )}
        </Section>

      </div>

      {/* Match preview modal */}
      {previewMatch && (
        <MatchPreview match={previewMatch} onClose={() => setPreviewMatch(null)} />
      )}
    </div>
  )
}
