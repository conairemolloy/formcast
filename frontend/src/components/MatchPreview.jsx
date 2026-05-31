import { useState, useEffect } from 'react'
import api from '../api'
import { X, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(v, decimals = 0) {
  if (v == null) return '—'
  return `${(v * 100).toFixed(decimals)}%`
}

function FormBadge({ result }) {
  const map = {
    W: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    D: 'bg-gray-700/60 text-gray-300 border border-gray-600/30',
    L: 'bg-red-500/20 text-red-400 border border-red-500/30',
  }
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-[11px] font-bold ${map[result] ?? 'bg-gray-700 text-gray-400'}`}>
      {result}
    </span>
  )
}

function StatBox({ label, value }) {
  return (
    <div className="flex flex-col items-center bg-gray-800/50 rounded-lg px-3 py-2 min-w-0">
      <span className="text-[10px] text-gray-500 uppercase tracking-wider whitespace-nowrap">{label}</span>
      <span className="text-sm font-semibold text-white tabular-nums mt-0.5">{value ?? '—'}</span>
    </div>
  )
}

function SectionHeader({ icon, title }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-emerald-400">{icon}</span>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">{title}</h3>
    </div>
  )
}

function Divider() {
  return <div className="border-t border-gray-800 my-5" />
}

// ---------------------------------------------------------------------------
// Section 1 — Win probabilities
// ---------------------------------------------------------------------------

function WinProbSection({ d }) {
  const ph = Math.round((d.p_home ?? 0) * 100)
  const pd = Math.round((d.p_draw ?? 0) * 100)
  const pa = Math.round((d.p_away ?? 0) * 100)

  return (
    <div>
      <SectionHeader icon="⚽" title="Win Probabilities" />

      {/* Elo ratings */}
      <div className="flex justify-between text-[11px] text-gray-500 mb-3">
        <span>Elo <span className="text-gray-300 font-medium">{d.home_elo}</span></span>
        <span>Elo <span className="text-gray-300 font-medium">{d.away_elo}</span></span>
      </div>

      {/* Probability bars */}
      <div className="flex h-8 rounded-lg overflow-hidden mb-2">
        <div
          className="flex items-center justify-center text-xs font-bold text-white bg-emerald-600 transition-all"
          style={{ width: `${ph}%` }}
        >
          {ph >= 12 ? `${ph}%` : ''}
        </div>
        <div
          className="flex items-center justify-center text-xs font-bold text-white bg-gray-600 transition-all"
          style={{ width: `${pd}%` }}
        >
          {pd >= 10 ? `${pd}%` : ''}
        </div>
        <div
          className="flex items-center justify-center text-xs font-bold text-white bg-red-600 transition-all"
          style={{ width: `${pa}%` }}
        >
          {pa >= 12 ? `${pa}%` : ''}
        </div>
      </div>

      <div className="flex justify-between text-[11px]">
        <div className="flex flex-col items-start gap-0.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block mr-1" />
          <span className="text-emerald-400 font-semibold">{ph}%</span>
          <span className="text-gray-500">Home win</span>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <span className="w-2 h-2 rounded-full bg-gray-500 inline-block mr-1" />
          <span className="text-gray-300 font-semibold">{pd}%</span>
          <span className="text-gray-500">Draw</span>
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <span className="w-2 h-2 rounded-full bg-red-500 inline-block mr-1" />
          <span className="text-red-400 font-semibold">{pa}%</span>
          <span className="text-gray-500">Away win</span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 2 — Goals markets
// ---------------------------------------------------------------------------

function GoalsSection({ goals }) {
  const ou = goals.over_under ?? {}

  return (
    <div>
      <SectionHeader icon="📊" title="Goals Markets" />

      <div className="grid grid-cols-2 gap-4">
        {/* Over / Under table */}
        <div>
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">Over / Under</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500">
                <th className="text-left font-normal pb-1">Market</th>
                <th className="text-right font-normal pb-1">Over</th>
                <th className="text-right font-normal pb-1">Under</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {['0.5', '1.5', '2.5', '3.5'].map(t => (
                <tr key={t}>
                  <td className="py-1 text-gray-400">{t} goals</td>
                  <td className="py-1 text-right text-emerald-400 font-medium tabular-nums">{pct(ou[t]?.over)}</td>
                  <td className="py-1 text-right text-red-400 font-medium tabular-nums">{pct(ou[t]?.under)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* BTTS + to score */}
        <div className="flex flex-col gap-2">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Both Teams Score</p>
          <div className="flex gap-2">
            <div className="flex-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-emerald-400 tabular-nums">{pct(goals.btts)}</div>
              <div className="text-[10px] text-gray-500">Yes</div>
            </div>
            <div className="flex-1 bg-gray-800/50 rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-gray-300 tabular-nums">{pct(1 - (goals.btts ?? 0))}</div>
              <div className="text-[10px] text-gray-500">No</div>
            </div>
          </div>

          <p className="text-[10px] uppercase tracking-wider text-gray-500 mt-1">Team to Score</p>
          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex justify-between items-center bg-gray-800/40 rounded px-2 py-1.5">
              <span className="text-gray-400">Home</span>
              <span className="font-semibold text-white tabular-nums">{pct(goals.home_to_score)}</span>
            </div>
            <div className="flex justify-between items-center bg-gray-800/40 rounded px-2 py-1.5">
              <span className="text-gray-400">Away</span>
              <span className="font-semibold text-white tabular-nums">{pct(goals.away_to_score)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 3 — Top correct scores
// ---------------------------------------------------------------------------

function CorrectScoreSection({ goals }) {
  const top = goals.top_scores ?? []
  const maxProb = top[0]?.prob ?? 1

  return (
    <div>
      <SectionHeader icon="🎯" title="Most Likely Scores" />
      <div className="grid grid-cols-4 gap-1.5">
        {top.map((item, i) => {
          const isTop = i === 0
          return (
            <div
              key={item.score}
              className={`relative flex flex-col items-center justify-center rounded-lg py-2.5 px-1 border transition-colors ${
                isTop
                  ? 'bg-emerald-500/15 border-emerald-500/40 ring-1 ring-emerald-500/20'
                  : 'bg-gray-800/40 border-gray-700/50'
              }`}
            >
              {isTop && (
                <span className="absolute -top-1.5 left-1/2 -translate-x-1/2 text-[9px] bg-emerald-500 text-white rounded px-1 font-semibold leading-tight">
                  TOP
                </span>
              )}
              <span className={`text-sm font-bold tabular-nums ${isTop ? 'text-emerald-300' : 'text-white'}`}>
                {item.score}
              </span>
              <span className="text-[11px] text-gray-400 tabular-nums mt-0.5">{pct(item.prob, 1)}</span>
              {/* Mini probability bar */}
              <div className="w-full mt-1.5 h-0.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${isTop ? 'bg-emerald-500' : 'bg-gray-500'}`}
                  style={{ width: `${Math.round((item.prob / maxProb) * 100)}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 4 — Corners markets
// ---------------------------------------------------------------------------

function MarketsTable({ rows }) {
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-gray-500">
          <th className="text-left font-normal pb-1.5">Line</th>
          <th className="text-right font-normal pb-1.5">Over</th>
          <th className="text-right font-normal pb-1.5">Under</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-800">
        {rows.map(({ label, over }) => (
          <tr key={label}>
            <td className="py-1.5 text-gray-400">{label}</td>
            <td className="py-1.5 text-right text-emerald-400 font-medium tabular-nums">
              {over != null ? pct(over) : '—'}
            </td>
            <td className="py-1.5 text-right text-red-400 font-medium tabular-nums">
              {over != null ? pct(1 - over) : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function TeamAvgRow({ homeTeam, awayTeam, homeAvg, awayAvg, totalAvg }) {
  return (
    <div className="grid grid-cols-3 gap-2 mb-4">
      <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 truncate">{homeTeam}</p>
        <p className="text-sm font-semibold text-white tabular-nums">{homeAvg ?? '—'}</p>
        <p className="text-[10px] text-gray-600">avg / game</p>
      </div>
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5 text-center">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Expected</p>
        <p className="text-sm font-bold text-emerald-400 tabular-nums">{totalAvg ?? '—'}</p>
        <p className="text-[10px] text-gray-600">total</p>
      </div>
      <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 truncate">{awayTeam}</p>
        <p className="text-sm font-semibold text-white tabular-nums">{awayAvg ?? '—'}</p>
        <p className="text-[10px] text-gray-600">avg / game</p>
      </div>
    </div>
  )
}

function CornersSection({ corners, homeTeam, awayTeam }) {
  const hasData = corners?.total_avg != null

  return (
    <div>
      <SectionHeader icon="⚑" title="Corners Markets" />
      {!hasData ? (
        <p className="text-xs text-gray-600">Insufficient data for current season.</p>
      ) : (
        <>
          <TeamAvgRow
            homeTeam={homeTeam} awayTeam={awayTeam}
            homeAvg={corners.home_avg} awayAvg={corners.away_avg} totalAvg={corners.total_avg}
          />
          <MarketsTable rows={[
            { label: '8.5 corners',  over: corners.over_8_5 },
            { label: '9.5 corners',  over: corners.over_9_5 },
            { label: '10.5 corners', over: corners.over_10_5 },
          ]} />
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 5 — Cards markets
// ---------------------------------------------------------------------------

function CardsSection({ cards, homeTeam, awayTeam }) {
  const hasData = cards?.total_avg != null

  return (
    <div>
      <SectionHeader icon="🟨" title="Cards Markets" />
      {!hasData ? (
        <p className="text-xs text-gray-600">Insufficient data for current season.</p>
      ) : (
        <>
          <TeamAvgRow
            homeTeam={homeTeam} awayTeam={awayTeam}
            homeAvg={cards.home_avg} awayAvg={cards.away_avg} totalAvg={cards.total_avg}
          />
          <MarketsTable rows={[
            { label: '2.5 cards', over: cards.over_2_5 },
            { label: '3.5 cards', over: cards.over_3_5 },
            { label: '4.5 cards', over: cards.over_4_5 },
          ]} />
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 6 — Recent form
// ---------------------------------------------------------------------------

function FormColumn({ teamName, form }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-[11px] font-semibold text-gray-300 truncate mb-2">{teamName}</p>

      {/* Form letters */}
      {form.form?.length > 0 ? (
        <div className="flex gap-1 mb-3">
          {form.form.map((r, i) => <FormBadge key={i} result={r} />)}
        </div>
      ) : (
        <p className="text-[11px] text-gray-600 mb-3">No data</p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-1.5">
        <StatBox label="Scored" value={form.avg_scored} />
        <StatBox label="Conceded" value={form.avg_conceded} />
        <StatBox label="Corners" value={form.avg_corners} />
        <StatBox label="Yellows" value={form.avg_yellows} />
      </div>
    </div>
  )
}

function RecentFormSection({ homeTeam, awayTeam, homeForm, awayForm }) {
  return (
    <div>
      <SectionHeader icon="📈" title="Recent Form (last 5)" />
      <div className="flex gap-4">
        <FormColumn teamName={homeTeam} form={homeForm} />
        <div className="w-px bg-gray-800 self-stretch" />
        <FormColumn teamName={awayTeam} form={awayForm} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 5 — Head to head
// ---------------------------------------------------------------------------

function H2HSection({ homeTeam, awayTeam, h2h }) {
  const total = (h2h.home_wins ?? 0) + (h2h.draws ?? 0) + (h2h.away_wins ?? 0)

  return (
    <div>
      <SectionHeader icon="⚔️" title="Head to Head" />

      {/* Win bar */}
      {total > 0 && (
        <div className="mb-4">
          <div className="flex h-3 rounded-full overflow-hidden mb-1.5">
            <div
              className="bg-emerald-600"
              style={{ width: `${(h2h.home_wins / total) * 100}%` }}
            />
            <div
              className="bg-gray-600"
              style={{ width: `${(h2h.draws / total) * 100}%` }}
            />
            <div
              className="bg-red-600"
              style={{ width: `${(h2h.away_wins / total) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-emerald-400 font-semibold">{h2h.home_wins} wins</span>
            <span className="text-gray-400">{h2h.draws} draws · avg {h2h.avg_goals ?? '—'} goals</span>
            <span className="text-red-400 font-semibold">{h2h.away_wins} wins</span>
          </div>
        </div>
      )}

      {/* Recent H2H results */}
      {h2h.matches?.length > 0 ? (
        <div className="flex flex-col gap-1.5">
          {h2h.matches.map((m, i) => {
            const homeWon = m.home_goals > m.away_goals
            const awayWon = m.away_goals > m.home_goals
            return (
              <div key={i} className="flex items-center justify-between bg-gray-800/40 rounded-lg px-3 py-2 text-xs">
                <span className={`flex-1 truncate ${homeWon ? 'text-white font-medium' : 'text-gray-400'}`}>
                  {m.home_team}
                </span>
                <span className="mx-3 tabular-nums font-bold text-white shrink-0">
                  {m.home_goals ?? '?'} – {m.away_goals ?? '?'}
                </span>
                <span className={`flex-1 truncate text-right ${awayWon ? 'text-white font-medium' : 'text-gray-400'}`}>
                  {m.away_team}
                </span>
                <span className="ml-3 text-gray-600 shrink-0 text-[10px]">{m.date?.slice(0, 7)}</span>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-sm text-gray-600">No previous meetings found.</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section 7 — Team Profiles (disciplinary + fatigue)
// ---------------------------------------------------------------------------

function aggrColorClass(v) {
  if (v == null) return 'text-gray-400'
  if (v > 0.5) return 'text-red-400'
  if (v > 0.3) return 'text-amber-400'
  return 'text-emerald-400'
}

function aggrBarClass(v) {
  if (v == null) return 'bg-gray-600'
  if (v > 0.5) return 'bg-red-500'
  if (v > 0.3) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function fatigueColorClass(days) {
  if (days == null) return 'text-gray-400'
  if (days < 4) return 'text-red-400'
  if (days <= 6) return 'text-amber-400'
  return 'text-emerald-400'
}

function congestionColorClass(n) {
  if (n == null) return 'text-gray-400'
  if (n > 5) return 'text-red-400'
  if (n >= 3) return 'text-amber-400'
  return 'text-emerald-400'
}

function TrendIcon({ value }) {
  if (value == null || value === 0) return <Minus className="w-3 h-3 text-gray-400 inline" />
  if (value > 0) return <TrendingUp className="w-3 h-3 text-red-400 inline" />
  return <TrendingDown className="w-3 h-3 text-emerald-400 inline" />
}

function TendencyCol({ teamName, t, side }) {
  if (!t) {
    return (
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-semibold text-gray-300 truncate mb-3">{teamName}</p>
        <p className="text-xs text-gray-600">No profile data</p>
      </div>
    )
  }

  const cardAvg = side === 'home' ? t.home_yellow_avg : t.away_yellow_avg
  const cardLabel = side === 'home' ? 'Home yellows' : 'Away yellows'
  const showPremiumBadge = side === 'away' && (t.away_card_premium ?? 0) > 0.3

  return (
    <div className="flex-1 min-w-0">
      <p className="text-[11px] font-semibold text-gray-300 truncate mb-3">{teamName}</p>

      {/* Aggression bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-gray-500 uppercase tracking-wider">Aggression</span>
          <span className={`font-semibold tabular-nums ${aggrColorClass(t.aggression_index)}`}>
            {t.aggression_index != null ? t.aggression_index.toFixed(2) : '—'}
          </span>
        </div>
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${aggrBarClass(t.aggression_index)}`}
            style={{ width: `${Math.round((t.aggression_index ?? 0) * 100)}%` }}
          />
        </div>
      </div>

      {/* Disciplinary stats */}
      <div className="flex flex-col gap-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Avg yellows</span>
          <span className="text-white tabular-nums">
            {t.avg_yellows_per_game != null ? t.avg_yellows_per_game.toFixed(1) : '—'}/game
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Avg fouls</span>
          <span className="text-white tabular-nums">
            {t.avg_fouls_per_game != null ? t.avg_fouls_per_game.toFixed(1) : '—'}/game
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-500">{cardLabel}</span>
          <span className="flex items-center gap-1.5 tabular-nums text-white">
            {cardAvg != null ? cardAvg.toFixed(2) : '—'}
            {showPremiumBadge && (
              <span className="text-[9px] bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded px-1 font-semibold leading-tight">
                +{t.away_card_premium.toFixed(2)}
              </span>
            )}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-500">Yellow trend</span>
          <span className="flex items-center gap-1">
            <TrendIcon value={t.yellow_trend} />
            <span className={
              t.yellow_trend > 0 ? 'text-red-400' :
              t.yellow_trend < 0 ? 'text-emerald-400' : 'text-gray-400'
            }>
              {t.yellow_trend > 0 ? 'Rising' : t.yellow_trend < 0 ? 'Falling' : 'Stable'}
            </span>
          </span>
        </div>
      </div>

      {/* Fatigue */}
      <div className="mt-3 pt-3 border-t border-gray-800/60">
        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1.5">Fatigue</p>
        <div className="flex flex-col gap-1 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Last match</span>
            <span className={`tabular-nums ${fatigueColorClass(t.days_since_last)}`}>
              {t.days_since_last != null ? `${t.days_since_last}d ago` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Last 21 days</span>
            <span className={`tabular-nums ${congestionColorClass(t.matches_last_21d)}`}>
              {t.matches_last_21d != null ? `${t.matches_last_21d} matches` : '—'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function TeamProfilesSection({ homeTeam, awayTeam, homeTendency, awayTendency, loading }) {
  return (
    <div>
      <SectionHeader icon="🧬" title="Team Profiles" />
      {loading ? (
        <div className="flex items-center gap-2 py-4">
          <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
          <span className="text-xs text-gray-500">Loading profiles…</span>
        </div>
      ) : (
        <div className="flex gap-4">
          <TendencyCol teamName={homeTeam} t={homeTendency} side="home" />
          <div className="w-px bg-gray-800 self-stretch" />
          <TendencyCol teamName={awayTeam} t={awayTendency} side="away" />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

export default function MatchPreview({ match, onClose }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  const [tendencies, setTendencies]             = useState({ home: null, away: null })
  const [tendenciesLoading, setTendenciesLoading] = useState(false)

  useEffect(() => {
    if (!match) return
    setData(null)
    setLoading(true)
    setError(null)
    api.get('/api/match/preview', {
      params: { home_team: match.home_team, away_team: match.away_team },
    })
      .then(res => setData(res.data.data))
      .catch(e => setError(e?.response?.data?.error ?? 'Failed to load preview'))
      .finally(() => setLoading(false))
  }, [match?.home_team, match?.away_team])

  useEffect(() => {
    if (!match) return
    setTendencies({ home: null, away: null })
    setTendenciesLoading(true)
    Promise.all([
      api.get('/api/team/tendencies', { params: { team: match.home_team } }).catch(() => null),
      api.get('/api/team/tendencies', { params: { team: match.away_team } }).catch(() => null),
    ])
      .then(([homeRes, awayRes]) => {
        setTendencies({
          home: homeRes?.data?.data ?? null,
          away: awayRes?.data?.data ?? null,
        })
      })
      .finally(() => setTendenciesLoading(false))
  }, [match?.home_team, match?.away_team])

  // Close on Escape
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!match) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-6 pb-8 px-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div className="relative z-10 w-full max-w-xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-800">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] uppercase tracking-widest text-emerald-400 font-semibold mb-1">
              Match Preview
            </p>
            <div className="flex items-center gap-3">
              <span className="text-base font-bold text-white truncate">{data?.home_canon ?? match.home_team}</span>
              <span className="text-gray-500 font-normal shrink-0 text-sm">vs</span>
              <span className="text-base font-bold text-white truncate">{data?.away_canon ?? match.away_team}</span>
            </div>
            {match.competition && (
              <p className="text-xs text-gray-500 mt-0.5">{match.competition}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
              <p className="text-sm text-gray-500">Generating analysis…</p>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {data && !loading && (
            <>
              <WinProbSection d={data} />
              <Divider />
              <GoalsSection goals={data.goals} />
              <Divider />
              <CorrectScoreSection goals={data.goals} />
              <Divider />
              <CornersSection
                corners={data.corners}
                homeTeam={data.home_canon ?? data.home_team}
                awayTeam={data.away_canon ?? data.away_team}
              />
              <Divider />
              <CardsSection
                cards={data.cards}
                homeTeam={data.home_canon ?? data.home_team}
                awayTeam={data.away_canon ?? data.away_team}
              />
              <Divider />
              <RecentFormSection
                homeTeam={data.home_canon ?? data.home_team}
                awayTeam={data.away_canon ?? data.away_team}
                homeForm={data.home_form}
                awayForm={data.away_form}
              />
              <Divider />
              <H2HSection
                homeTeam={data.home_canon ?? data.home_team}
                awayTeam={data.away_canon ?? data.away_team}
                h2h={data.h2h}
              />
              <Divider />
              <TeamProfilesSection
                homeTeam={data.home_canon ?? data.home_team}
                awayTeam={data.away_canon ?? data.away_team}
                homeTendency={tendencies.home}
                awayTendency={tendencies.away}
                loading={tendenciesLoading}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
