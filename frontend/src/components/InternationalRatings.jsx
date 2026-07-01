import { useState, useEffect, useRef } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'

const MEDAL = ['🥇', '🥈', '🥉']
const MAX_RATING = 2200

const WC_2026_TEAMS = new Set(['Algeria','Argentina','Australia','Austria','Belgium','Bosnia and Herzegovina','Brazil','Canada','Cape Verde','Curaçao','Czech Republic','Ecuador','Egypt','France','Germany','Haiti','Iran','Iraq','Ivory Coast','Japan','Jordan','Mexico','Morocco','Netherlands','New Zealand','Norway','Paraguay','Qatar','Saudi Arabia','Scotland','Senegal','South Africa','South Korea','Spain','Sweden','Switzerland','Tunisia','Turkey','United States','Uruguay'])

const CONF_TABS = ['WC 2026', 'All', 'UEFA', 'CONMEBOL', 'CONCACAF', 'CAF', 'AFC', 'OFC']

const CONF_STYLE = {
  'UEFA':             'bg-blue-500/20 text-blue-400',
  'CONMEBOL':         'bg-yellow-500/20 text-yellow-500',
  'CONCACAF':         'bg-red-500/20 text-red-400',
  'CAF':              'bg-orange-500/20 text-orange-400',
  'AFC':              'bg-violet-500/20 text-violet-400',
  'OFC':              'bg-teal-500/20 text-teal-400',
  'Other / Non-FIFA': 'bg-gray-800 text-gray-500',
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
    <div>
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-white">International Ratings</h1>
        <p className="mt-1 text-sm text-gray-500">
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
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-400/40'
                  : activeConf === conf
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
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
        <span className="text-sm text-gray-500">
          {loading ? '…' : `${displayData.length} teams`}
        </span>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showAll}
            onChange={e => setShowAll(e.target.checked)}
            className="w-4 h-4 rounded border-gray-700 bg-gray-900 accent-emerald-500"
          />
          <span className="text-sm text-gray-400">Show all teams (including non-FIFA)</span>
        </label>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading ratings…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="text-red-400 p-6">{error}</div>
      )}

      {/* Empty */}
      {!loading && !error && displayData.length === 0 && (
        <div className="text-center py-20 text-gray-500">No teams found</div>
      )}

      {/* Table */}
      {!loading && !error && displayData.length > 0 && (
        <div className="rounded-xl border border-gray-800 overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-gray-400 font-medium w-14">#</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">Team</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">Confederation</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Elo Rating</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Matches</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">Last Match</th>
              </tr>
            </thead>
            <tbody>
              {displayData.map((team, i) => {
                const pct       = Math.min((team.elo_rating / MAX_RATING) * 100, 100)
                const isMedal   = i < 3 && activeConf === 'All'
                const confStyle = CONF_STYLE[team.confederation] ?? 'bg-gray-800 text-gray-500'

                return (
                  <tr
                    key={team.team}
                    onClick={() => onTeamClick?.({ name: team.team, elo: team.elo_rating, confederation: team.confederation, rank: i + 1 })}
                    className={`border-b border-gray-800/50 transition-colors hover:bg-gray-800/50 cursor-pointer ${
                      isMedal ? 'bg-gray-900/80' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-gray-500 font-mono">
                      {isMedal ? MEDAL[i] : `#${i + 1}`}
                    </td>
                    <td className="px-4 py-3 font-medium text-white">{team.team}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${confStyle}`}>
                        {team.confederation}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-3">
                        <div className="hidden sm:block w-28 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${isMedal ? 'bg-emerald-400' : 'bg-emerald-600'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={`font-mono tabular-nums ${isMedal ? 'text-emerald-300 font-semibold' : 'text-gray-300'}`}>
                          {team.elo_rating.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400 tabular-nums">
                      {team.matches_played}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400 font-mono text-xs">
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
