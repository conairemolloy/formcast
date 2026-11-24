import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2, ChevronLeft } from 'lucide-react'

const CONF_STYLE = {
  'UEFA':             'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CONMEBOL':         'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CONCACAF':         'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CAF':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'AFC':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'OFC':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'Other / Non-FIFA': 'bg-[var(--muted)] text-[var(--muted-foreground)]',
}

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

export default function InternationalTeamProfile({ team, eloRating, confederation, eloRank, onBack }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.get(`/api/international/team/profile?team=${encodeURIComponent(team)}`)
      .then(res => setProfile(res.data.data))
      .catch(() => setError('Failed to load team data'))
      .finally(() => setLoading(false))
  }, [team])

  const confStyle = CONF_STYLE[confederation] ?? 'bg-[var(--muted)] text-[var(--muted-foreground)]'
  // API returns matches descending (newest first) — reverse for chronological form row
  const formChron = [...(profile?.recent_results ?? [])].reverse()

  return (
    <div className="fc-page space-y-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to Ratings
      </button>

      {/* Header */}
      <div className="fc-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${confStyle}`}>
                {confederation}
              </span>
              {eloRank != null && (
                <span className="text-xs text-[var(--muted-foreground)]">#{eloRank}</span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-[var(--foreground)]">{team}</h1>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-[var(--muted-foreground)] mb-0.5">Elo Rating</p>
            <p className="text-4xl font-bold text-[var(--primary)] tabular-nums">
              {eloRating != null ? Math.round(eloRating) : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-[var(--muted-foreground)]">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading team data…
        </div>
      )}

      {/* Error */}
      {error && <div className="text-[var(--chart-5)] p-4 text-sm">{error}</div>}

      {!loading && !error && profile && (
        <>
          {/* Stats row */}
          <div className="fc-card p-5">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[var(--muted)] rounded-lg p-3 text-center">
                <p className="text-xs text-[var(--muted-foreground)] mb-1">Matches Played</p>
                <p className="text-2xl font-bold tabular-nums text-[var(--foreground)]">
                  {profile.matches_played ?? '—'}
                </p>
              </div>
              <div className="bg-[var(--muted)] rounded-lg p-3 text-center">
                <p className="text-xs text-[var(--muted-foreground)] mb-1">First Match</p>
                <p className="text-sm font-semibold text-[var(--foreground)] tabular-nums mt-1">
                  {profile.first_match_date ?? '—'}
                </p>
              </div>
              <div className="bg-[var(--muted)] rounded-lg p-3 text-center">
                <p className="text-xs text-[var(--muted-foreground)] mb-1">Last Match</p>
                <p className="text-sm font-semibold text-[var(--foreground)] tabular-nums mt-1">
                  {profile.last_match_date ?? '—'}
                </p>
              </div>
            </div>
          </div>

          {/* Recent form + results */}
          {profile.recent_results?.length > 0 && (
            <div className="fc-card p-5">
              <h2 className="text-base font-semibold text-[var(--foreground)] mb-3">Recent Form</h2>

              {/* Form badges — oldest left, newest right */}
              <div className="flex items-center gap-1.5 mb-4">
                {formChron.map((m, i) => <ResultBadge key={i} result={m.result} />)}
              </div>

              {/* Results table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)] text-xs">
                      <th className="text-left pb-2 font-medium">Date</th>
                      <th className="text-left pb-2 font-medium">Opponent</th>
                      <th className="text-center pb-2 font-medium">Venue</th>
                      <th className="text-center pb-2 font-medium">Score</th>
                      <th className="text-center pb-2 font-medium">Result</th>
                      <th className="text-left pb-2 font-medium">Tournament</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.recent_results.map((m, i) => (
                      <tr key={i} className="border-b border-[var(--border)]">
                        <td className="py-2.5 text-[var(--muted-foreground)] tabular-nums whitespace-nowrap">
                          {m.date ?? '—'}
                        </td>
                        <td className="py-2.5 text-[var(--foreground)] font-medium">{m.opponent}</td>
                        <td className="py-2.5 text-center">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            m.venue === 'H'
                              ? 'bg-[var(--muted)] text-[var(--muted-foreground)]'
                              : m.venue === 'A'
                              ? 'bg-[var(--chart-4)]/15 text-[var(--chart-4)]'
                              : 'bg-transparent border border-[var(--border)] text-[var(--muted-foreground)]'
                          }`}>
                            {m.venue ?? '—'}
                          </span>
                        </td>
                        <td className="py-2.5 text-center font-mono font-bold text-[var(--foreground)] tabular-nums">
                          {m.team_score != null && m.opponent_score != null
                            ? `${m.team_score}–${m.opponent_score}`
                            : '—'}
                        </td>
                        <td className="py-2.5 text-center">
                          <ResultBadge result={m.result} />
                        </td>
                        <td className="py-2.5 text-[var(--muted-foreground)] text-xs">{m.tournament ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
