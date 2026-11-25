import { useState } from 'react'
import { ArrowRight, BarChart2, Lock, Shield } from 'lucide-react'
import '../remodel.css'
import InfoTip from './InfoTip'

// Remodelled landing (frontend/DESIGN.md). The reference page every other
// remodelled page matches. Lives at 'landing-new' alongside Landing.jsx until
// we swap deliberately.
//
// Claims on this page follow DESIGN.md §8 / ROADMAP "Current State & Honest
// Claims": no ROI, no CLV, no bare hit-rate, team count is 440+ / 11 leagues.
//
// InfoTips (glossary.js) sit where a term FIRST appears for a new visitor —
// once each, never on the hero.

const STATS = [
  // 1,168 of 1,170 log rows. The other 2 (Copa Libertadores, first publish run
  // 2026-05-26) were published 51 min after kickoff — match_time is UTC (from
  // football-data.org utcDate). Both are untracked-league rows and never settle.
  { value: '1,168',  label: 'Predictions published pre-kickoff' },
  { value: '608',    label: 'Predictions settled this season', tip: 'settled' },
  { value: '128k',   label: 'Matches in our database',         tip: 'matches-modelled' },
]

const NOT_A_TIPSTER = [
  'Probabilities, not promises',
  'No deleted losing streaks',
  'No black-box locks',
  'Just the numbers, on record',
]

const STEPS = [
  {
    title: 'Model the match',
    body: 'Five models — Elo, Glicko-2, Dixon-Coles, XGBoost and a dedicated draw classifier — each read the game on their own terms.',
  },
  {
    title: 'Price the outcome',
    body: <>A single meta-learner — a logistic regression trained only on predictions each model made before seeing the result — blends the five into one probability<InfoTip term="model" /> per outcome.</>,
  },
  {
    title: 'Show the difference',
    body: <>Our number goes next to the bookmaker’s<InfoTip term="book-price" />. Where the gap is real, that’s the edge — timestamped and sealed when published, logged win or lose.</>,
  },
]

const FEATURES = [
  { title: 'Today’s tips',               body: 'The day’s best value bets, ranked by edge.' },
  { title: 'Value bets',                 body: 'Every price where our probability beats the market’s, with the gap shown.' },
  { title: 'Verified track record',      body: 'Every call timestamped and sealed, and settled in public where we track results.' },
  { title: 'Team ratings',               body: '440+ teams across 11 leagues, rated after every match.' },
  { title: 'Accumulators',               body: 'Multi-leg builds from the value card, with the combined probability shown.' },
  { title: 'International football hub', body: 'National-team ratings, plus World Cup 2026 results and the bracket.' },
]

const pad = n => String(n).padStart(2, '0')

function PrimaryButton({ onClick, children, type = 'button' }) {
  return (
    <button type={type} onClick={onClick} className="rl-btn rl-btn--primary">
      {children}
      <ArrowRight className="rl-btn-icon" aria-hidden="true" />
    </button>
  )
}

function Eyebrow({ children, pill = false }) {
  return <p className={pill ? 'rl-eyebrow rl-eyebrow--pill' : 'rl-eyebrow'}>{children}</p>
}

export default function LandingNew({ onNavigate, onShowAuth }) {
  const [email, setEmail]         = useState('')
  const [emailNote, setEmailNote] = useState('')

  // App's handleNav doesn't reset scroll; from deep on this page that would
  // land the user mid-way down the next page.
  function go(id) {
    window.scrollTo(0, 0)
    onNavigate?.(id)
  }

  const signUp = () => onShowAuth?.()

  function handleEmailSubmit(e) {
    e.preventDefault()
    // TODO(digest): POST to the Resend daily-digest signup endpoint once it exists.
    console.info('[LandingNew] digest signup (no-op):', email)
    setEmailNote('Thanks — the daily email isn’t live yet, so nothing was saved. Sign up free to get tips today.')
  }

  return (
    <div className="remodel remodel-page">

      {/* ── 1. HERO ── */}
      <section className="rl-section rl-hero">
        <div className="rl-container rl-hero-grid">
          <div>
            <Eyebrow pill>Matchday, made measurable</Eyebrow>
            <h1 className="rl-display-xl">
              The odds are a <em>starting point.</em>
            </h1>
            <p className="rl-lede">
              Five models find the mispricing hiding in the market.
              Every call is timestamped and sealed. Every result stays on record.
            </p>
            <div className="rl-cta-row">
              <PrimaryButton onClick={signUp}>Sign up free</PrimaryButton>
              <button type="button" className="rl-btn rl-btn--outline" onClick={() => go('prediction-log')}>
                Explore the public ledger
              </button>
            </div>
          </div>

          {/* Slot for the live public-ledger / fixture cards (DESIGN.md §5.2).
              Deliberately empty — no fabricated fixtures, hashes or record numbers.
              Wire to the real ledger feed when the card primitive is built. */}
          <div className="rl-hero-slot" aria-hidden="true">
            <div className="rl-hero-slot-head">
              <span>Public ledger</span>
              <span>SHA-256 sealed</span>
            </div>
            <div className="rl-hero-slot-rows">
              <span /><span /><span />
            </div>
            <p className="rl-hero-slot-note">Live ledger cards — slot</p>
          </div>
        </div>
      </section>

      {/* ── 2. STAT STRIP + NOT A TIPSTER ── */}
      <section className="rl-stats">
        <div className="rl-container">
          <dl className="rl-stat-grid">
            {STATS.map(s => (
              <div key={s.label} className="rl-stat">
                <dt className="rl-stat-label">{s.label}{s.tip && <InfoTip term={s.tip} />}</dt>
                <dd className="rl-stat-value">{s.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="rl-tipster">
          <div className="rl-container rl-tipster-row">
            <span className="rl-tipster-lead">Not a tipster.</span>
            {NOT_A_TIPSTER.map(t => (
              <span key={t} className="rl-tipster-item">
                <ArrowRight className="rl-tipster-arrow" aria-hidden="true" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. GATED TODAY'S TIPS ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container rl-split">
          <div>
            <Eyebrow>Today’s tips</Eyebrow>
            <h2 className="rl-display">Today’s tips are live.</h2>
            <p className="rl-body rl-body--fg">
              Today’s best value bets<InfoTip term="value-bet" />, ranked by edge<InfoTip term="edge" />.
            </p>
            <p className="rl-body">Football now — more sports coming. Pick the ones you follow.</p>
          </div>
          <div className="rl-locked">
            <Lock className="rl-locked-icon" aria-hidden="true" />
            <h3 className="rl-h3">Members only.</h3>
            <p className="rl-body">
              Every value bet we’ve found today, ranked by edge. Sign up to see the full card.
            </p>
            <PrimaryButton onClick={signUp}>Sign up free</PrimaryButton>
          </div>
        </div>
      </section>

      {/* ── 4. ABOUT ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container rl-about">
          <img src="/conaire.jpg" alt="Conaire Molloy" className="rl-photo" />
          <div>
            <Eyebrow>Who built this</Eyebrow>
            <h2 className="rl-display">
              Conaire Molloy — <em>Data Analyst</em>
            </h2>
            <p className="rl-body">
              Data analyst with a maths and finance background. Built the
              five-model ensemble solo. No tipping service — just a model, and every
              result logged publicly.
            </p>
          </div>
        </div>
      </section>

      {/* ── 5. 01 — A BETTER READ ON THE GAME ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container">
          <Eyebrow>01 — A better read on the game</Eyebrow>
          <h2 className="rl-display">One match. Five points of view.</h2>
          <ol className="rl-steps">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rl-step">
                <span className="rl-index">{pad(i + 1)}/{pad(STEPS.length)}</span>
                <h3 className="rl-h3">{s.title}</h3>
                <p className="rl-body">{s.body}</p>
              </li>
            ))}
          </ol>
          <button type="button" className="rl-link" onClick={() => go('how-it-works')}>
            How the ensemble works <ArrowRight className="rl-btn-icon" aria-hidden="true" />
          </button>
        </div>
      </section>

      {/* ── 6. 02 — OUR MOST IMPORTANT FEATURE ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container rl-split">
          <div>
            <Eyebrow>02 — Our most important feature</Eyebrow>
            <h2 className="rl-display">
              An open book. <em>Even on a bad day.</em>
            </h2>
          </div>
          <div className="rl-proof-list">
            <div className="rl-proof-item">
              <Shield className="rl-proof-icon" aria-hidden="true" />
              <div>
                <h3 className="rl-h3">Sealed and timestamped</h3>
                <p className="rl-body">
                  Every prediction gets a SHA-256 fingerprint and a timestamp when
                  it’s published — all but two so far before the first whistle, and
                  every settled one. Change a single digit afterwards and the
                  fingerprint no longer matches.
                </p>
              </div>
            </div>
            <div className="rl-proof-item">
              <span className="rl-proof-icon rl-proof-icon--spacer" aria-hidden="true" />
              <div>
                <h3 className="rl-h3">The whole record. No edits.</h3>
                <p className="rl-body">
                  Wins, misses and bad days all stay on the ledger. Nothing quietly
                  disappears when the final whistle goes.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 7. EVERYTHING INSIDE ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container">
          <Eyebrow>Everything inside</Eyebrow>
          <h2 className="rl-display">A clearer view of every match.</h2>
          <ol className="rl-features">
            {FEATURES.map((f, i) => (
              <li key={f.title} className="rl-feature">
                <span className="rl-index">{pad(i + 1)}</span>
                <span className="rl-feature-title">{f.title}</span>
                <span className="rl-feature-body">{f.body}</span>
              </li>
            ))}
          </ol>
          <PrimaryButton onClick={signUp}>Sign up free</PrimaryButton>
        </div>
      </section>

      {/* ── 8. EMAIL CAPTURE ── */}
      <section className="rl-section rl-rule">
        <div className="rl-container rl-split">
          <div>
            <Eyebrow>A note when there’s value</Eyebrow>
            <h2 className="rl-display">Get today’s tips in your inbox.</h2>
            <p className="rl-body">
              One email a day with the best value bets we’ve found. Nothing when
              there’s nothing worth sending.
            </p>
          </div>
          <form className="rl-email" onSubmit={handleEmailSubmit}>
            <label htmlFor="rl-email-input" className="rl-sr-only">Email address</label>
            <input
              id="rl-email-input"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => { setEmail(e.target.value); setEmailNote('') }}
              className="rl-input"
            />
            <PrimaryButton type="submit">Keep me posted</PrimaryButton>
            {emailNote && <p className="rl-small" role="status">{emailNote}</p>}
          </form>
        </div>
      </section>

      {/* ── 9. FOOTER ── */}
      <footer className="rl-footer">
        <div className="rl-container rl-footer-grid">
          <div>
            <p className="rl-logo">
              <BarChart2 className="rl-logo-mark" aria-hidden="true" />
              FormCast
            </p>
            <p className="rl-body">A clearer view of the game.</p>
          </div>
          <div className="rl-footer-cta">
            <PrimaryButton onClick={signUp}>Sign up free</PrimaryButton>
          </div>
        </div>
        <div className="rl-container rl-footer-base">
          <p className="rl-small">
            For informational and research purposes only. Not financial advice.
            Bet responsibly. 18+ only. Availability subject to your jurisdiction.
          </p>
          <nav className="rl-footer-links" aria-label="Footer">
            <button type="button" onClick={() => go('how-it-works')}>How it works</button>
            <span aria-hidden="true">·</span>
            <button type="button" onClick={() => go('prediction-log')}>Public ledger</button>
            <span aria-hidden="true">·</span>
            <span>© FormCast 2026</span>
          </nav>
        </div>
      </footer>
    </div>
  )
}
