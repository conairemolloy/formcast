import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2, ArrowLeft, Bookmark } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot,
} from 'recharts'
import { CHART, AXIS, TOOLTIP_STYLE } from '../chartTheme'

const RESULT_STYLE = {
  W: { bg: 'bg-[var(--chart-2)]/15', text: 'text-[var(--chart-2)]', border: 'border-[var(--chart-2)]/30' },
  D: { bg: 'bg-[var(--muted)]', text: 'text-[var(--muted-foreground)]', border: 'border-[var(--border)]' },
  L: { bg: 'bg-[var(--chart-5)]/15', text: 'text-[var(--chart-5)]', border: 'border-[var(--chart-5)]/30' },
}

function ResultBadge({ result }) {
  if (!result) return <span className="text-[var(--muted-foreground)]/60">—</span>
  const s = RESULT_STYLE[result] ?? RESULT_STYLE.D
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold border ${s.bg} ${s.text} ${s.border}`}>
      {result}
    </span>
  )
}

function StatBlock({ label, value, color = 'text-[var(--foreground)]', sub }) {
  return (
    <div className="bg-[var(--muted)] rounded-lg p-3 text-center">
      <p className="text-xs text-[var(--muted-foreground)] mb-1">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-[var(--muted-foreground)]/60 mt-0.5">{sub}</p>}
    </div>
  )
}

const HistoryTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={TOOLTIP_STYLE}>
      <p className="text-[var(--muted-foreground)] mb-0.5">{payload[0].payload.season}</p>
      <p className="text-[var(--primary)] font-semibold tabular-nums">{payload[0].value}</p>
    </div>
  )
}

export default function TeamProfile({
  team, eloRating, league, eloRank, onBack,
  user, onWatchlistUpdate, onShowAuth,
}) {
  const [history, setHistory] = useState([])
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [saving, setSaving]   = useState(false)

  const watchlist = user?.watchlist || []
  const saved     = watchlist.includes(team)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.get(`/api/ratings/history?team=${encodeURIComponent(team)}`),
      api.get(`/api/team/profile?team=${encodeURIComponent(team)}`),
    ])
      .then(([histRes, profRes]) => {
        setHistory(histRes.data.data)
        setProfile(profRes.data.data)
      })
      .catch(() => setError('Failed to load team data'))
      .finally(() => setLoading(false))
  }, [team])

  async function toggleWatchlist() {
    if (!user) {
      onShowAuth?.()
      return
    }
    if (saving) return
    setSaving(true)
    try {
      const endpoint = saved ? '/api/auth/watchlist/remove' : '/api/auth/watchlist/add'
      const res = await api.post(endpoint, { team_name: team })
      onWatchlistUpdate?.(res.data.watchlist)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  const lastPoint  = history.length > 0 ? history[history.length - 1] : null
  const formStreak = (profile?.last_10 ?? []).map(m => m.result).filter(Boolean)
  const stats      = profile?.stats ?? {}

  return (
    <div className="fc-page space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Ratings
      </button>

      {/* Header */}
      <div className="fc-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              {league && (
                <span className="text-xs bg-[var(--muted)] text-[var(--muted-foreground)] px-2 py-0.5 rounded font-medium">
                  {league}
                </span>
              )}
              {eloRank && league && (
                <span className="text-xs text-[var(--muted-foreground)]">#{eloRank} in {league}</span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-[var(--foreground)]">{team}</h1>

            {/* Save button */}
            <button
              onClick={toggleWatchlist}
              disabled={saving}
              className={`mt-3 flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                saved
                  ? 'text-[var(--primary)] bg-[var(--primary)]/10 border-[var(--primary)]/30 hover:bg-[var(--primary)]/20'
                  : 'text-[var(--muted-foreground)] bg-[var(--muted)] border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--input)]'
              } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={!user ? 'Sign in to save teams' : undefined}
            >
              <Bookmark
                className="w-4 h-4"
                fill={saved ? 'currentColor' : 'none'}
              />
              {saved ? 'Saved' : 'Save Team'}
            </button>
          </div>

          <div className="text-right shrink-0">
            <p className="text-xs text-[var(--muted-foreground)] mb-0.5">Elo Rating</p>
            <p className="text-4xl font-bold text-[var(--primary)] tabular-nums">
              {eloRating != null ? Math.round(eloRating) : '—'}
            </p>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-[var(--muted-foreground)]">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading team data…
        </div>
      )}

      {error && <div className="text-[var(--chart-5)] p-4 text-sm">{error}</div>}

      {!loading && !error && (
        <>
          {/* Section 1 — Elo History */}
          {history.length > 0 && (
            <div className="fc-card p-5">
              <h2 className="text-base font-semibold text-[var(--foreground)] mb-1">Elo Rating History</h2>
              <p className="text-xs text-[var(--muted-foreground)] mb-4">End-of-season rating, all available seasons</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={history} margin={{ top: 12, right: 20, bottom: 8, left: 0 }}>
                  <XAxis dataKey="season" {...AXIS} interval={4} tickFormatter={v => `'${v.slice(2, 4)}`} />
                  <YAxis domain={['auto', 'auto']} {...AXIS} width={44} tickFormatter={v => Math.round(v)} />
                  <Tooltip content={<HistoryTooltip />} cursor={{ stroke: CHART.grid }} />
                  <Line
                    type="monotone"
                    dataKey="elo_rating"
                    stroke={CHART.coral}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: CHART.coral, stroke: CHART.cream }}
                  />
                  {lastPoint && (
                    <ReferenceDot
                      x={lastPoint.season}
                      y={lastPoint.elo_rating}
                      r={5}
                      fill={CHART.coral}
                      stroke={CHART.cream}
                      strokeWidth={2}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Section 2 — Recent Form */}
          {profile?.last_10?.length > 0 && (
            <div className="fc-card p-5">
              <h2 className="text-base font-semibold text-[var(--foreground)] mb-3">Recent Form</h2>
              <div className="flex items-center gap-1.5 mb-4">
                {formStreak.map((r, i) => <ResultBadge key={i} result={r} />)}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)] text-xs">
                      <th className="text-left pb-2 font-medium">Date</th>
                      <th className="text-center pb-2 font-medium">Venue</th>
                      <th className="text-left pb-2 font-medium">Opponent</th>
                      <th className="text-center pb-2 font-medium">Score</th>
                      <th className="text-center pb-2 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.last_10.map((m, i) => (
                      <tr key={i} className="border-b border-[var(--border)]">
                        <td className="py-2.5 text-[var(--muted-foreground)] tabular-nums whitespace-nowrap">{m.date ?? '—'}</td>
                        <td className="py-2.5 text-center">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            m.venue === 'H'
                              ? 'bg-[var(--muted)] text-[var(--muted-foreground)]'
                              : 'bg-[var(--chart-4)]/15 text-[var(--chart-4)]'
                          }`}>
                            {m.venue}
                          </span>
                        </td>
                        <td className="py-2.5 text-[var(--foreground)] font-medium">{m.opponent}</td>
                        <td className="py-2.5 text-center font-mono font-bold text-[var(--foreground)] tabular-nums">
                          {m.score ?? '—'}
                        </td>
                        <td className="py-2.5 text-center">
                          <ResultBadge result={m.result} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 3 — Season Stats */}
          {stats.played > 0 && (
            <div className="fc-card p-5">
              <h2 className="text-base font-semibold text-[var(--foreground)] mb-1">
                {profile.season} Season Stats
              </h2>
              <p className="text-xs text-[var(--muted-foreground)] mb-4">{stats.played} matches played</p>

              <div className="grid grid-cols-4 gap-3 mb-3">
                <StatBlock label="Wins"   value={stats.wins}   color="text-[var(--chart-2)]" />
                <StatBlock label="Draws"  value={stats.draws}  color="text-[var(--muted-foreground)]" />
                <StatBlock label="Losses" value={stats.losses} color="text-[var(--chart-5)]" />
                <StatBlock
                  label="Goal Diff"
                  value={(stats.goal_diff > 0 ? '+' : '') + stats.goal_diff}
                  color={stats.goal_diff > 0 ? 'text-[var(--chart-2)]' : stats.goal_diff < 0 ? 'text-[var(--chart-5)]' : 'text-[var(--muted-foreground)]'}
                />
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3">
                <StatBlock label="Goals For"     value={stats.goals_for} />
                <StatBlock label="Goals Against" value={stats.goals_against} />
                <StatBlock
                  label="Avg Goals / Game"
                  value={stats.avg_goals_for}
                  color="text-[var(--foreground)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Home', data: stats.home, color: 'text-[var(--muted-foreground)]' },
                  { label: 'Away', data: stats.away, color: 'text-[var(--chart-4)]' },
                ].map(({ label, data: d, color }) => (
                  <div key={label} className="bg-[var(--muted)] rounded-lg p-3">
                    <p className={`text-xs font-semibold mb-2 ${color}`}>{label}</p>
                    <div className="flex items-center gap-3 text-sm">
                      <span>
                        <span className="text-[var(--chart-2)] font-bold">{d.wins}</span>
                        <span className="text-[var(--muted-foreground)]/60 text-xs">W</span>
                      </span>
                      <span>
                        <span className="text-[var(--muted-foreground)] font-bold">{d.draws}</span>
                        <span className="text-[var(--muted-foreground)]/60 text-xs">D</span>
                      </span>
                      <span>
                        <span className="text-[var(--chart-5)] font-bold">{d.losses}</span>
                        <span className="text-[var(--muted-foreground)]/60 text-xs">L</span>
                      </span>
                      <span className="ml-auto text-[var(--muted-foreground)] text-xs tabular-nums">
                        {d.gf}–{d.ga}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 4 — H2H */}
          {profile?.h2h?.length > 0 && (
            <div className="fc-card p-5">
              <h2 className="text-base font-semibold text-[var(--foreground)] mb-1">Head to Head</h2>
              <p className="text-xs text-[var(--muted-foreground)] mb-4">All-time record vs most frequent opponents</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                    <th className="text-left pb-2 font-medium">Opponent</th>
                    <th className="text-center pb-2 font-medium">P</th>
                    <th className="text-center pb-2 font-medium text-[var(--chart-2)]">W</th>
                    <th className="text-center pb-2 font-medium">D</th>
                    <th className="text-center pb-2 font-medium text-[var(--chart-5)]">L</th>
                    <th className="text-right pb-2 font-medium">Win %</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.h2h.map((row, i) => (
                    <tr key={i} className={i < profile.h2h.length - 1 ? 'border-b border-[var(--border)]' : ''}>
                      <td className="py-2.5 text-[var(--foreground)] font-medium">{row.opponent}</td>
                      <td className="py-2.5 text-center text-[var(--muted-foreground)] tabular-nums">{row.played}</td>
                      <td className="py-2.5 text-center text-[var(--chart-2)] font-semibold tabular-nums">{row.wins}</td>
                      <td className="py-2.5 text-center text-[var(--muted-foreground)] tabular-nums">{row.draws}</td>
                      <td className="py-2.5 text-center text-[var(--chart-5)] font-semibold tabular-nums">{row.losses}</td>
                      <td className="py-2.5 text-right tabular-nums text-[var(--foreground)]">
                        {row.played > 0 ? ((row.wins / row.played) * 100).toFixed(0) : 0}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
