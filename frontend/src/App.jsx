import { useState } from 'react'
import { BarChart2, Menu, X } from 'lucide-react'
import Landing from './components/Landing'
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

const NAV_ITEMS = [
  { id: 'ratings',      label: 'Ratings' },
  { id: 'matches',      label: 'Matches' },
  { id: 'live',         label: 'Live' },
  { id: 'predictions',  label: 'Predictions' },
  { id: 'backtest',     label: 'Backtest' },
  { id: 'how-it-works', label: 'How It Works' },
  { id: 'h2h',          label: 'H2H' },
  { id: 'tournament',   label: 'Tournament' },
  { id: 'value-bets',   label: 'Value Bets' },
  { id: 'accumulators', label: 'Accumulators' },
]

function App() {
  const [active, setActive]           = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [menuOpen, setMenuOpen]       = useState(false)

  function handleNav(id) {
    setActive(id)
    setSelectedTeam(null)
    setMenuOpen(false)
  }

  if (active === null) {
    return <Landing onNavigate={handleNav} />
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          <button
            onClick={() => handleNav(null)}
            className="flex items-center gap-2 text-white font-bold text-lg tracking-tight hover:text-emerald-400 transition-colors shrink-0"
          >
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            FormCast
          </button>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => handleNav(id)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  active === id
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {label}
              </button>
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

        {/* Mobile dropdown */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-900 px-2 py-2 flex flex-col gap-0.5">
            {NAV_ITEMS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => handleNav(id)}
                className={`w-full text-left px-4 py-2.5 rounded text-sm font-medium transition-colors ${
                  active === id
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {active === 'ratings' && !selectedTeam && (
          <RatingsTable onTeamClick={setSelectedTeam} />
        )}
        {active === 'ratings' && selectedTeam && (
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
