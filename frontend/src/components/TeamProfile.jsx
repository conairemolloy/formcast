import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2, ArrowLeft, Bookmark } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot,
} from 'recharts'

const RESULT_STYLE = {
  W: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  D: { bg: 'bg-gray-700/40',   text: 'text-gray-400',    border: 'border-gray-600/30' },
  L: { bg: 'bg-red-500/20',    text: 'text-red-400',     border: 'border-red-500/30' },
}

function ResultBadge({ result }) {
  if (!result) return <span className="text-gray-600">—</span>
  const s = RESULT_STYLE[result] ?? RESULT_STYLE.D
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold border ${s.bg} ${s.text} ${s.border}`}>
      {result}
    </span>
  )
}

function StatBlock({ label, value, color = 'text-white', sub }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 text-center">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

const HistoryTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
      <p className="text-gray-400 mb-0.5">{payload[0].payload.season}</p>
      <p className="text-emerald-400 font-semibold tabular-nums">{payload[0].value}</p>
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
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Ratings
      </button>

      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              {league && (
                <span className="text-xs bg-gray-800 border border-gray-700 text-gray-400 px-2 py-0.5 rounded font-medium">
                  {league}
                </span>
              )}
              {eloRank && league && (
                <span className="text-xs text-gray-500">#{eloRank} in {league}</span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-white">{team}</h1>

            {/* Save button */}
            <button
              onClick={toggleWatchlist}
              disabled={saving}
              className={`mt-3 flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                saved
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20'
                  : 'text-gray-400 bg-gray-800 border-gray-700 hover:text-white hover:border-gray-600'
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
            <p className="text-xs text-gray-500 mb-0.5">Elo Rating</p>
            <p className="text-4xl font-bold text-emerald-400 tabular-nums">
              {eloRating != null ? Math.round(eloRating) : '—'}
            </p>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading team data…
        </div>
      )}

      {error && <div className="text-red-400 p-4 text-sm">{error}</div>}

      {!loading && !error && (
        <>
          {/* Section 1 — Elo History */}
          {history.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-base font-semibold text-white mb-1">Elo Rating History</h2>
              <p className="text-xs text-gray-500 mb-4">End-of-season rating, all available seasons</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={history} margin={{ top: 12, right: 20, bottom: 8, left: 0 }}>
                  <XAxis
                    dataKey="season"
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={4}
                    tickFormatter={v => `'${v.slice(2, 4)}`}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fill: '#6b7280', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={44}
                    tickFormatter={v => Math.round(v)}
                  />
                  <Tooltip content={<HistoryTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.06)' }} />
                  <Line
                    type="monotone"
                    dataKey="elo_rating"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#34d399', stroke: '#10b981' }}
                  />
                  {lastPoint && (
                    <ReferenceDot
                      x={lastPoint.season}
                      y={lastPoint.elo_rating}
                      r={5}
                      fill="#10b981"
                      stroke="#34d399"
                      strokeWidth={2}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Section 2 — Recent Form */}
          {profile?.last_10?.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-base font-semibold text-white mb-3">Recent Form</h2>
              <div className="flex items-center gap-1.5 mb-4">
                {formStreak.map((r, i) => <ResultBadge key={i} result={r} />)}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-500 text-xs">
                      <th className="text-left pb-2 font-medium">Date</th>
                      <th className="text-center pb-2 font-medium">Venue</th>
                      <th className="text-left pb-2 font-medium">Opponent</th>
                      <th className="text-center pb-2 font-medium">Score</th>
                      <th className="text-center pb-2 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.last_10.map((m, i) => (
                      <tr key={i} className="border-b border-gray-800/50">
                        <td className="py-2.5 text-gray-400 tabular-nums whitespace-nowrap">{m.date ?? '—'}</td>
                        <td className="py-2.5 text-center">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            m.venue === 'H'
                              ? 'bg-blue-500/15 text-blue-400'
                              : 'bg-orange-500/15 text-orange-400'
                          }`}>
                            {m.venue}
                          </span>
                        </td>
                        <td className="py-2.5 text-white font-medium">{m.opponent}</td>
                        <td className="py-2.5 text-center font-mono font-bold text-white tabular-nums">
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
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-base font-semibold text-white mb-1">
                {profile.season} Season Stats
              </h2>
              <p className="text-xs text-gray-500 mb-4">{stats.played} matches played</p>

              <div className="grid grid-cols-4 gap-3 mb-3">
                <StatBlock label="Wins"   value={stats.wins}   color="text-emerald-400" />
                <StatBlock label="Draws"  value={stats.draws}  color="text-gray-300" />
                <StatBlock label="Losses" value={stats.losses} color="text-red-400" />
                <StatBlock
                  label="Goal Diff"
                  value={(stats.goal_diff > 0 ? '+' : '') + stats.goal_diff}
                  color={stats.goal_diff > 0 ? 'text-emerald-400' : stats.goal_diff < 0 ? 'text-red-400' : 'text-gray-300'}
                />
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3">
                <StatBlock label="Goals For"     value={stats.goals_for} />
                <StatBlock label="Goals Against" value={stats.goals_against} />
                <StatBlock
                  label="Avg Goals / Game"
                  value={stats.avg_goals_for}
                  color="text-gray-300"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Home', data: stats.home, color: 'text-blue-400' },
                  { label: 'Away', data: stats.away, color: 'text-orange-400' },
                ].map(({ label, data: d, color }) => (
                  <div key={label} className="bg-gray-800/50 rounded-lg p-3">
                    <p className={`text-xs font-semibold mb-2 ${color}`}>{label}</p>
                    <div className="flex items-center gap-3 text-sm">
                      <span>
                        <span className="text-emerald-400 font-bold">{d.wins}</span>
                        <span className="text-gray-600 text-xs">W</span>
                      </span>
                      <span>
                        <span className="text-gray-300 font-bold">{d.draws}</span>
                        <span className="text-gray-600 text-xs">D</span>
                      </span>
                      <span>
                        <span className="text-red-400 font-bold">{d.losses}</span>
                        <span className="text-gray-600 text-xs">L</span>
                      </span>
                      <span className="ml-auto text-gray-500 text-xs tabular-nums">
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
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-base font-semibold text-white mb-1">Head to Head</h2>
              <p className="text-xs text-gray-500 mb-4">All-time record vs most frequent opponents</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-xs text-gray-500">
                    <th className="text-left pb-2 font-medium">Opponent</th>
                    <th className="text-center pb-2 font-medium">P</th>
                    <th className="text-center pb-2 font-medium text-emerald-500">W</th>
                    <th className="text-center pb-2 font-medium">D</th>
                    <th className="text-center pb-2 font-medium text-red-500">L</th>
                    <th className="text-right pb-2 font-medium">Win %</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.h2h.map((row, i) => (
                    <tr key={i} className={i < profile.h2h.length - 1 ? 'border-b border-gray-800/50' : ''}>
                      <td className="py-2.5 text-white font-medium">{row.opponent}</td>
                      <td className="py-2.5 text-center text-gray-400 tabular-nums">{row.played}</td>
                      <td className="py-2.5 text-center text-emerald-400 font-semibold tabular-nums">{row.wins}</td>
                      <td className="py-2.5 text-center text-gray-400 tabular-nums">{row.draws}</td>
                      <td className="py-2.5 text-center text-red-400 font-semibold tabular-nums">{row.losses}</td>
                      <td className="py-2.5 text-right tabular-nums text-gray-300">
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
