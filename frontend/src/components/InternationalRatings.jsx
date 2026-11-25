import { useState, useEffect, useRef } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'

const MEDAL = ['🥇', '🥈', '🥉']
const MAX_RATING = 2200

const WC_2026_TEAMS = new Set(['Algeria','Argentina','Australia','Austria','Belgium','Bosnia and Herzegovina','Brazil','Canada','Cape Verde','Curaçao','Czech Republic','Ecuador','Egypt','France','Germany','Haiti','Iran','Iraq','Ivory Coast','Japan','Jordan','Mexico','Morocco','Netherlands','New Zealand','Norway','Paraguay','Qatar','Saudi Arabia','Scotland','Senegal','South Africa','South Korea','Spain','Sweden','Switzerland','Tunisia','Turkey','United States','Uruguay'])

const CONF_TABS = ['WC 2026', 'All', 'UEFA', 'CONMEBOL', 'CONCACAF', 'CAF', 'AFC', 'OFC']

const CONF_STYLE = {
  'UEFA':             'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CONMEBOL':         'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CONCACAF':         'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'CAF':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'AFC':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'OFC':              'bg-[var(--muted)] text-[var(--muted-foreground)]',
  'Other / Non-FIFA': 'bg-[var(--muted)] text-[var(--muted-foreground)]',
}

export default function InternationalRatings({ onTeamClick }) {
  const [data, setData]           = useState([])
  const [confCounts, setConfCounts] = useState({})
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [activeConf, setActiveConf] = useState('All')
  const [showAll, setShowAll]     = useState(false)
  const ratingsRef                    = useRef(null)

  // Confederation counts for tab labels — fetch once, no min_matches applied
  useEffect(() => {
    api.get('/api/international/confederations')
      .then(res => {
        const map = {}
        for (const row of res.data.data) map[row.confederation] = row.count
        setConfCounts(map)
      })
      .catch(() => {})
  }, [])

  // Ratings — refetch when confederation or min_matches toggle changes
  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams()
    if (activeConf !== 'All' && activeConf !== 'WC 2026') params.set('confederation', activeConf)
    if (!showAll) params.set('min_matches', '20')

    api.get(`/api/international/ratings?${params}`)
      .then(res => setData(res.data.data))
      .catch(() => setError('Failed to load ratings'))
      .finally(() => setLoading(false))
  }, [activeConf, showAll])

  const displayData = activeConf === 'WC 2026'
    ? data.filter(t => WC_2026_TEAMS.has(t.team))
    : data

  const tabCount = conf =>
    conf === 'WC 2026' ? 40 :
    conf === 'All'     ? Object.values(confCounts).reduce((s, n) => s + n, 0) || null :
                         confCounts[conf] ?? null

  return (
    <div className="fc-page">
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-[var(--foreground)]">International Ratings</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Separate rating system from club football — calibrated for national teams with
          tournament-importance weighting and neutral-venue adjustment
        </p>
      </div>

      {/* Confederation tabs */}
      <div ref={ratingsRef} className="flex gap-2 flex-wrap mb-4">
        {CONF_TABS.map(conf => {
          const count = tabCount(conf)
          return (
            <button
              key={conf}
              onClick={() => setActiveConf(conf)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                activeConf === conf && conf === 'WC 2026'
                  ? 'bg-[var(--primary)]/12 text-[var(--primary)] border border-[var(--primary)]/30'
                  : activeConf === conf
                  ? 'bg-[var(--primary)]/12 text-[var(--primary)] border border-[var(--primary)]/30'
                  : 'bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:text-[var(--foreground)]'
              }`}
            >
              {conf === 'WC 2026' ? '🏆 WC 2026' : conf}
              {count != null && (
                <span className="ml-1.5 text-xs opacity-60">({count})</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Sub-controls */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-[var(--muted-foreground)]">
          {loading ? '…' : `${displayData.length} teams`}
        </span>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showAll}
            onChange={e => setShowAll(e.target.checked)}
            className="w-4 h-4 rounded border-[var(--border)] bg-[var(--card)] accent-[var(--primary)]"
          />
          <span className="text-sm text-[var(--muted-foreground)]">Show all teams (including non-FIFA)</span>
        </label>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-[var(--muted-foreground)]">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading ratings…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="text-[var(--chart-5)] p-6">{error}</div>
      )}

      {/* Empty */}
      {!loading && !error && displayData.length === 0 && (
        <div className="text-center py-20 text-[var(--muted-foreground)]">No teams found</div>
      )}

      {/* Table */}
      {!loading && !error && displayData.length > 0 && (
        <div className="fc-card overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="bg-[var(--card)] border-b border-[var(--border)]">
                <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium w-14">#</th>
                <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium">Team</th>
                <th className="px-4 py-3 text-left text-[var(--muted-foreground)] font-medium">Confederation</th>
                <th className="px-4 py-3 text-right text-[var(--muted-foreground)] font-medium">Elo Rating</th>
                <th className="px-4 py-3 text-right text-[var(--muted-foreground)] font-medium">Matches</th>
                <th className="px-4 py-3 text-right text-[var(--muted-foreground)] font-medium">Last Match</th>
              </tr>
            </thead>
            <tbody>
              {displayData.map((team, i) => {
                const pct       = Math.min((team.elo_rating / MAX_RATING) * 100, 100)
                const isMedal   = i < 3 && activeConf === 'All'
                const confStyle = CONF_STYLE[team.confederation] ?? 'bg-[var(--muted)] text-[var(--muted-foreground)]'

                return (
                  <tr
                    key={team.team}
                    onClick={() => onTeamClick?.({ name: team.team, elo: team.elo_rating, confederation: team.confederation, rank: i + 1 })}
                    className={`border-b border-[var(--border)] transition-colors hover:bg-[var(--secondary)] cursor-pointer ${
                      isMedal ? 'bg-[var(--primary)]/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-[var(--muted-foreground)] font-mono">
                      {isMedal ? MEDAL[i] : `#${i + 1}`}
                    </td>
                    <td className="px-4 py-3 font-medium text-[var(--foreground)] hover:text-[var(--primary)] transition-colors">{team.team}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${confStyle}`}>
                        {team.confederation}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-3">
                        <div className="hidden sm:block w-28 h-1.5 bg-[var(--muted)] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${isMedal ? 'bg-[var(--primary)]' : 'bg-[var(--muted-foreground)]'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={`font-mono tabular-nums ${isMedal ? 'text-[var(--primary)] font-semibold' : 'text-[var(--foreground)]'}`}>
                          {team.elo_rating.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--muted-foreground)] tabular-nums">
                      {team.matches_played}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--muted-foreground)] font-mono text-xs">
                      {team.last_match_date}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
