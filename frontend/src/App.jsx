import { useState, Fragment } from 'react'
import { BarChart2, Menu, X, LayoutDashboard } from 'lucide-react'
import Landing from './components/Landing'
import Dashboard from './components/Dashboard'
import RatingsTable from './components/RatingsTable'
import TeamProfile from './components/TeamProfile'
import BacktestReport from './components/BacktestReport'
import ValueBets from './components/ValueBets'
import Predictions from './components/Predictions'
import Accumulators from './components/Accumulators'
import Tournament from './components/Tournament'
import Matches from './components/Matches'
import Live from './components/Live'
import HowItWorks from './components/HowItWorks'
import H2H from './components/H2H'

const NAV_GROUPS = [
  {
    label: null,
    items: [{ id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'ANALYSIS',
    items: [
      { id: 'ratings', label: 'Ratings' },
      { id: 'matches', label: 'Matches' },
      { id: 'h2h',     label: 'H2H' },
    ],
  },
  {
    label: 'PREDICTIONS',
    items: [
      { id: 'live',        label: 'Live' },
      { id: 'predictions', label: 'Predictions' },
      { id: 'tournament',  label: 'Tournament' },
    ],
  },
  {
    label: 'BETTING',
    items: [
      { id: 'value-bets',   label: 'Value Bets' },
      { id: 'accumulators', label: 'Accumulators' },
      { id: 'backtest',     label: 'Backtest' },
    ],
  },
  {
    label: 'LEARN',
    items: [{ id: 'how-it-works', label: 'How It Works' }],
  },
]

function App() {
  const [active, setActive]             = useState('dashboard')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [menuOpen, setMenuOpen]         = useState(false)

  function handleNav(id) {
    setActive(id)
    setSelectedTeam(null)
    setMenuOpen(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          <button
            onClick={() => handleNav('dashboard')}
            className="flex items-center gap-2 text-white font-bold text-lg tracking-tight hover:text-emerald-400 transition-colors shrink-0"
          >
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            FormCast
          </button>

          {/* Desktop nav — grouped */}
          <nav className="hidden md:flex items-center gap-0.5 overflow-x-auto">
            {NAV_GROUPS.map((group, gi) => (
              <Fragment key={gi}>
                {gi > 0 && (
                  <span className="mx-1.5 shrink-0 text-[9px] font-mono text-gray-700 uppercase tracking-[0.15em] select-none">
                    {group.label}
                  </span>
                )}
                {group.items.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => handleNav(id)}
                    className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                      active === id
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-gray-400 hover:text-white hover:bg-gray-800'
                    }`}
                  >
                    {Icon && <Icon className="w-3.5 h-3.5" />}
                    {label}
                  </button>
                ))}
              </Fragment>
            ))}
          </nav>

          {/* Hamburger */}
          <button
            className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile dropdown — grouped */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-900 px-2 py-2 space-y-0.5">
            {NAV_GROUPS.map((group, gi) => (
              <div key={gi}>
                {group.label && (
                  <p className="px-4 pt-2.5 pb-1 text-[9px] font-mono text-gray-600 uppercase tracking-[0.18em] select-none">
                    {group.label}
                  </p>
                )}
                {group.items.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => handleNav(id)}
                    className={`w-full text-left flex items-center gap-2.5 px-4 py-2.5 rounded text-sm font-medium transition-colors ${
                      active === id
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-gray-400 hover:text-white hover:bg-gray-800'
                    }`}
                  >
                    {Icon && <Icon className="w-4 h-4" />}
                    {label}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {active === 'landing'      && <Landing onNavigate={handleNav} />}
        {active === 'dashboard'    && <Dashboard onNavigate={handleNav} />}
        {active === 'ratings'      && !selectedTeam && <RatingsTable onTeamClick={setSelectedTeam} />}
        {active === 'ratings'      && selectedTeam && (
          <TeamProfile
            team={selectedTeam.name}
            eloRating={selectedTeam.elo}
            league={selectedTeam.league}
            eloRank={selectedTeam.rank}
            onBack={() => setSelectedTeam(null)}
          />
        )}
        {active === 'matches'      && <Matches />}
        {active === 'live'         && <Live />}
        {active === 'predictions'  && <Predictions />}
        {active === 'backtest'     && <BacktestReport />}
        {active === 'how-it-works' && <HowItWorks />}
        {active === 'h2h'          && <H2H />}
        {active === 'tournament'   && <Tournament />}
        {active === 'value-bets'   && <ValueBets />}
        {active === 'accumulators' && <Accumulators />}
      </main>
    </div>
  )
}

export default App
