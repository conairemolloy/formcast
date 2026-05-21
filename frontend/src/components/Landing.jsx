import { Activity, Target, Shuffle, ExternalLink, BarChart2, ArrowRight } from 'lucide-react'

const TICKER_ITEMS = [
  '128,797 matches',
  '14 competitions',
  '68.7% walk-forward accuracy',
  'Brier Score 0.156',
  'Bayern Munich Elo 2051',
  'Arsenal Elo 1993',
  'Real Madrid Elo 2087',
  'Man City Elo 2045',
  'Liverpool Elo 1978',
  'Ensemble AUC 0.731',
  '33 years of data',
  '1993 → 2026',
]

const STATS = [
  { value: '128,797', label: 'Matches Analysed',      emerald: true  },
  { value: '68.7%',   label: 'Walk-Forward Accuracy', emerald: true  },
  { value: '0.156',   label: 'Brier Score',           emerald: false },
  { value: '14',      label: 'Competitions',          emerald: false },
]

const MODELS = [
  { name: 'Elo Rating',     desc: 'Dynamic pairwise strength rating updated after every result',          metric: 'K-factor competition-tuned',    top: true  },
  { name: 'Glicko-2',       desc: 'Bayesian extension with uncertainty (RD) and volatility (σ)',          metric: 'RD < 45 for active clubs',      top: true  },
  { name: 'Dixon-Coles',    desc: 'Bivariate Poisson goal model with low-score correction',              metric: 'ρ correction α = 0.13',          top: true  },
  { name: 'Bradley-Terry',  desc: 'Maximum-likelihood pairwise comparison over all historical results',  metric: 'Newton-Raphson convergence',    top: false },
  { name: 'XGBoost',        desc: 'Gradient-boosted trees trained on 47 engineered match features',      metric: 'Holdout AUC 0.731',             top: false },
  { name: 'Feedforward NN', desc: 'Deep network on form, fatigue, and contextual match features',        metric: '5 layers · 512 hidden units',   top: false },
  { name: 'LSTM',           desc: 'Recurrent sequence model trained on sequential match history',         metric: '12-match temporal window',      top: false },
]

const FEATURES = [
  {
    Icon: Activity,
    title: 'Live Win Probabilities',
    desc:  'Real-time in-play probability updates as the match unfolds. The ensemble re-evaluates after every goal, red card, and penalty.',
    tab:   'live',
    cta:   'Watch Live',
  },
  {
    Icon: Target,
    title: 'Value Bet Screener',
    desc:  'Surface positive expected value opportunities before the market closes. Model-calibrated probabilities vs. bookmaker implied odds.',
    tab:   'value-bets',
    cta:   'Screen Bets',
  },
  {
    Icon: Shuffle,
    title: 'Tournament Simulator',
    desc:  'Monte Carlo predictions for any league or knockout competition. 10,000 simulations ranked by championship probability.',
    tab:   'tournament',
    cta:   'Simulate Now',
  },
]

const COMPETITIONS = [
  'EPL', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1', 'Championship',
  'Champions League', 'Eredivisie', 'Euro 2024', 'Primeira Liga',
  'Süper Lig', 'Scottish Prem', 'Liga MX', 'MLS',
]

const doubled = [...TICKER_ITEMS, ...TICKER_ITEMS]

export default function Landing({ onNavigate }) {
  return (
    <div className="min-h-screen text-white" style={{ backgroundColor: '#0a0a0f' }}>

      {/* ── NAV ── */}
      <nav
        className="sticky top-0 z-50 border-b border-white/[0.06] backdrop-blur-md"
        style={{ backgroundColor: 'rgba(10,10,15,0.92)' }}
      >
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-base tracking-tight select-none">
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            <span className="text-white">FormCast</span>
          </div>
          <span className="text-[11px] font-mono text-gray-600 border border-gray-800 rounded px-2 py-1 hover:border-gray-700 hover:text-gray-500 transition-colors cursor-default">
            formcast-blush.vercel.app
          </span>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section
        className="relative overflow-hidden pt-24 pb-16 px-6"
        style={{
          backgroundImage: [
            'linear-gradient(rgba(16,185,129,0.025) 1px, transparent 1px)',
            'linear-gradient(90deg, rgba(16,185,129,0.025) 1px, transparent 1px)',
          ].join(','),
          backgroundSize: '48px 48px',
        }}
      >
        {/* ambient glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(16,185,129,0.08) 0%, transparent 65%)' }}
        />

        <div className="relative max-w-5xl mx-auto text-center animate-fade-up">
          {/* live badge */}
          <div className="inline-flex items-center gap-2 mb-8 px-3 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/[0.05] text-xs font-mono text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live · 7-model ensemble · Updated continuously
          </div>

          <h1
            className="font-black leading-[0.95] tracking-tight mb-6"
            style={{ fontSize: 'clamp(52px, 9vw, 92px)' }}
          >
            <span className="text-white block">Predict Football.</span>
            <span
              className="block bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, #10b981 0%, #818cf8 55%, #3b82f6 100%)' }}
            >
              Mathematically.
            </span>
          </h1>

          <p className="text-gray-400 text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
            7-model ensemble trained on{' '}
            <span className="text-white font-semibold">128,797 matches</span>{' '}
            across{' '}
            <span className="text-white font-semibold">14 competitions</span>.{' '}
            <span className="text-emerald-400 font-semibold">68.7%</span> walk-forward accuracy.{' '}
            Live now.
          </p>

          <div className="flex items-center justify-center gap-3 flex-wrap mb-16">
            <button
              onClick={() => onNavigate('live')}
              className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-sm bg-emerald-500 hover:bg-emerald-400 text-black transition-all duration-200 hover:shadow-[0_0_28px_rgba(16,185,129,0.45)] active:scale-95"
            >
              View Live Matches
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('backtest')}
              className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-sm border border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white transition-all duration-200 active:scale-95"
            >
              Explore Models
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* data ticker */}
          <div className="border border-gray-800/80 rounded-lg overflow-hidden">
            <div className="h-9 flex items-center" style={{ backgroundColor: 'rgba(0,0,0,0.35)' }}>
              <div className="flex-shrink-0 h-full flex items-center px-3 border-r border-gray-800/80 bg-emerald-500/[0.04]">
                <span className="text-[9px] font-mono font-bold text-emerald-500 tracking-[0.15em] uppercase">Data</span>
              </div>
              <div className="overflow-hidden flex-1">
                <div
                  className="flex whitespace-nowrap"
                  style={{ animation: 'ticker 38s linear infinite' }}
                >
                  {doubled.map((item, i) => (
                    <span key={i} className="text-[11px] font-mono flex-shrink-0">
                      <span className={i % 4 === 0 || i % 4 === 2 ? 'text-emerald-500' : 'text-gray-600'}>
                        {item}
                      </span>
                      <span className="text-gray-800 mx-5">·</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <section className="py-14 px-6">
        <div className="max-w-5xl mx-auto">
          <div
            className="grid grid-cols-2 md:grid-cols-4 gap-px rounded-xl overflow-hidden"
            style={{ backgroundColor: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.05)' }}
          >
            {STATS.map(({ value, label, emerald }) => (
              <div
                key={label}
                className="flex flex-col items-center justify-center text-center py-10 px-6"
                style={{ backgroundColor: '#0a0a0f' }}
              >
                <div
                  className="text-4xl md:text-5xl font-black font-mono mb-2 tabular-nums"
                  style={{
                    color: emerald ? '#10b981' : '#3b82f6',
                    textShadow: emerald
                      ? '0 0 40px rgba(16,185,129,0.55), 0 0 100px rgba(16,185,129,0.15)'
                      : '0 0 40px rgba(59,130,246,0.55), 0 0 100px rgba(59,130,246,0.15)',
                  }}
                >
                  {value}
                </div>
                <div className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.18em]">
                  {label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── MODEL STACK ── */}
      <section className="py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="text-[9px] font-mono text-gray-700 uppercase tracking-[0.2em] mb-3">
              Prediction Engine
            </div>
            <h2 className="text-3xl md:text-4xl font-black text-white mb-3">
              Seven Models.{' '}
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: 'linear-gradient(135deg, #10b981, #3b82f6)' }}
              >
                One Prediction.
              </span>
            </h2>
            <p className="text-gray-600 text-sm font-mono max-w-md mx-auto">
              Each model outputs a probability. The ensemble weights by historical calibration.
            </p>
          </div>

          <div className="grid grid-cols-6 gap-3">
            {MODELS.map(({ name, desc, metric, top }) => (
              <div
                key={name}
                className={`${top ? 'col-span-2' : 'col-span-3'} group rounded-lg p-5 transition-all duration-300 cursor-default`}
                style={{
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderTop: '1px solid rgba(16,185,129,0.14)',
                  backgroundColor: 'rgba(255,255,255,0.008)',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(16,185,129,0.22)'; e.currentTarget.style.backgroundColor = 'rgba(16,185,129,0.025)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.borderTopColor = 'rgba(16,185,129,0.14)'; e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.008)' }}
              >
                <div className="text-sm font-bold text-white mb-1.5 group-hover:text-emerald-400 transition-colors">
                  {name}
                </div>
                <div className="text-xs text-gray-600 leading-relaxed mb-3">{desc}</div>
                <div
                  className="inline-flex px-2 py-0.5 rounded text-[10px] font-mono text-emerald-600"
                  style={{ backgroundColor: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.1)' }}
                >
                  {metric}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHAT YOU GET ── */}
      <section className="py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="text-[9px] font-mono text-gray-700 uppercase tracking-[0.2em] mb-3">Tools</div>
            <h2 className="text-3xl md:text-4xl font-black text-white mb-3">What You Get</h2>
            <p className="text-gray-600 text-sm font-mono">Three tools built on the same engine.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {FEATURES.map(({ Icon, title, desc, tab, cta }) => (
              <button
                key={title}
                onClick={() => onNavigate(tab)}
                className="group text-left rounded-lg p-6 flex flex-col transition-all duration-300"
                style={{
                  border: '1px solid rgba(255,255,255,0.06)',
                  backgroundColor: 'rgba(255,255,255,0.008)',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(59,130,246,0.22)'; e.currentTarget.style.backgroundColor = 'rgba(59,130,246,0.025)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.008)' }}
              >
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center mb-4 transition-colors"
                  style={{ backgroundColor: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.15)' }}
                >
                  <Icon className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-sm font-bold text-white mb-2 group-hover:text-blue-400 transition-colors">
                  {title}
                </div>
                <div className="text-xs text-gray-600 leading-relaxed flex-1">{desc}</div>
                <div className="mt-4 flex items-center gap-1 text-[11px] font-semibold text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  {cta} <ArrowRight className="w-3 h-3" />
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── DATA ── */}
      <section className="py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto text-center">
          <div className="text-[9px] font-mono text-gray-700 uppercase tracking-[0.2em] mb-3">Training Data</div>
          <h2 className="text-3xl md:text-4xl font-black text-white mb-6">
            Built on{' '}
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, #10b981, #3b82f6)' }}
            >
              33 Years
            </span>
            {' '}of Data
          </h2>

          <div className="flex items-center justify-center gap-4 mb-10">
            <span
              className="text-2xl font-black font-mono tabular-nums"
              style={{ color: '#10b981', textShadow: '0 0 30px rgba(16,185,129,0.4)' }}
            >
              1993
            </span>
            <div className="flex-1 max-w-36 h-px" style={{ background: 'linear-gradient(90deg, rgba(16,185,129,0.5), rgba(59,130,246,0.5))' }} />
            <span className="text-2xl font-black font-mono tabular-nums text-white">2026</span>
          </div>

          <div className="flex flex-wrap justify-center gap-2">
            {COMPETITIONS.map((comp) => (
              <span
                key={comp}
                className="text-xs font-mono text-gray-500 rounded px-3 py-1.5 transition-colors cursor-default"
                style={{ border: '1px solid rgba(255,255,255,0.07)', backgroundColor: 'rgba(255,255,255,0.015)' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(16,185,129,0.25)'; e.currentTarget.style.color = '#10b981' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = '' }}
              >
                {comp}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-10 px-6 border-t border-gray-800/40">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-600">
            <BarChart2 className="w-4 h-4 text-emerald-500" />
            FormCast — Sports Prediction Platform
          </div>
          <div className="text-[11px] font-mono text-gray-700 text-center">
            Python · Flask · React · Supabase · Railway · Vercel
          </div>
          <a
            href="https://github.com"
            className="flex items-center gap-1.5 text-xs text-gray-700 hover:text-gray-400 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            GitHub
          </a>
        </div>
      </footer>

    </div>
  )
}
