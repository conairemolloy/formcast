import { BarChart2, Zap, TrendingUp, ArrowRight, CheckCircle2 } from 'lucide-react'

const USE_CASES = [
  {
    Icon: Zap,
    color: 'emerald',
    title: 'Find Value Bets',
    desc: 'Every week the model scans upcoming fixtures across 6 leagues and identifies matches where our probability beats the bookmaker\'s implied odds by 5% or more.',
    cta: 'View Value Bets →',
    tab: 'value-bets',
    iconBg:   'bg-emerald-500/10 border-emerald-500/20',
    iconText: 'text-emerald-400',
    btnHover: 'hover:text-emerald-400',
  },
  {
    Icon: BarChart2,
    color: 'blue',
    title: 'Analyse Any Match',
    desc: 'Click any upcoming fixture to get a full breakdown — win probabilities, correct scores, BTTS, goals markets, corners, cards, H2H record and current form.',
    cta: 'View Live Fixtures →',
    tab: 'live',
    iconBg:   'bg-blue-500/10 border-blue-500/20',
    iconText: 'text-blue-400',
    btnHover: 'hover:text-blue-400',
  },
  {
    Icon: TrendingUp,
    color: 'purple',
    title: 'Track Team Form',
    desc: 'Browse Elo ratings for 500+ teams across 14 competitions. Click any team for their full rating history, season stats and head-to-head record.',
    cta: 'View Ratings →',
    tab: 'ratings',
    iconBg:   'bg-purple-500/10 border-purple-500/20',
    iconText: 'text-purple-400',
    btnHover: 'hover:text-purple-400',
  },
]

const STATS = [
  { value: '68.7%',    label: 'Hit Rate',       color: '#10b981' },
  { value: '0.156',    label: 'Brier Score',     color: '#3b82f6' },
  { value: '+19%',     label: 'Mean CLV',        color: '#10b981' },
  { value: '128,797',  label: 'Matches',         color: '#3b82f6' },
]

const STEPS = [
  {
    n: '1',
    title: '7 Models',
    desc: 'Elo, Glicko-2, Dixon-Coles, BTL, XGBoost, Neural Network, LSTM each generate probabilities independently.',
  },
  {
    n: '2',
    title: 'Ensemble',
    desc: 'A meta-learner combines all 7 outputs, weighted by historical accuracy per league and situation.',
  },
  {
    n: '3',
    title: 'Edge Detection',
    desc: 'Model probabilities are compared against live bookmaker odds to identify underpriced outcomes.',
  },
]

export default function Landing({ onNavigate }) {
  return (
    <div className="min-h-screen text-white" style={{ backgroundColor: '#0a0a0f' }}>

      {/* ── NAV ── */}
      <nav
        className="sticky top-0 z-50 border-b border-white/[0.06] backdrop-blur-md"
        style={{ backgroundColor: 'rgba(10,10,15,0.92)' }}
      >
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-base tracking-tight select-none">
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            <span className="text-white">FormCast</span>
          </div>
          <button
            onClick={() => onNavigate('dashboard')}
            className="text-xs text-gray-400 hover:text-white transition-colors flex items-center gap-1.5"
          >
            Dashboard <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section
        className="relative overflow-hidden pt-20 sm:pt-28 pb-16 sm:pb-20 px-6"
        style={{
          backgroundImage: [
            'linear-gradient(rgba(16,185,129,0.025) 1px, transparent 1px)',
            'linear-gradient(90deg, rgba(16,185,129,0.025) 1px, transparent 1px)',
          ].join(','),
          backgroundSize: '48px 48px',
        }}
      >
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(16,185,129,0.08) 0%, transparent 65%)' }}
        />

        <div className="relative max-w-3xl mx-auto text-center">
          <h1
            className="font-black leading-tight tracking-tight mb-5"
            style={{ fontSize: 'clamp(36px, 7vw, 80px)' }}
          >
            <span className="text-white">Predict. Analyse.</span>
            <br />
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, #10b981 0%, #818cf8 55%, #3b82f6 100%)' }}
            >
              Find Edge.
            </span>
          </h1>

          <p className="text-gray-400 text-base sm:text-lg max-w-xl mx-auto mb-8 leading-relaxed">
            AI-powered match intelligence across{' '}
            <span className="text-white font-semibold">14 competitions</span>.{' '}
            <span className="text-white font-semibold">128,797</span> matches trained.{' '}
            <span className="text-emerald-400 font-semibold">68.7%</span> prediction accuracy.
          </p>

          <div className="flex items-center justify-center gap-3 flex-wrap mb-6">
            <button
              onClick={() => onNavigate('value-bets')}
              className="px-6 py-3 rounded-lg font-semibold text-sm bg-emerald-500 hover:bg-emerald-400 text-black transition-all duration-200 hover:shadow-[0_0_28px_rgba(16,185,129,0.45)] active:scale-95"
            >
              View Today's Value Bets
            </button>
            <button
              onClick={() => onNavigate('live')}
              className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-sm border border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white transition-all duration-200 active:scale-95"
            >
              Explore Live Fixtures
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <p className="text-xs text-gray-600 font-mono">
            68.7% hit rate · Mean CLV +19% · 128,797 matches
          </p>
        </div>
      </section>

      {/* ── USE CASES ── */}
      <section className="py-16 sm:py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.2em] mb-2">
              Getting Started
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              How to use FormCast
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {USE_CASES.map(({ Icon, title, desc, cta, tab, iconBg, iconText, btnHover }) => (
              <div
                key={title}
                className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col gap-4 hover:border-gray-700 transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 ${iconBg}`}>
                  <Icon className={`w-5 h-5 ${iconText}`} />
                </div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-white mb-2">{title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
                </div>
                <button
                  onClick={() => onNavigate(tab)}
                  className={`text-sm font-medium text-gray-400 text-left transition-colors ${btnHover}`}
                >
                  {cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <section className="py-10 sm:py-14 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div
            className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 rounded-xl overflow-hidden"
            style={{ border: '1px solid rgba(255,255,255,0.06)', backgroundColor: 'rgba(255,255,255,0.02)', divideColor: 'rgba(255,255,255,0.06)' }}
          >
            {STATS.map(({ value, label, color }) => (
              <div
                key={label}
                className="flex flex-col items-center justify-center py-8 px-4 text-center"
                style={{ borderColor: 'rgba(255,255,255,0.06)' }}
              >
                <p
                  className="text-3xl sm:text-4xl font-black font-mono tabular-nums mb-1"
                  style={{ color, textShadow: `0 0 30px ${color}55` }}
                >
                  {value}
                </p>
                <p className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.15em]">
                  {label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-16 sm:py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.2em] mb-2">
              Under the Hood
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              How the model works
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 relative">
            {/* connector line (desktop only) */}
            <div
              className="hidden md:block absolute top-7 left-[calc(16.67%+0.5rem)] right-[calc(16.67%+0.5rem)] h-px"
              style={{ background: 'linear-gradient(90deg, rgba(16,185,129,0.3), rgba(59,130,246,0.3))' }}
            />

            {STEPS.map(({ n, title, desc }) => (
              <div key={n} className="relative flex flex-col items-center text-center px-6 pb-8 md:pb-0">
                {/* number circle */}
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-black mb-5 relative z-10"
                  style={{
                    background: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(59,130,246,0.15))',
                    border: '1px solid rgba(16,185,129,0.25)',
                    color: '#10b981',
                  }}
                >
                  {n}
                </div>
                <h3 className="text-base font-bold text-white mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed max-w-xs">{desc}</p>

                {/* mobile connector */}
                {n !== '3' && (
                  <div
                    className="md:hidden w-px h-8 mt-4"
                    style={{ background: 'linear-gradient(to bottom, rgba(16,185,129,0.3), rgba(59,130,246,0.3))' }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER CTA ── */}
      <section className="py-16 sm:py-20 px-6 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-6">
            Ready to find your edge?
          </h2>
          <button
            onClick={() => onNavigate('dashboard')}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg font-semibold text-sm bg-emerald-500 hover:bg-emerald-400 text-black transition-all duration-200 hover:shadow-[0_0_28px_rgba(16,185,129,0.45)] active:scale-95"
          >
            Go to Dashboard
            <ArrowRight className="w-4 h-4" />
          </button>

          <div className="mt-12 flex items-center justify-center gap-4 text-xs text-gray-700 font-mono flex-wrap">
            <span>Python · Flask · React</span>
            <span className="text-gray-800">·</span>
            <span>7-model ensemble</span>
            <span className="text-gray-800">·</span>
            <span>33 years of data</span>
          </div>
        </div>
      </section>

    </div>
  )
}
