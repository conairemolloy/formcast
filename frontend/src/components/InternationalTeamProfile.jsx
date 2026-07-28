import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2, ChevronLeft } from 'lucide-react'

const CONF_STYLE = {
  'UEFA':             'bg-[var(--bg-overlay)] text-[var(--text-secondary)]',
  'CONMEBOL':         'bg-[var(--bg-overlay)] text-[var(--text-secondary)]',
  'CONCACAF':         'bg-red-500/20 text-red-400',
  'CAF':              'bg-orange-500/20 text-orange-400',
  'AFC':              'bg-violet-500/20 text-violet-400',
  'OFC':              'bg-teal-500/20 text-teal-400',
  'Other / Non-FIFA': 'bg-gray-800 text-gray-500',
}

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

  const confStyle = CONF_STYLE[confederation] ?? 'bg-gray-800 text-gray-500'
  // API returns matches descending (newest first) — reverse for chronological form row
  const formChron = [...(profile?.recent_results ?? [])].reverse()

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to Ratings
      </button>

      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${confStyle}`}>
                {confederation}
              </span>
              {eloRank != null && (
                <span className="text-xs text-gray-500">#{eloRank}</span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-white">{team}</h1>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-gray-500 mb-0.5">Elo Rating</p>
            <p className="text-4xl font-bold text-emerald-400 tabular-nums">
              {eloRating != null ? Math.round(eloRating) : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading team data…
        </div>
      )}

      {/* Error */}
      {error && <div className="text-red-400 p-4 text-sm">{error}</div>}

      {!loading && !error && profile && (
        <>
          {/* Stats row */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-800/50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Matches Played</p>
                <p className="text-2xl font-bold tabular-nums text-white">
                  {profile.matches_played ?? '—'}
                </p>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">First Match</p>
                <p className="text-sm font-semibold text-gray-300 tabular-nums mt-1">
                  {profile.first_match_date ?? '—'}
                </p>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Last Match</p>
                <p className="text-sm font-semibold text-gray-300 tabular-nums mt-1">
                  {profile.last_match_date ?? '—'}
                </p>
              </div>
            </div>
          </div>

          {/* Recent form + results */}
          {profile.recent_results?.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-base font-semibold text-white mb-3">Recent Form</h2>

              {/* Form badges — oldest left, newest right */}
              <div className="flex items-center gap-1.5 mb-4">
                {formChron.map((m, i) => <ResultBadge key={i} result={m.result} />)}
              </div>

              {/* Results table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-500 text-xs">
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
                      <tr key={i} className="border-b border-gray-800/50">
                        <td className="py-2.5 text-gray-400 tabular-nums whitespace-nowrap">
                          {m.date ?? '—'}
                        </td>
                        <td className="py-2.5 text-white font-medium">{m.opponent}</td>
                        <td className="py-2.5 text-center">
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            m.venue === 'H'
                              ? 'bg-[var(--bg-overlay)] text-[var(--text-secondary)]'
                              : m.venue === 'A'
                              ? 'bg-orange-500/15 text-orange-400'
                              : 'bg-gray-700/40 text-gray-400'
                          }`}>
                            {m.venue ?? '—'}
                          </span>
                        </td>
                        <td className="py-2.5 text-center font-mono font-bold text-white tabular-nums">
                          {m.team_score != null && m.opponent_score != null
                            ? `${m.team_score}–${m.opponent_score}`
                            : '—'}
                        </td>
                        <td className="py-2.5 text-center">
                          <ResultBadge result={m.result} />
                        </td>
                        <td className="py-2.5 text-gray-500 text-xs">{m.tournament ?? '—'}</td>
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
