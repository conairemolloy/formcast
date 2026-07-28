import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import { Loader2, ShieldCheck, Copy, Check, X, Info } from 'lucide-react'

// ── helpers ──────────────────────────────────────────────────────────────────

function pct(v) {
  if (v == null) return '—'
  return (parseFloat(v) * 100).toFixed(1) + '%'
}

function fmt(v, decimals = 4) {
  if (v == null) return '—'
  return (parseFloat(v) * 100).toFixed(1) + '%'
}

function fmtDate(d) {
  if (!d) return '—'
  return d.slice(0, 10)
}

function fmtPublished(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
      timeZoneName: 'short',
    })
  } catch {
    return ts
  }
}

// ── sub-components ────────────────────────────────────────────────────────────

const OUTCOME_STYLE = {
  H: 'bg-[var(--bg-overlay)] text-[var(--text-secondary)] border border-[var(--border)]',
  D: 'bg-[var(--bg-overlay)] text-[var(--text-secondary)] border border-[var(--border)]',
  A: 'bg-[var(--bg-overlay)] text-[var(--text-secondary)] border border-[var(--border)]',
}
const OUTCOME_LABEL = { H: 'Home', D: 'Draw', A: 'Away' }

function OutcomeBadge({ outcome }) {
  if (!outcome) return <span className="text-gray-600">—</span>
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${OUTCOME_STYLE[outcome] ?? 'bg-gray-700 text-gray-300'}`}>
      {OUTCOME_LABEL[outcome] ?? outcome}
    </span>
  )
}

function CorrectBadge({ correct, actual }) {
  if (!actual) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-500 border border-gray-700">PENDING</span>
  if (correct === '1') return <span className="text-emerald-400 font-bold text-base">✓</span>
  return <span className="text-red-400 font-bold text-base">✗</span>
}

function HashCell({ hash }) {
  const [copied, setCopied] = useState(false)
  const [modal, setModal]   = useState(false)
  if (!hash) return <span className="text-gray-600">—</span>

  function copy(e) {
    e.stopPropagation()
    navigator.clipboard.writeText(hash).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <>
      <span className="flex items-center gap-1">
        <button
          onClick={() => setModal(true)}
          className="font-mono text-xs text-emerald-400 hover:text-emerald-300 underline underline-offset-2 cursor-pointer"
          title="Click to see full hash"
        >
          {hash.slice(0, 8)}
        </button>
        <button
          onClick={copy}
          className="text-gray-600 hover:text-gray-400 transition-colors"
          title="Copy full hash"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
        </button>
      </span>

      {modal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setModal(false)}
        >
          <div
            className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-lg w-full mx-4 space-y-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                <h3 className="font-semibold text-white">SHA-256 Prediction Hash</h3>
              </div>
              <button onClick={() => setModal(false)} className="text-gray-500 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-400 leading-relaxed">
              This hash proves the prediction was published before the match kicked off.
              It was computed from the prediction data and a UTC timestamp using SHA-256.
              Any change to the probabilities, outcome, or timestamp would produce a completely different hash.
            </p>

            <div className="bg-gray-950 rounded-lg p-3 border border-gray-800">
              <p className="text-[10px] text-gray-600 mb-1 uppercase tracking-wider">Full hash</p>
              <p className="font-mono text-xs text-emerald-300 break-all select-all">{hash}</p>
            </div>

            <div className="bg-gray-950 rounded-lg p-3 border border-gray-800 space-y-1">
              <p className="text-[10px] text-gray-600 mb-1 uppercase tracking-wider">Hash input format</p>
              <p className="font-mono text-[11px] text-gray-400 break-all">
                {"match_date|home_team|away_team|p_home|p_draw|p_away|predicted|published_at"}
              </p>
            </div>

            <button
              onClick={copy}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 transition-colors text-sm"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy full hash'}
            </button>
          </div>
        </div>
      )}
    </>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex-1 min-w-[120px]">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold tabular-nums text-white">{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function PredictionLog() {
  const [data,    setData]    = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const [leagueFilter,  setLeagueFilter]  = useState('all')
  const [statusFilter,  setStatusFilter]  = useState('all')  // all | pending | correct | incorrect
  const [showHashInfo,  setShowHashInfo]  = useState(false)

  useEffect(() => {
    api.get('/predictions/log')
      .then(r => {
        setData(r.data.data ?? [])
        setSummary(r.data.summary ?? null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const leagues = useMemo(() => {
    if (!summary?.leagues?.length) return []
    return summary.leagues
  }, [summary])

  const filtered = useMemo(() => {
    return data.filter(row => {
      if (leagueFilter !== 'all' && row.league !== leagueFilter) return false
      if (statusFilter === 'pending'   && row.actual_result)            return false
      if (statusFilter === 'correct'   && row.correct !== '1')          return false
      if (statusFilter === 'incorrect' && row.correct !== '0')          return false
      return true
    })
  }, [data, leagueFilter, statusFilter])

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-gray-500 gap-2">
      <Loader2 className="w-5 h-5 animate-spin" />
      Loading prediction log…
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-64 text-red-400 text-sm">
      Failed to load: {error}
    </div>
  )

  const hitRatePct = summary?.hit_rate != null
    ? (summary.hit_rate * 100).toFixed(1) + '%'
    : '—'

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Prediction Log</h1>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
            <ShieldCheck className="w-3.5 h-3.5" />
            Cryptographically verified
          </span>
        </div>
        <p className="text-sm text-gray-400">
          Every prediction published before kickoff. SHA-256 hashed and timestamped.{' '}
          <button
            className="text-emerald-400 underline underline-offset-2 hover:text-emerald-300"
            onClick={() => setShowHashInfo(v => !v)}
          >
            How does verification work?
          </button>
        </p>

        {showHashInfo && (
          <div className="mt-2 p-4 bg-gray-900 border border-emerald-500/20 rounded-xl text-sm text-gray-400 space-y-2 max-w-2xl">
            <p className="flex items-start gap-2">
              <Info className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              Each prediction is hashed using SHA-256 over a canonical string containing the
              match date, team names, probabilities, predicted outcome, and the UTC timestamp
              at which the prediction was published.
            </p>
            <p>
              Because the hash is computed and stored <em>before kickoff</em>, anyone can
              independently verify that the probabilities and predicted outcome were not altered
              after the result was known. Just reconstruct the input string and check that
              SHA-256 produces the same digest.
            </p>
          </div>
        )}
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="flex flex-wrap gap-3">
          <StatCard
            label="Total predictions"
            value={summary.total?.toLocaleString()}
            sub={summary.leagues?.length ? `${summary.leagues.length} leagues` : undefined}
          />
          <StatCard
            label="Hit rate"
            value={hitRatePct}
            sub={summary.settled ? `${summary.settled} settled` : undefined}
          />
          <StatCard
            label="Correct"
            value={summary.correct?.toLocaleString()}
            sub={summary.settled ? `of ${summary.settled} played` : undefined}
          />
          <StatCard
            label="Date range"
            value={summary.date_from ? summary.date_from.slice(0, 7) : '—'}
            sub={summary.date_to ? `to ${summary.date_to.slice(0, 10)}` : undefined}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={leagueFilter}
          onChange={e => setLeagueFilter(e.target.value)}
          className="bg-gray-900 border border-gray-700 text-gray-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          <option value="all">All leagues</option>
          {leagues.map(l => <option key={l} value={l}>{l}</option>)}
        </select>

        <div className="flex gap-1">
          {[
            { value: 'all',       label: 'All' },
            { value: 'pending',   label: 'Pending' },
            { value: 'correct',   label: '✓ Correct' },
            { value: 'incorrect', label: '✗ Incorrect' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === opt.value
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gray-900 text-gray-400 border border-gray-800 hover:text-white hover:border-gray-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <span className="text-xs text-gray-600 ml-auto">
          {filtered.length} of {data.length} predictions
        </span>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          {data.length === 0 ? 'No predictions published yet.' : 'No predictions match the current filters.'}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/60">
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">Published</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3">Match</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">League</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">Predicted</th>
                <th className="text-right text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">P(H)</th>
                <th className="text-right text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">P(D)</th>
                <th className="text-right text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">P(A)</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3 whitespace-nowrap">Result</th>
                <th className="text-center text-xs text-gray-500 font-medium px-3 py-3">✓/✗</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-3">Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {filtered.map((row, i) => (
                <tr
                  key={row.hash ?? i}
                  className={`hover:bg-gray-900/40 transition-colors ${
                    row.correct === '1' ? 'bg-emerald-950/10' :
                    row.correct === '0' ? 'bg-red-950/10' : ''
                  }`}
                >
                  <td className="px-3 py-2.5 text-xs text-gray-500 whitespace-nowrap">
                    <div>{fmtDate(row.published_at?.slice(0, 10))}</div>
                    <div className="text-[10px] text-gray-700">{row.published_at?.slice(11, 16)} UTC</div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-white whitespace-nowrap">
                      {row.home_team} <span className="text-gray-600">vs</span> {row.away_team}
                    </div>
                    <div className="text-[10px] text-gray-600">
                      {row.match_date}{row.match_time ? ` · ${row.match_time}` : ''}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-400 whitespace-nowrap max-w-[140px] truncate">
                    {row.league ?? '—'}
                  </td>
                  <td className="px-3 py-2.5">
                    <OutcomeBadge outcome={row.predicted_outcome} />
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-gray-300">
                    {pct(row.p_home)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-gray-300">
                    {pct(row.p_draw)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-gray-300">
                    {pct(row.p_away)}
                  </td>
                  <td className="px-3 py-2.5">
                    {row.actual_result
                      ? <OutcomeBadge outcome={row.actual_result} />
                      : <span className="text-[10px] text-gray-600 uppercase tracking-wider">—</span>
                    }
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <CorrectBadge correct={row.correct} actual={row.actual_result} />
                  </td>
                  <td className="px-3 py-2.5">
                    <HashCell hash={row.hash} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
