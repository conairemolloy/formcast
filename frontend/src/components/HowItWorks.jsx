const MODELS = [
  {
    name: 'Elo Rating',
    desc: 'Dynamic strength rating updated after every result. Teams gain points for wins, lose for losses, with larger swings for upsets.',
    formula: 'E(A) = 1 / (1 + 10^(-(R_A - R_B) / 400))',
    metric: 'Dynamic strength rating, updated every match',
    metricColor: 'text-[var(--text-secondary)]',
  },
  {
    name: 'Glicko-2',
    desc: 'Extends Elo with a confidence interval (RD) and consistency measure (σ). New teams start uncertain; certainty grows with more matches.',
    formula: 'E = 1 / (1 + exp(-g(φ) × (μ_A - μ_B)))',
    metric: 'Uncertainty-aware ratings',
    metricColor: 'text-[var(--text-secondary)]',
  },
  {
    name: 'Dixon-Coles',
    desc: 'Models the number of goals each team scores using Poisson distributions, with a correction for low-scoring matches near 0-0.',
    formula: 'P(x,y) = τ(x,y) × P(X=x) × P(Y=y)',
    metric: 'Full scoreline probabilities',
    metricColor: 'text-[var(--text-secondary)]',
  },
  {
    name: 'XGBoost',
    desc: 'Gradient-boosted decision trees trained on 78 engineered features including form, fatigue, H2H history, and xG statistics.',
    formula: 'F(x) = Σ f_k(x),  minimising log-loss',
    metric: 'Feature-driven H/D/A probabilities',
    metricColor: 'text-[var(--text-secondary)]',
  },
  {
    name: 'Draw Classifier',
    desc: 'A dedicated binary gradient-boosted model, trained on 13 draw-relevant features, that estimates only the chance of a draw — the hardest outcome to call. Its output is one of the inputs the meta-learner blends.',
    formula: 'P(draw) = XGB_binary(x_draw)',
    metric: 'Specialist draw probability',
    metricColor: 'text-[var(--text-secondary)]',
  },
]

const GLOSSARY = [
  {
    term: 'Brier Score',
    def: 'Mean squared error of probability estimates. Lower is better. A uniform 3-outcome guess (⅓ each) scores 0.667 (multiclass Brier, range 0–2).',
  },
  {
    term: 'Expected Value (EV)',
    def: 'EV = P_model × odds − 1. Positive means the bet is underpriced relative to the true probability.',
  },
  {
    term: 'Walk-Forward Testing',
    def: 'Predictions made only using data available at the time. No future information leaks into the model.',
  },
  {
    term: 'Kelly Criterion',
    def: 'Optimal stake fraction = edge / (odds − 1). Half-Kelly is used in practice for reduced variance.',
  },
  {
    term: 'xG (Expected Goals)',
    def: 'Probability that a shot results in a goal, based on position, angle, and match situation.',
  },
]

const DATA_SOURCES = [
  {
    source: 'football-data.co.uk',
    coverage: '11 leagues · 1993–2026',
    provides: 'Results, bookmaker odds, match statistics',
  },
  {
    source: 'Understat',
    coverage: 'Top 5 leagues · 2014–2025',
    provides: 'Expected Goals (xG) for shots and matches. Feed currently paused — matches since May 2025 have no xG.',
  },
  {
    source: 'football-data.org',
    coverage: 'Live + upcoming fixtures',
    provides: 'Real-time scores, minute-by-minute updates',
  },
  {
    source: 'Supabase',
    coverage: 'All 128,602 matches',
    provides: 'Database hosting processed data for the API',
  },
]

function FormulaBlock({ formula }) {
  return (
    <div className="mt-3 rounded-md px-3 py-2 bg-gray-950 border border-gray-800">
      <code className="text-xs font-mono text-gray-400 break-all">{formula}</code>
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.2em] mb-2">
      {children}
    </p>
  )
}

export default function HowItWorks() {
  return (
    <div className="space-y-12 max-w-5xl mx-auto">

      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">How It Works</h1>
        <p className="text-gray-400 text-sm sm:text-base">
          The mathematics behind FormCast's predictions.
        </p>
      </div>

      {/* Section 1 — Overview */}
      <section className="space-y-4">
        <SectionLabel>Overview</SectionLabel>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-6 space-y-4">
          <p className="text-gray-300 leading-relaxed">
            FormCast combines <span className="text-white font-semibold">5 models</span> — Elo, Glicko-2,
            Dixon-Coles, XGBoost and a draw classifier — into
            a single ensemble. Each model sees football differently — some track rating momentum, some
            model goal distributions, some learn from raw features. No single model captures everything,
            so we let them vote.
          </p>
          <p className="text-gray-400 leading-relaxed text-sm">
            The ensemble is a meta-learner trained on out-of-fold predictions from all 5 models. It learns
            how much to trust each model, then outputs a final probability for each of the three
            outcomes: home win, draw, away win.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {[
              { value: '128,602', label: 'Matches in database', sub: '1993–2026 · Elo history' },
              { value: '50,298',  label: 'Ensemble training', sub: '2014+ · xG era' },
              { value: '1993–2026', label: 'Time span' },
              { value: '11', label: 'Leagues' },
            ].map(({ value, label, sub }) => (
              <div key={label} className="text-center bg-gray-950 rounded-lg py-4 border border-gray-800">
                <p className="text-xl sm:text-2xl font-black font-mono text-emerald-400 tabular-nums">{value}</p>
                <p className="text-[10px] font-mono text-gray-600 uppercase tracking-wider mt-1">{label}</p>
                {sub && <p className="text-[10px] text-gray-600 mt-0.5">{sub}</p>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 2 — The Models */}
      <section className="space-y-4">
        <SectionLabel>The Models</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {MODELS.map(({ name, desc, formula, metric, metricColor }) => (
            <div
              key={name}
              className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col"
            >
              <p className="text-sm font-bold text-white mb-1">{name}</p>
              <p className="text-xs text-gray-500 leading-relaxed flex-1">{desc}</p>
              <FormulaBlock formula={formula} />
              <p className={`text-xs font-semibold mt-3 ${metricColor}`}>{metric}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3 — The Ensemble */}
      <section className="space-y-4">
        <SectionLabel>The Ensemble</SectionLabel>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-6 space-y-5">
          <p className="text-gray-300 leading-relaxed text-sm">
            The 5 models' outputs — probability vectors such as{' '}
            <code className="text-xs font-mono text-gray-400 bg-gray-950 px-1.5 py-0.5 rounded">[P(H), P(D), P(A)]</code>,
            rating gaps and the draw classifier's P(draw) — feed one global meta-learner: a logistic regression
            trained on out-of-fold predictions (time-ordered splits), so it never learns from a match it is scoring.
          </p>

          {/* Flow diagram */}
          <div className="overflow-x-auto">
            <div className="flex items-center gap-2 min-w-max py-2">
              <div className="flex flex-col gap-1.5">
                {MODELS.map(({ name }) => (
                  <div
                    key={name}
                    className="px-3 py-1.5 rounded-md border border-gray-700 bg-gray-950 text-xs font-mono text-gray-400 whitespace-nowrap"
                  >
                    {name}
                  </div>
                ))}
              </div>

              <div className="flex flex-col items-center gap-0.5 px-2">
                {MODELS.map((_, i) => (
                  <div key={i} className="w-8 border-t border-dashed border-gray-700 mt-3" />
                ))}
              </div>

              <div className="flex flex-col items-center justify-center self-stretch">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 text-center">
                  <p className="text-xs font-bold text-emerald-400 whitespace-nowrap">Meta-learner</p>
                  <p className="text-[10px] text-gray-500 mt-0.5 whitespace-nowrap">Logistic regression</p>
                </div>
              </div>

              <div className="w-8 border-t border-dashed border-emerald-600/50" />

              <div className="bg-gray-950 border border-emerald-500/20 rounded-xl px-4 py-3 text-center">
                <p className="text-xs font-bold text-white whitespace-nowrap">Final probability</p>
                <p className="text-[10px] font-mono text-emerald-400 mt-0.5 whitespace-nowrap">[P(H), P(D), P(A)]</p>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-2 text-xs text-gray-500 bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5">
            <span className="text-[var(--brand)] shrink-0">ℹ</span>
            <span>
              Evaluation: the ensemble is trained on the first 80% of matches (to March 2024) and scored on
              the most recent 20% it never saw (10,060 matches). The deployed model is then refit on all data
              through the latest completed match, so live predictions use the full history.
            </span>
          </div>
        </div>
      </section>

      {/* Section 4 — Glossary */}
      <section className="space-y-4">
        <SectionLabel>Key Concepts</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {GLOSSARY.map(({ term, def }) => (
            <div key={term} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-sm font-semibold text-emerald-400 mb-1.5">{term}</p>
              <p className="text-xs text-gray-500 leading-relaxed">{def}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Section 5 — Data Sources */}
      <section className="space-y-4">
        <SectionLabel>Data Sources</SectionLabel>
        <div className="rounded-xl border border-gray-800 overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-gray-400 font-medium text-xs">Source</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium text-xs">Coverage</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium text-xs">Provides</th>
              </tr>
            </thead>
            <tbody>
              {DATA_SOURCES.map(({ source, coverage, provides }, i) => (
                <tr
                  key={source}
                  className={`${i < DATA_SOURCES.length - 1 ? 'border-b border-gray-800/60' : ''} hover:bg-gray-800/30 transition-colors`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-emerald-400 whitespace-nowrap">{source}</td>
                  <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{coverage}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{provides}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

    </div>
  )
}
