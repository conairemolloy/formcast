import { useState, useEffect } from 'react'
import api from '../api'
import { Loader2 } from 'lucide-react'

const CONF_STYLE = {
  UEFA:             'bg-blue-500/20 text-blue-400',
  CONMEBOL:         'bg-yellow-500/20 text-yellow-500',
  CONCACAF:         'bg-red-500/20 text-red-400',
  CAF:              'bg-orange-500/20 text-orange-400',
  AFC:              'bg-violet-500/20 text-violet-400',
  OFC:              'bg-teal-500/20 text-teal-400',
  'Other / Non-FIFA': 'bg-gray-800 text-gray-500',
}

function pct(v) {
  return typeof v === 'number' ? v.toFixed(1) + '%' : '—'
}

// ── Individual tie card ───────────────────────────────────────────────────────

function TieCard({ tie, onTeamClick, isHighlighted }) {
  const [hovered, setHovered] = useState(null)

  const teams = [
    { name: tie.team1, elo: tie.team1_elo, conf: tie.team1_conf, winPct: tie.team1_win_pct },
    { name: tie.team2, elo: tie.team2_elo, conf: tie.team2_conf, winPct: tie.team2_win_pct },
  ]

  const borderClass = isHighlighted
    ? 'border-amber-500/50'
    : tie.settled
    ? 'border-gray-700'
    : 'border-gray-800'

  return (
    <div
      className={`rounded-lg border overflow-hidden text-xs ${borderClass} ${
        isHighlighted ? 'ring-1 ring-amber-500/30' : ''
      }`}
      style={{ minWidth: 180, maxWidth: 210 }}
    >
      {tie.settled && (
        <div className="px-2 py-0.5 bg-gray-900 border-b border-gray-800 text-gray-500 font-mono text-[10px]">
          {tie.date} · FT {tie.score}
        </div>
      )}
      {!tie.settled && (
        <div className="px-2 py-0.5 bg-gray-900 border-b border-gray-800 text-gray-600 font-mono text-[10px]">
          {tie.date}
        </div>
      )}

      {teams.map((team) => {
        const isWinner = tie.settled && tie.winner === team.name
        const isLoser  = tie.settled && tie.winner && tie.winner !== team.name
        const isHov    = hovered === team.name

        return (
          <div
            key={team.name}
            onMouseEnter={() => setHovered(team.name)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onTeamClick?.(team.name)}
            className={`
              flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors
              ${isWinner ? 'bg-emerald-900/30 border-l-2 border-l-emerald-500' : ''}
              ${isLoser  ? 'opacity-40 bg-gray-900/40' : ''}
              ${!isWinner && !isLoser ? 'bg-gray-900/60 hover:bg-gray-800/60' : ''}
              ${isHov && !isLoser ? 'bg-gray-800/80' : ''}
            `}
          >
            <span className={`flex-1 font-medium truncate ${isWinner ? 'text-white' : 'text-gray-300'}`}>
              {team.name}
            </span>
            {!tie.settled && (
              <span className="tabular-nums text-gray-500 shrink-0">
                {team.winPct.toFixed(0)}%
              </span>
            )}
            {isWinner && (
              <span className="text-emerald-400 shrink-0">✓</span>
            )}
          </div>
        )
      })}

      {/* Hover detail: Elo + confederation */}
      {hovered && !tie.settled && (
        <div className="px-2 py-1 border-t border-gray-800 bg-gray-950/80 text-[10px] text-gray-400 flex items-center gap-2">
          {(() => {
            const t = teams.find(x => x.name === hovered)
            const cs = CONF_STYLE[t.conf] ?? 'bg-gray-800 text-gray-500'
            return (
              <>
                <span className={`px-1 rounded ${cs}`}>{t.conf}</span>
                <span className="tabular-nums">Elo {t.elo.toFixed(0)}</span>
              </>
            )
          })()}
        </div>
      )}
    </div>
  )
}

// ── Connector lines between rounds ────────────────────────────────────────────

function Connector({ count }) {
  const lines = []
  for (let i = 0; i < count; i++) {
    lines.push(
      <div key={i} className="flex-1 flex items-center">
        <div className="w-full border-t border-gray-700/60" />
      </div>
    )
  }
  return <div className="flex flex-col w-4 shrink-0">{lines}</div>
}

// ── Half-bracket (8 ties → R16 → QF → SF) ───────────────────────────────────

function BracketHalf({ ties, sims, half, onTeamClick }) {
  // Map team → sim row for probability lookups
  const simMap = {}
  for (const row of sims) simMap[row.team] = row

  // Final and SF labels
  const sfLabel = half === 'left' ? 'Semi-Final 1' : 'Semi-Final 2'

  // For R16 projected matchup labels, we show which pair of R32 ties feeds each match
  const r16Pairs = [
    [ties[0], ties[1]],
    [ties[2], ties[3]],
    [ties[4], ties[5]],
    [ties[6], ties[7]],
  ]

  return (
    <div className="flex items-stretch gap-0">
      {/* R32 column */}
      <div className="flex flex-col justify-around gap-2 py-2">
        {ties.map((tie) => (
          <TieCard
            key={tie.tie_id}
            tie={tie}
            onTeamClick={onTeamClick}
          />
        ))}
      </div>

      {/* Connector R32→R16 */}
      <div className="flex flex-col justify-around py-2 w-4 shrink-0">
        {r16Pairs.map((pair, i) => (
          <div key={i} className="flex-1 flex flex-col">
            <div className="flex-1 border-r border-t border-gray-700/50 rounded-tr" />
            <div className="flex-1 border-r border-b border-gray-700/50 rounded-br" />
          </div>
        ))}
      </div>

      {/* R16 column */}
      <div className="flex flex-col justify-around gap-6 py-2">
        {r16Pairs.map((pair, i) => {
          const qfSims = buildProjectedMatch(pair, simMap, 'r16_pct')
          return (
            <ProjectedMatchCard
              key={i}
              label="R16"
              teams={qfSims}
              onTeamClick={onTeamClick}
            />
          )
        })}
      </div>

      {/* Connector R16→QF */}
      <div className="flex flex-col justify-around py-2 w-4 shrink-0">
        {[[0, 1], [2, 3]].map((_, i) => (
          <div key={i} className="flex-1 flex flex-col">
            <div className="flex-1 border-r border-t border-gray-700/50 rounded-tr" />
            <div className="flex-1 border-r border-b border-gray-700/50 rounded-br" />
          </div>
        ))}
      </div>

      {/* QF column */}
      <div className="flex flex-col justify-around gap-10 py-2">
        {[[r16Pairs[0], r16Pairs[1]], [r16Pairs[2], r16Pairs[3]]].map((qfPairs, i) => {
          const sfSims = buildProjectedMatch(qfPairs.flat(), simMap, 'qf_pct')
          return (
            <ProjectedMatchCard
              key={i}
              label="QF"
              teams={sfSims}
              style="border-gray-700"
              onTeamClick={onTeamClick}
            />
          )
        })}
      </div>

      {/* Connector QF→SF */}
      <div className="flex flex-col justify-around py-2 w-4 shrink-0">
        <div className="flex-1 flex flex-col">
          <div className="flex-1 border-r border-t border-gray-700/50 rounded-tr" />
          <div className="flex-1 border-r border-b border-gray-700/50 rounded-br" />
        </div>
      </div>

      {/* SF column */}
      <div className="flex flex-col justify-center py-2">
        {(() => {
          const sfSims = buildProjectedMatch(ties.map(t => t), simMap, 'sf_pct')
          return (
            <ProjectedMatchCard
              label={sfLabel}
              teams={sfSims}
              accent="amber"
              onTeamClick={onTeamClick}
            />
          )
        })()}
      </div>
    </div>
  )
}

// ── Projected match card (R16 / QF / SF / Final) ─────────────────────────────

function buildProjectedMatch(sourceTies, simMap, probKey) {
  // From a set of source ties, pick the top-2 most likely teams
  const candidates = {}
  for (const tie of sourceTies) {
    for (const teamName of [tie.team1, tie.team2].filter(Boolean)) {
      const row = simMap[teamName]
      if (!row) continue
      const p = row[probKey] ?? 0
      if (!candidates[teamName] || p > candidates[teamName]) {
        candidates[teamName] = p
      }
    }
  }
  return Object.entries(candidates)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([name, prob]) => ({ name, prob }))
}

function ProjectedMatchCard({ label, teams, accent, onTeamClick }) {
  const borderClass = accent === 'amber'
    ? 'border-amber-500/40 ring-1 ring-amber-500/20'
    : accent === 'yellow'
    ? 'border-yellow-400/50 ring-1 ring-yellow-400/20'
    : 'border-gray-700/60'

  const labelClass = accent === 'amber'
    ? 'text-amber-400'
    : accent === 'yellow'
    ? 'text-yellow-400'
    : 'text-gray-500'

  return (
    <div
      className={`rounded-lg border overflow-hidden text-xs ${borderClass}`}
      style={{ minWidth: 180, maxWidth: 210 }}
    >
      <div className={`px-2 py-0.5 bg-gray-900/80 border-b border-gray-800 text-[10px] font-semibold uppercase tracking-wider ${labelClass}`}>
        {label}
      </div>
      {teams.length === 0 && (
        <div className="px-2 py-2 text-gray-600 italic">TBD</div>
      )}
      {teams.map((t, i) => (
        <div
          key={t.name}
          onClick={() => onTeamClick?.(t.name)}
          className="flex items-center gap-2 px-2 py-1.5 bg-gray-900/60 hover:bg-gray-800/60 cursor-pointer transition-colors border-b border-gray-800/40 last:border-0"
        >
          <span className="flex-1 font-medium text-gray-200 truncate">{t.name}</span>
          <div className="flex items-center gap-1 shrink-0">
            <div className="w-12 h-1 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={accent === 'amber' ? 'h-full bg-amber-500 rounded-full' : accent === 'yellow' ? 'h-full bg-yellow-400 rounded-full' : 'h-full bg-emerald-600 rounded-full'}
                style={{ width: `${Math.min(t.prob, 100)}%` }}
              />
            </div>
            <span className="tabular-nums text-gray-400 text-[10px] w-9 text-right">
              {t.prob.toFixed(1)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Title odds leaderboard ────────────────────────────────────────────────────

function TitleOdds({ teamPaths }) {
  const alive = teamPaths.filter(t => t.champion_pct > 0).slice(0, 16)
  const max   = alive[0]?.champion_pct ?? 1

  return (
    <div className="rounded-xl border border-gray-800 overflow-hidden">
      <div className="bg-gray-900 px-4 py-2.5 border-b border-gray-800">
        <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
          Title Odds — Simulated Win Probabilities
        </h3>
      </div>
      <div className="divide-y divide-gray-800/50">
        {alive.map((row, i) => {
          const confStyle = CONF_STYLE[row.confederation] ?? 'bg-gray-800 text-gray-500'
          const barPct    = (row.champion_pct / max) * 100
          const goldTier  = i === 0
          const silverTier = i === 1

          return (
            <div
              key={row.team}
              className={`flex items-center gap-3 px-4 py-2 ${goldTier ? 'bg-yellow-900/10' : silverTier ? 'bg-gray-800/30' : ''}`}
            >
              <span className="w-5 text-xs font-mono text-gray-500 shrink-0">
                {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`}
              </span>
              <span className={`flex-1 text-sm font-medium truncate ${goldTier ? 'text-yellow-300' : silverTier ? 'text-gray-200' : 'text-gray-300'}`}>
                {row.team}
              </span>
              <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium shrink-0 ${confStyle}`}>
                {row.confederation}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={goldTier ? 'h-full bg-yellow-400 rounded-full' : silverTier ? 'h-full bg-gray-400 rounded-full' : 'h-full bg-emerald-600 rounded-full'}
                    style={{ width: `${barPct}%` }}
                  />
                </div>
                <span className={`tabular-nums text-xs font-mono w-10 text-right ${goldTier ? 'text-yellow-300 font-semibold' : 'text-gray-400'}`}>
                  {row.champion_pct.toFixed(1)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Draw-side analysis ────────────────────────────────────────────────────────

function DrawAnalysis({ drawAnalysis }) {
  if (!drawAnalysis) return null
  const { left, right } = drawAnalysis
  const stronger = left.avg_elo >= right.avg_elo ? 'left' : 'right'

  return (
    <div className="rounded-xl border border-gray-800 overflow-hidden">
      <div className="bg-gray-900 px-4 py-2.5 border-b border-gray-800 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Draw Side Analysis</h3>
        <span className="text-[11px] text-gray-500">Avg Elo of remaining teams per half</span>
      </div>
      <div className="grid grid-cols-2 divide-x divide-gray-800">
        {[
          { key: 'left', label: 'Left Half (SF1 side)', data: left },
          { key: 'right', label: 'Right Half (SF2 side)', data: right },
        ].map(({ key, label, data }) => (
          <div key={key} className="p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-300">{label}</span>
              <span className={`text-xs font-mono tabular-nums ${stronger === key ? 'text-amber-400 font-semibold' : 'text-gray-500'}`}>
                {data.avg_elo} {stronger === key ? '(stronger)' : ''}
              </span>
            </div>
            <div className="space-y-0.5">
              {(data.teams ?? []).slice(0, 8).map(t => {
                const cs = CONF_STYLE[t.confederation] ?? 'bg-gray-800 text-gray-500'
                return (
                  <div key={t.team} className="flex items-center gap-2 text-[11px]">
                    <span className="flex-1 text-gray-300 truncate">{t.team}</span>
                    <span className={`px-1 rounded ${cs}`}>{t.confederation}</span>
                    <span className="tabular-nums text-gray-500 font-mono">{t.elo.toFixed(0)}</span>
                  </div>
                )
              })}
              {(data.teams ?? []).length > 8 && (
                <div className="text-[10px] text-gray-600 pt-1">+{data.teams.length - 8} more</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Root component ────────────────────────────────────────────────────────────

export default function WorldCupBracket({ onTeamClick }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [view, setView]       = useState('bracket') // 'bracket' | 'odds' | 'sides'

  useEffect(() => {
    api.get('/api/international/worldcup/bracket')
      .then(res => setData(res.data.data))
      .catch(() => setError('Failed to load bracket data'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 gap-3 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        Loading bracket…
      </div>
    )
  }

  if (error) {
    return <div className="text-red-400 p-4 text-sm">{error}</div>
  }

  if (!data) return null

  const { r32, team_paths: teamPaths, draw_analysis: drawAnalysis } = data
  const leftTies  = r32.filter(t => t.bracket_half === 'left')
  const rightTies = r32.filter(t => t.bracket_half === 'right')
  const simMap    = Object.fromEntries(teamPaths.map(t => [t.team, t]))

  return (
    <div className="space-y-4">
      {/* Sub-navigation */}
      <div className="flex gap-2 flex-wrap">
        {[
          { key: 'bracket', label: 'Bracket Tree' },
          { key: 'odds',    label: 'Title Odds' },
          { key: 'sides',   label: 'Draw Analysis' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors border ${
              view === key
                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                : 'bg-gray-900 text-gray-400 border-gray-700 hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Bracket tree */}
      {view === 'bracket' && (
        <div className="space-y-6">
          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs text-gray-500">
            <span><span className="text-gray-300">%</span> = Elo win probability (knockout, no draws)</span>
            <span><span className="text-emerald-400">✓</span> = Confirmed result</span>
            <span className="text-amber-400">Gold border</span> = SF/Final tie
          </div>

          {/* Left half */}
          <div>
            <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
              Left Half — Semi-Final 1 side
            </div>
            <div className="overflow-x-auto pb-2">
              <BracketHalf
                ties={leftTies}
                sims={teamPaths}
                half="left"
                onTeamClick={onTeamClick}
              />
            </div>
          </div>

          {/* Final connector */}
          <div className="flex items-center gap-3 px-2">
            <div className="flex-1 border-t border-gray-700/40" />
            <ProjectedMatchCard
              label="Final — July 19"
              teams={buildProjectedMatch(r32, simMap, 'final_pct')}
              accent="yellow"
              onTeamClick={onTeamClick}
            />
            <div className="flex-1 border-t border-gray-700/40" />
          </div>

          {/* Right half */}
          <div>
            <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
              Right Half — Semi-Final 2 side
            </div>
            <div className="overflow-x-auto pb-2">
              <BracketHalf
                ties={rightTies}
                sims={teamPaths}
                half="right"
                onTeamClick={onTeamClick}
              />
            </div>
          </div>
        </div>
      )}

      {/* Title odds */}
      {view === 'odds' && <TitleOdds teamPaths={teamPaths} />}

      {/* Draw side analysis */}
      {view === 'sides' && <DrawAnalysis drawAnalysis={drawAnalysis} />}
    </div>
  )
}
