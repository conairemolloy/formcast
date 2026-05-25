import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

function LegPill({ home, away, outcome, odds }) {
  if (typeof home !== 'string' || typeof away !== 'string') return null
  return (
    <span className="inline-flex items-center gap-1 bg-gray-800 rounded px-2 py-0.5 text-xs text-gray-300 mr-1 mb-1">
      <span className="font-medium text-white">{home} vs {away}</span>
      <span className="text-gray-500">·</span>
      <span className="font-mono text-blue-400">{outcome ?? '—'}</span>
      <span className="text-gray-600">@{Number(odds)?.toFixed(2) ?? '—'}</span>
    </span>
  )
}

function AccaCard({ acca }) {
  const ev = Number(acca.acca_ev)
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex flex-wrap gap-1">
          <LegPill home={acca.leg1_home} away={acca.leg1_away} outcome={acca.leg1_outcome} odds={acca.leg1_odds} />
          <LegPill home={acca.leg2_home} away={acca.leg2_away} outcome={acca.leg2_outcome} odds={acca.leg2_odds} />
          <LegPill home={acca.leg3_home} away={acca.leg3_away} outcome={acca.leg3_outcome} odds={acca.leg3_odds} />
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
            {Number(acca.combined_odds)?.toFixed(2) ?? '—'}
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

export default function Accumulators() {
  const [data, setData]         = useState({ 2: [], 3: [] })
  const [loading, setLoading]   = useState({ 2: true, 3: true })
  const [error, setError]       = useState({ 2: null, 3: null })
  const [nLegs, setNLegs]       = useState(2)
  const [wonFilter, setWonFilter] = useState('ALL')
  const [sortBy, setSortBy]     = useState('ev')

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

  const isLoading = loading[nLegs]
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

      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg px-4 py-3 flex items-start gap-3">
        <span className="text-blue-400 text-sm mt-0.5">ℹ</span>
        <div>
          <p className="text-sm font-medium text-blue-300">Historical Accumulator Tracker</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Historical accumulators built from value bets identified by the model.
            Each acca combines 2 or 3 legs with positive expected value. Results
            shown are actual outcomes. Live accumulators require odds API integration (coming soon).
          </p>
        </div>
      </div>

      {/* Filters + sort */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Won / Lost filter */}
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

        {/* Sort */}
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
            : filtered.map((acca, i) => <AccaCard key={i} acca={acca} />)
          }
        </div>
      )}
    </div>
  )
}
