import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

function LegPill({ home, away, outcome, odds }) {
  if (!home) return null
  return (
    <span className="inline-flex items-center gap-1 bg-gray-800 rounded px-2 py-0.5 text-xs text-gray-300 mr-1 mb-1">
      <span className="font-medium text-white">{home} vs {away}</span>
      <span className="text-gray-500">·</span>
      <span className="font-mono text-blue-400">{outcome}</span>
      <span className="text-gray-600">@{odds}</span>
    </span>
  )
}

export default function Accumulators() {
  const [data, setData]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [nLegs, setNLegs]     = useState(2)

  useEffect(() => {
    axios.get(`/api/accumulator?n_legs=${nLegs}&limit=20`)
      .then(r => setData(r.data.data))
      .catch(() => setError('Failed to load accumulators'))
      .finally(() => setLoading(false))
  }, [nLegs])

  const handleLegsChange = (n) => {
    setLoading(true)
    setNLegs(n)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading accumulators…
    </div>
  )
  if (error) return <div className="text-red-400 p-6">{error}</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Accumulators</h1>
        <div className="flex gap-2">
          {[2, 3].map(n => (
            <button
              key={n}
              onClick={() => handleLegsChange(n)}
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

      <div className="space-y-3">
        {data.map((acca, i) => (
          <div
            key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <div className="flex flex-wrap gap-1">
                <LegPill home={acca.leg1_home} away={acca.leg1_away} outcome={acca.leg1_outcome} odds={acca.leg1_odds} />
                <LegPill home={acca.leg2_home} away={acca.leg2_away} outcome={acca.leg2_outcome} odds={acca.leg2_odds} />
                {acca.n_legs === 3 && (
                  <LegPill home={acca.leg3_home} away={acca.leg3_away} outcome={acca.leg3_outcome} odds={acca.leg3_odds} />
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {acca.won
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  : <XCircle className="w-5 h-5 text-red-500" />
                }
              </div>
            </div>

            <div className="flex gap-6 text-sm">
              <div>
                <span className="text-gray-500 text-xs">Combined Odds</span>
                <p className="font-mono font-semibold text-white">{acca.combined_odds}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Model Prob</span>
                <p className="font-mono font-semibold text-gray-300">{(acca.combined_p * 100).toFixed(1)}%</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs">EV</span>
                <p className={`font-mono font-semibold ${acca.acca_ev > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {acca.acca_ev > 0 ? '+' : ''}{acca.acca_ev.toFixed(3)}
                </p>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Date</span>
                <p className="font-mono text-gray-400 text-xs mt-0.5">{acca.match_date}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
