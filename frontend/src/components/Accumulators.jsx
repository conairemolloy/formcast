import { useState, useEffect, useMemo, useRef } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle, ChevronDown } from 'lucide-react'
import { formatOdds, useOddsFormat } from '../oddsFormat'

function LegPill({ home, away, outcome, odds, format }) {
  if (typeof home !== 'string' || typeof away !== 'string') return null
  return (
    <span className="inline-flex items-center gap-1 bg-gray-800 rounded px-2 py-0.5 text-xs text-gray-300 mr-1 mb-1">
      <span className="font-medium text-white">{home} vs {away}</span>
      <span className="text-gray-500">·</span>
      <span className="font-mono text-[var(--text-secondary)]">{outcome ?? '—'}</span>
      <span className="text-gray-600">@{odds != null ? formatOdds(odds, format) : '—'}</span>
    </span>
  )
}

function AccaCard({ acca, format }) {
  const ev = Number(acca.acca_ev)
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex flex-wrap gap-1">
          <LegPill home={acca.leg1_home} away={acca.leg1_away} outcome={acca.leg1_outcome} odds={acca.leg1_odds} format={format} />
          <LegPill home={acca.leg2_home} away={acca.leg2_away} outcome={acca.leg2_outcome} odds={acca.leg2_odds} format={format} />
          <LegPill home={acca.leg3_home} away={acca.leg3_away} outcome={acca.leg3_outcome} odds={acca.leg3_odds} format={format} />
        </div>
        <div className="shrink-0">
          {acca.won
            ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            : <XCircle className="w-5 h-5 text-red-500" />
          }
        </div>
      </div>

      <div className="flex gap-6 text-sm">
        <div>
          <span className="text-gray-500 text-xs">Combined Odds</span>
          <p className="font-mono font-semibold text-white">
            {acca.combined_odds != null ? formatOdds(acca.combined_odds, format) : '—'}
          </p>
        </div>
        <div>
          <span className="text-gray-500 text-xs">Model Prob</span>
          <p className="font-mono font-semibold text-gray-300">
            {acca.combined_p != null ? (Number(acca.combined_p) * 100).toFixed(1) + '%' : '—'}
          </p>
        </div>
        <div>
          <span className="text-gray-500 text-xs">EV</span>
          <p className={`font-mono font-semibold ${ev > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {acca.acca_ev != null ? (ev > 0 ? '+' : '') + ev.toFixed(3) : '—'}
          </p>
        </div>
        <div>
          <span className="text-gray-500 text-xs">Date</span>
          <p className="font-mono text-gray-400 text-xs mt-0.5">{acca.match_date ?? '—'}</p>
        </div>
      </div>
    </div>
  )
}

const SORT_OPTIONS = [
  { value: 'ev',   label: 'EV' },
  { value: 'odds', label: 'Combined Odds' },
  { value: 'date', label: 'Date' },
]

// ---------------------------------------------------------------------------
// EV Matrix helpers — mirror the correlation penalty from value_betting.py
// ---------------------------------------------------------------------------

function correlationPenalty(a, b) {
  let penalty = 1.0
  const sameLeague = a.league === b.league
  const sameDate   = a.match_date === b.match_date
  if (sameLeague) penalty *= 0.92
  if (sameDate && sameLeague) penalty *= 0.95
  return Math.max(penalty, 0.70)
}

function computeCellEV(a, b) {
  const raw = a.odds * b.odds * a.p_model * b.p_model - 1
  return raw * correlationPenalty(a, b)
}

function evCellClass(ev) {
  if (ev > 0.15) return 'bg-emerald-500/25 text-emerald-300 border-emerald-500/20 hover:bg-emerald-500/40'
  if (ev > 0.05) return 'bg-amber-500/20  text-amber-300  border-amber-500/20  hover:bg-amber-500/35'
  if (ev > 0)    return 'bg-gray-700/40   text-gray-400   border-gray-700/50   hover:bg-gray-700/60'
  return             'bg-red-500/10    text-red-400    border-red-500/10    hover:bg-red-500/20'
}

function shortLabel(bet) {
  const h = (bet.home_team ?? '?').split(' ')[0]
  const a = (bet.away_team ?? '?').split(' ')[0]
  return `${h}v${a}(${bet.outcome})`
}

// ---------------------------------------------------------------------------
// EVMatrix component
// ---------------------------------------------------------------------------

function EVMatrix({ bets, format }) {
  // Normalise selected pair as [lo, hi] so [i,j] and [j,i] both map to the same key
  const [selected, setSelected] = useState(null)

  const items = bets.slice(0, 10)

  if (items.length === 0) {
    return <p className="text-gray-500 text-sm py-2">No value bets available for matrix.</p>
  }

  function handleClick(i, j) {
    if (i === j) return
    const key = [Math.min(i, j), Math.max(i, j)]
    setSelected(prev =>
      prev && prev[0] === key[0] && prev[1] === key[1] ? null : key
    )
  }

  function isSelected(i, j) {
    if (!selected) return false
    const [lo, hi] = selected
    return (i === lo && j === hi) || (i === hi && j === lo)
  }

  const detail = selected ? (() => {
    const a       = items[selected[0]]
    const b       = items[selected[1]]
    const penalty = correlationPenalty(a, b)
    const ev      = computeCellEV(a, b)
    return { a, b, penalty, ev, combinedOdds: a.odds * b.odds, combinedP: a.p_model * b.p_model }
  })() : null

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        Top {items.length} value bets by edge. EV is correlation-adjusted for same-league legs.
        Click any cell to inspect that combination.
      </p>

      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="w-24 min-w-[96px]" />
              {items.map((b, j) => (
                <th key={j} className="pb-2 px-0.5 font-normal min-w-[68px]">
                  <span
                    className="block truncate w-16 text-center text-gray-500"
                    title={`${b.home_team} vs ${b.away_team} (${b.outcome})`}
                  >
                    {shortLabel(b)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((a, i) => (
              <tr key={i}>
                <td className="pr-2 py-0.5">
                  <span
                    className="block truncate w-24 text-right text-gray-500"
                    title={`${a.home_team} vs ${a.away_team} (${a.outcome})`}
                  >
                    {shortLabel(a)}
                  </span>
                </td>
                {items.map((b, j) => {
                  if (i === j) {
                    return (
                      <td key={j} className="px-0.5 py-0.5">
                        <div className="w-16 h-8 bg-gray-800 rounded flex items-center justify-center text-gray-700 select-none">
                          —
                        </div>
                      </td>
                    )
                  }
                  const ev  = computeCellEV(a, b)
                  const sel = isSelected(i, j)
                  return (
                    <td key={j} className="px-0.5 py-0.5">
                      <button
                        onClick={() => handleClick(i, j)}
                        title={`${shortLabel(a)} + ${shortLabel(b)}\nEV: ${ev > 0 ? '+' : ''}${(ev * 100).toFixed(1)}%`}
                        className={`w-16 h-8 rounded border font-mono transition-colors ${evCellClass(ev)} ${sel ? 'ring-2 ring-white/40' : ''}`}
                      >
                        {ev > 0 ? '+' : ''}{(ev * 100).toFixed(1)}%
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        {[
          ['bg-emerald-500/25 border-emerald-500/20', 'EV >15%'],
          ['bg-amber-500/20  border-amber-500/20',   '5–15%'],
          ['bg-gray-700/40   border-gray-700/50',    '0–5%'],
          ['bg-red-500/10    border-red-500/10',     'Negative'],
        ].map(([cls, label]) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className={`w-3 h-3 rounded border inline-block ${cls}`} />
            {label}
          </span>
        ))}
      </div>

      {/* Selected detail panel */}
      {detail && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Selected Combination</p>
          <div className="flex items-center gap-2 flex-wrap">
            <LegPill
              home={detail.a.home_team} away={detail.a.away_team}
              outcome={detail.a.outcome} odds={detail.a.odds} format={format}
            />
            <span className="text-gray-600 text-sm">+</span>
            <LegPill
              home={detail.b.home_team} away={detail.b.away_team}
              outcome={detail.b.outcome} odds={detail.b.odds} format={format}
            />
          </div>
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-gray-500 text-xs">Combined Odds</span>
              <p className="font-mono font-semibold text-white">{formatOdds(detail.combinedOdds, format)}</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">Model Prob</span>
              <p className="font-mono font-semibold text-gray-300">{(detail.combinedP * 100).toFixed(1)}%</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">Adjusted EV</span>
              <p className={`font-mono font-semibold ${detail.ev > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {detail.ev > 0 ? '+' : ''}{(detail.ev * 100).toFixed(2)}%
              </p>
            </div>
            {detail.penalty < 1.0 && (
              <div>
                <span className="text-gray-500 text-xs">Corr. Penalty</span>
                <p className="font-mono text-amber-400">{(detail.penalty * 100).toFixed(0)}%</p>
              </div>
            )}
            <div>
              <span className="text-gray-500 text-xs">Leagues</span>
              <p className="font-mono text-gray-400 text-xs mt-0.5">
                {detail.a.league ?? '—'} / {detail.b.league ?? '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Accumulators page
// ---------------------------------------------------------------------------

export default function Accumulators() {
  const [data, setData]             = useState({ 2: [], 3: [] })
  const [loading, setLoading]       = useState({ 2: true, 3: true })
  const [error, setError]           = useState({ 2: null, 3: null })
  const [nLegs, setNLegs]           = useState(2)
  const [wonFilter, setWonFilter]   = useState('ALL')
  const [sortBy, setSortBy]         = useState('ev')

  const [matrixOpen, setMatrixOpen]         = useState(false)
  const [matrixBets, setMatrixBets]         = useState([])
  const [matrixLoading, setMatrixLoading]   = useState(false)
  const [matrixError, setMatrixError]       = useState(null)
  const matrixFetched                       = useRef(false)
  const [oddsFormat]                        = useOddsFormat()

  useEffect(() => {
    for (const n of [2, 3]) {
      api.get(`/api/accumulator?n_legs=${n}&limit=50`)
        .then(r => {
          const rows = r.data.data ?? []
          setData(prev => ({ ...prev, [n]: rows }))
        })
        .catch(() => setError(prev => ({ ...prev, [n]: 'Failed to load accumulators' })))
        .finally(() => setLoading(prev => ({ ...prev, [n]: false })))
    }
  }, [])

  // Lazy-load value bets for the matrix only when the section is first opened
  useEffect(() => {
    if (!matrixOpen || matrixFetched.current) return
    matrixFetched.current = true
    setMatrixLoading(true)
    api.get('/api/value-bets?min_edge=0.05&limit=20')
      .then(r => setMatrixBets(r.data.data ?? []))
      .catch(() => setMatrixError('Failed to load value bets for matrix'))
      .finally(() => setMatrixLoading(false))
  }, [matrixOpen])

  const rows = data[nLegs]

  const filtered = useMemo(() => {
    let result = rows
    if (wonFilter === 'WON')  result = result.filter(a => a.won)
    if (wonFilter === 'LOST') result = result.filter(a => !a.won)
    return [...result].sort((a, b) => {
      if (sortBy === 'ev')   return Number(b.acca_ev) - Number(a.acca_ev)
      if (sortBy === 'odds') return Number(b.combined_odds) - Number(a.combined_odds)
      if (sortBy === 'date') return (b.match_date ?? '').localeCompare(a.match_date ?? '')
      return 0
    })
  }, [rows, wonFilter, sortBy])

  const isLoading  = loading[nLegs]
  const fetchError = error[nLegs]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Accumulators</h1>
        <div className="flex gap-2">
          {[2, 3].map(n => (
            <button
              key={n}
              onClick={() => setNLegs(n)}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                nLegs === n
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
              }`}
            >
              {n}-Leg
            </button>
          ))}
        </div>
      </div>

      {/* EV Matrix — collapsible, default closed */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <button
          onClick={() => setMatrixOpen(o => !o)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-white">EV Matrix</span>
            <span className="text-xs text-gray-500">2-leg combination explorer</span>
          </div>
          <ChevronDown
            className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${matrixOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {matrixOpen && (
          <div className="border-t border-gray-800 p-4">
            {matrixLoading && (
              <div className="flex items-center gap-2 text-gray-400 py-4">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Loading value bets…</span>
              </div>
            )}
            {matrixError && (
              <p className="text-red-400 text-sm py-2">{matrixError}</p>
            )}
            {!matrixLoading && !matrixError && <EVMatrix bets={matrixBets} format={oddsFormat} />}
          </div>
        )}
      </div>

      {/* Info banner */}
      <div className="bg-[var(--brand-subtle)] border border-[var(--brand-border)] rounded-lg px-4 py-3 flex items-start gap-3">
        <span className="text-[var(--brand)] text-sm mt-0.5">ℹ</span>
        <div>
          <p className="text-sm font-medium text-[var(--brand)]">Historical Accumulator Tracker</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Historical accumulators built from value bets identified by the model.
            Each acca combines 2 or 3 legs with positive expected value. Results
            shown are actual outcomes. Live accumulators require odds API integration (coming soon).
          </p>
        </div>
      </div>

      {/* Filters + sort */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1">
          {[['ALL', 'All'], ['WON', 'Won'], ['LOST', 'Lost']].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setWonFilter(val)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                wonFilter === val
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-700 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-gray-500">Sort</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
          >
            {SORT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <span className="text-sm text-gray-500">
          Showing{' '}
          <span className="text-white font-medium">{filtered.length}</span>
          {filtered.length !== rows.length && ` of ${rows.length}`}
          {' '}accumulators
        </span>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          Loading accumulators…
        </div>
      )}

      {fetchError && (
        <div className="text-red-400 p-6">{fetchError}</div>
      )}

      {!isLoading && !fetchError && (
        <div className="space-y-3">
          {filtered.length === 0
            ? <p className="text-gray-500 text-sm">No accumulators found.</p>
            : filtered.map((acca, i) => <AccaCard key={i} acca={acca} format={oddsFormat} />)
          }
        </div>
      )}
    </div>
  )
}
