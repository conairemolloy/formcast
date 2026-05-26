import { useState, useRef, useEffect } from 'react'
import { BarChart2, Menu, X, LayoutDashboard, ChevronDown, LogIn } from 'lucide-react'
import api from './api'
import { clearAuthToken } from './api'
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
import PredictionLog from './components/PredictionLog'
import Auth from './components/Auth'
import UserMenu from './components/UserMenu'
import WatchlistPage from './components/WatchlistPage'
import SettingsPage from './components/SettingsPage'

const NAV_GROUPS = [
  {
    label: 'Analysis',
    items: [
      { id: 'ratings', label: 'Ratings' },
      { id: 'matches', label: 'Matches' },
      { id: 'h2h',     label: 'H2H' },
    ],
  },
  {
    label: 'Predictions',
    items: [
      { id: 'live',        label: 'Live' },
      { id: 'predictions', label: 'Predictions' },
      { id: 'tournament',  label: 'Tournament' },
    ],
  },
  {
    label: 'Betting',
    items: [
      { id: 'value-bets',   label: 'Value Bets' },
      { id: 'accumulators', label: 'Accumulators' },
      { id: 'backtest',     label: 'Backtest' },
    ],
  },
  {
    label: 'Learn',
    items: [
      { id: 'how-it-works',   label: 'How It Works' },
      { id: 'prediction-log', label: 'Prediction Log' },
    ],
  },
]

function NavDropdown({ group, active, onNav }) {
  const [open, setOpen] = useState(false)
  const closeTimer      = useRef(null)
  const isActive        = group.items.some(item => item.id === active)

  useEffect(() => () => clearTimeout(closeTimer.current), [])

  function enter() {
    clearTimeout(closeTimer.current)
    setOpen(true)
  }

  function leave() {
    closeTimer.current = setTimeout(() => setOpen(false), 120)
  }

  function pick(id) {
    setOpen(false)
    onNav(id)
  }

  return (
    <div className="relative" onMouseEnter={enter} onMouseLeave={leave}>
      <button
        className={`flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
          isActive
            ? 'text-emerald-400'
            : 'text-gray-400 hover:text-white'
        }`}
      >
        {group.label}
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 bg-gray-900 border border-gray-800 rounded-xl shadow-xl z-50 min-w-[168px] py-1.5 overflow-hidden">
          {group.items.map(item => (
            <button
              key={item.id}
              onClick={() => pick(item.id)}
              className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                active === item.id
                  ? 'text-emerald-400 bg-emerald-500/10'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function App() {
  const [active, setActive]         = useState('dashboard')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [menuOpen, setMenuOpen]     = useState(false)
  const [user, setUser]             = useState(null)
  const [showAuth, setShowAuth]     = useState(false)
  const [sessionChecked, setSessionChecked] = useState(false)

  // Restore session from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('auth_user')
    const token  = localStorage.getItem('auth_token')
    if (stored && token) {
      try {
        const cached = JSON.parse(stored)
        setUser(cached)
        // Verify token is still valid in background
        api.get('/api/auth/profile')
          .then(res => setUser(u => ({ ...u, ...res.data.profile, access_token: token })))
          .catch(() => {
            clearAuthToken()
            setUser(null)
          })
      } catch (_) {
        clearAuthToken()
      }
    }
    setSessionChecked(true)
  }, [])

  function handleNav(id) {
    setActive(id)
    setSelectedTeam(null)
    setMenuOpen(false)
  }

  function handleLogin(profile) {
    setUser(profile)
  }

  function handleLogout() {
    setUser(null)
    if (['watchlist', 'settings'].includes(active)) {
      setActive('dashboard')
    }
  }

  function handleWatchlistUpdate(newWatchlist) {
    setUser(u => {
      if (!u) return u
      const updated = { ...u, watchlist: newWatchlist }
      localStorage.setItem('auth_user', JSON.stringify(updated))
      return updated
    })
  }

  function handleUserUpdate(profile) {
    setUser(u => {
      if (!u) return u
      const updated = { ...u, ...profile }
      localStorage.setItem('auth_user', JSON.stringify(updated))
      return updated
    })
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          {/* Logo */}
          <button
            onClick={() => handleNav('dashboard')}
            className="flex items-center gap-2 text-white font-bold text-lg tracking-tight hover:text-emerald-400 transition-colors shrink-0"
          >
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            FormCast
          </button>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => handleNav('dashboard')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                active === 'dashboard'
                  ? 'text-emerald-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              Dashboard
            </button>

            {NAV_GROUPS.map(group => (
              <NavDropdown
                key={group.label}
                group={group}
                active={active}
                onNav={handleNav}
              />
            ))}
          </nav>

          {/* Right side: auth */}
          <div className="flex items-center gap-3 shrink-0">
            {sessionChecked && (
              user ? (
                <UserMenu
                  user={user}
                  onLogout={handleLogout}
                  onNavigate={handleNav}
                />
              ) : (
                <button
                  onClick={() => setShowAuth(true)}
                  className="hidden md:flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-400 hover:text-white border border-gray-700 hover:border-gray-600 rounded-lg transition-colors"
                >
                  <LogIn className="w-4 h-4" />
                  Sign In
                </button>
              )
            )}

            {/* Hamburger */}
            <button
              className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
              onClick={() => setMenuOpen(o => !o)}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-900 px-2 py-2 space-y-0.5">
            <button
              onClick={() => handleNav('dashboard')}
              className={`w-full text-left flex items-center gap-2.5 px-4 py-2.5 rounded text-sm font-medium transition-colors ${
                active === 'dashboard'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </button>

            {NAV_GROUPS.map(group => (
              <div key={group.label}>
                <p className="px-4 pt-3 pb-1 text-[9px] font-mono text-gray-600 uppercase tracking-[0.18em] select-none">
                  {group.label}
                </p>
                {group.items.map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => handleNav(id)}
                    className={`w-full text-left flex items-center px-6 py-2.5 rounded text-sm font-medium transition-colors ${
                      active === id
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-gray-400 hover:text-white hover:bg-gray-800'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            ))}

            {/* Mobile auth */}
            <div className="border-t border-gray-800 mt-2 pt-2">
              {user ? (
                <>
                  <button
                    onClick={() => handleNav('watchlist')}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
                  >
                    My Watchlist
                  </button>
                  <button
                    onClick={() => handleNav('settings')}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
                  >
                    Settings
                  </button>
                </>
              ) : (
                <button
                  onClick={() => { setMenuOpen(false); setShowAuth(true) }}
                  className="w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm text-emerald-400 font-medium"
                >
                  <LogIn className="w-4 h-4" />
                  Sign In
                </button>
              )}
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {active === 'landing'        && <Landing onNavigate={handleNav} />}
        {active === 'dashboard'      && <Dashboard onNavigate={handleNav} />}
        {active === 'ratings'        && !selectedTeam && (
          <RatingsTable
            onTeamClick={setSelectedTeam}
            user={user}
            onWatchlistUpdate={handleWatchlistUpdate}
            onShowAuth={() => setShowAuth(true)}
          />
        )}
        {active === 'ratings'        && selectedTeam && (
          <TeamProfile
            team={selectedTeam.name}
            eloRating={selectedTeam.elo}
            league={selectedTeam.league}
            eloRank={selectedTeam.rank}
            onBack={() => setSelectedTeam(null)}
            user={user}
            onWatchlistUpdate={handleWatchlistUpdate}
            onShowAuth={() => setShowAuth(true)}
          />
        )}
        {active === 'matches'        && <Matches />}
        {active === 'live'           && <Live />}
        {active === 'predictions'    && <Predictions />}
        {active === 'backtest'       && <BacktestReport />}
        {active === 'how-it-works'   && <HowItWorks />}
        {active === 'prediction-log' && <PredictionLog />}
        {active === 'h2h'            && <H2H />}
        {active === 'tournament'     && <Tournament />}
        {active === 'value-bets'     && <ValueBets />}
        {active === 'accumulators'   && <Accumulators />}
        {active === 'watchlist'      && user && (
          <WatchlistPage
            user={user}
            onWatchlistUpdate={handleWatchlistUpdate}
          />
        )}
        {active === 'settings'       && user && (
          <SettingsPage
            user={user}
            onUserUpdate={handleUserUpdate}
          />
        )}
      </main>

      {/* Auth modal */}
      {showAuth && (
        <Auth
          onClose={() => setShowAuth(false)}
          onLogin={handleLogin}
        />
      )}
    </div>
  )
}

export default App
