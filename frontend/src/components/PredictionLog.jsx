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
  H: 'bg-[var(--muted)] text-[var(--foreground)] border border-[var(--border)]',
  D: 'bg-[var(--muted)] text-[var(--foreground)] border border-[var(--border)]',
  A: 'bg-[var(--muted)] text-[var(--foreground)] border border-[var(--border)]',
}
const OUTCOME_LABEL = { H: 'Home', D: 'Draw', A: 'Away' }

function OutcomeBadge({ outcome }) {
  if (!outcome) return <span className="text-[var(--muted-foreground)]/60">—</span>
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${OUTCOME_STYLE[outcome] ?? 'bg-[var(--muted)] text-[var(--foreground)]'}`}>
      {OUTCOME_LABEL[outcome] ?? outcome}
    </span>
  )
}

function CorrectBadge({ correct, actual, status }) {
  if (status === 'not_tracked') return (
    <span
      title="League not covered by our results data, so this prediction can't be settled"
      className="fc-badge cursor-help"
    >
      NOT TRACKED
    </span>
  )
  if (!actual) return <span className="fc-badge fc-badge--pending">PENDING</span>
  if (correct === '1') return <span className="fc-badge fc-badge--positive">✓</span>
  return <span className="fc-badge fc-badge--negative">✗</span>
}

function HashCell({ hash }) {
  const [copied, setCopied] = useState(false)
  const [modal, setModal]   = useState(false)
  if (!hash) return <span className="text-[var(--muted-foreground)]/60">—</span>

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
          className="font-mono text-xs text-[var(--primary)] hover:text-[var(--ring)] underline underline-offset-2 cursor-pointer"
          title="Click to see full hash"
        >
          {hash.slice(0, 8)}
        </button>
        <button
          onClick={copy}
          className="text-[var(--muted-foreground)]/60 hover:text-[var(--muted-foreground)] transition-colors"
          title="Copy full hash"
        >
          {copied ? <Check className="w-3 h-3 text-[var(--chart-2)]" /> : <Copy className="w-3 h-3" />}
        </button>
      </span>

      {modal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setModal(false)}
        >
          <div
            className="fc-card p-6 max-w-lg w-full mx-4 space-y-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[var(--chart-2)] shrink-0" />
                <h3 className="font-semibold text-[var(--foreground)]">SHA-256 Prediction Hash</h3>
              </div>
              <button onClick={() => setModal(false)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
              This hash proves the prediction and its publish timestamp were sealed at publication and not altered afterwards.
              It was computed from the prediction data and a UTC timestamp using SHA-256.
              Any change to the probabilities, outcome, or timestamp would produce a completely different hash.
            </p>

            <div className="bg-[var(--background)] rounded-lg p-3 border border-[var(--border)]">
              <p className="text-[10px] text-[var(--muted-foreground)]/60 mb-1 uppercase tracking-wider">Full hash</p>
              <p className="font-mono text-xs text-[var(--foreground)] break-all select-all">{hash}</p>
            </div>

            <div className="bg-[var(--background)] rounded-lg p-3 border border-[var(--border)] space-y-1">
              <p className="text-[10px] text-[var(--muted-foreground)]/60 mb-1 uppercase tracking-wider">Hash input format</p>
              <p className="font-mono text-[11px] text-[var(--muted-foreground)] break-all">
                {"match_date|home_team|away_team|p_home|p_draw|p_away|predicted|published_at"}
              </p>
            </div>

            <button
              onClick={copy}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-[var(--primary)]/30 text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors text-sm"
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
    <div className="fc-card p-4 flex-1 min-w-[120px]">
      <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold tabular-nums text-[var(--foreground)]">{value ?? '—'}</p>
      {sub && <p className="text-xs text-[var(--muted-foreground)]/60 mt-0.5">{sub}</p>}
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
  const [statusFilter,  setStatusFilter]  = useState('all')  // all | pending | not_tracked | correct | incorrect
  const [showHashInfo,  setShowHashInfo]  = useState(false)

  useEffect(() => {
    api.get('/api/predictions/log')
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
      if (statusFilter === 'pending'     && row.status !== 'pending')     return false
      if (statusFilter === 'not_tracked' && row.status !== 'not_tracked') return false
      if (statusFilter === 'correct'   && row.correct !== '1')          return false
      if (statusFilter === 'incorrect' && row.correct !== '0')          return false
      return true
    })
  }, [data, leagueFilter, statusFilter])

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-[var(--muted-foreground)] gap-2">
      <Loader2 className="w-5 h-5 animate-spin" />
      Loading prediction log…
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-64 text-[var(--chart-5)] text-sm">
      Failed to load: {error}
    </div>
  )

  const hitRatePct = summary?.hit_rate != null
    ? (summary.hit_rate * 100).toFixed(1) + '%'
    : '—'

  return (
    <div className="fc-page space-y-6">

      {/* Header */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Prediction Log</h1>
          <span className="fc-badge fc-badge--positive">
            <ShieldCheck className="w-3.5 h-3.5" />
            Cryptographically verified
          </span>
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">
          Each prediction is SHA-256 hashed and timestamped when published — every settled prediction before kick-off.{' '}
          <button
            className="text-[var(--primary)] underline underline-offset-2 hover:text-[var(--ring)]"
            onClick={() => setShowHashInfo(v => !v)}
          >
            How does verification work?
          </button>
        </p>

        {showHashInfo && (
          <div className="fc-card mt-2 p-4 text-sm text-[var(--muted-foreground)] space-y-2 max-w-2xl">
            <p className="flex items-start gap-2">
              <Info className="w-4 h-4 text-[var(--primary)] mt-0.5 shrink-0" />
              Each prediction is hashed using SHA-256 over a canonical string containing the
              match date, team names, probabilities, predicted outcome, and the UTC timestamp
              at which the prediction was published.
            </p>
            <p>
              Because the hash is computed and stored <em>at publication</em>, anyone can
              independently verify that the probabilities, predicted outcome and publish timestamp
              were not altered afterwards. Just reconstruct the input string and check that
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
            value={(summary.tracked ?? summary.total)?.toLocaleString()}
            sub={[
              summary.leagues?.length ? `${summary.leagues.length} leagues` : null,
              summary.not_tracked ? `+${summary.not_tracked.toLocaleString()} not tracked` : null,
            ].filter(Boolean).join(' · ') || undefined}
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
          className="fc-input text-xs rounded-lg px-3 py-2"
        >
          <option value="all">All leagues</option>
          {leagues.map(l => <option key={l} value={l}>{l}</option>)}
        </select>

        <div className="flex gap-1">
          {[
            { value: 'all',       label: 'All' },
            { value: 'pending',   label: 'Pending' },
            { value: 'not_tracked', label: 'Not tracked' },
            { value: 'correct',   label: '✓ Correct' },
            { value: 'incorrect', label: '✗ Incorrect' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === opt.value
                  ? 'bg-[var(--primary)]/12 text-[var(--primary)] border border-[var(--primary)]/30'
                  : 'bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--input)]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <span className="text-xs text-[var(--muted-foreground)]/60 ml-auto">
          {filtered.length} of {data.length} predictions
        </span>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-[var(--muted-foreground)]/60">
          {data.length === 0 ? 'No predictions published yet.' : 'No predictions match the current filters.'}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--card)]">
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">Published</th>
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3">Match</th>
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">League</th>
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">Predicted</th>
                <th className="text-right text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">P(H)</th>
                <th className="text-right text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">P(D)</th>
                <th className="text-right text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">P(A)</th>
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3 whitespace-nowrap">Result</th>
                <th className="text-center text-xs text-[var(--muted-foreground)] font-medium px-3 py-3">✓/✗</th>
                <th className="text-left text-xs text-[var(--muted-foreground)] font-medium px-3 py-3">Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filtered.map((row, i) => (
                <tr
                  key={row.hash ?? i}
                  className={`hover:bg-[var(--card)] transition-colors ${
                    row.correct === '1' ? 'bg-[var(--chart-2)]/5' :
                    row.correct === '0' ? 'bg-[var(--chart-5)]/5' : ''
                  }`}
                >
                  <td className="px-3 py-2.5 text-xs text-[var(--muted-foreground)] whitespace-nowrap">
                    <div>{fmtDate(row.published_at?.slice(0, 10))}</div>
                    <div className="text-[10px] text-[var(--muted-foreground)]/60">{row.published_at?.slice(11, 16)} UTC</div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-[var(--foreground)] whitespace-nowrap">
                      {row.home_team} <span className="text-[var(--muted-foreground)]/60">vs</span> {row.away_team}
                    </div>
                    <div className="text-[10px] text-[var(--muted-foreground)]/60">
                      {row.match_date}{row.match_time ? ` · ${row.match_time}` : ''}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-[var(--muted-foreground)] whitespace-nowrap max-w-[140px] truncate">
                    {row.league ?? '—'}
                  </td>
                  <td className="px-3 py-2.5">
                    <OutcomeBadge outcome={row.predicted_outcome} />
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-[var(--foreground)]">
                    {pct(row.p_home)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-[var(--foreground)]">
                    {pct(row.p_draw)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs tabular-nums text-[var(--foreground)]">
                    {pct(row.p_away)}
                  </td>
                  <td className="px-3 py-2.5">
                    {row.actual_result
                      ? <OutcomeBadge outcome={row.actual_result} />
                      : <span className="text-[10px] text-[var(--muted-foreground)]/60 uppercase tracking-wider">—</span>
                    }
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <CorrectBadge correct={row.correct} actual={row.actual_result} status={row.status} />
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
