import { useState, useRef, useEffect } from 'react'
import { BarChart2, Menu, X, LayoutDashboard, ChevronDown, LogIn } from 'lucide-react'
import api from './api'
import { clearAuthToken } from './api'
import { setOddsFormat } from './oddsFormat'
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
import MatchResearch from './components/MatchResearch'
import InternationalRatings from './components/InternationalRatings'
import InternationalTeamProfile from './components/InternationalTeamProfile'
import WorldCupBracket from './components/WorldCupBracket'
import LandingNew from './components/LandingNew'
import About from './components/About'
import ProofPage from './components/ProofPage'
import './shell.css'

const NAV_GROUPS = [
  {
    label: 'Analysis',
    items: [
      { id: 'ratings',  label: 'Ratings' },
      { id: 'matches',  label: 'Matches' },
      { id: 'h2h',      label: 'H2H' },
      { id: 'research', label: 'Research' },
    ],
  },
  {
    label: 'International',
    items: [
      { id: 'international', label: 'Ratings' },
      { id: 'worldcup', label: '🏆 World Cup 2026' },
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

// Logged-out nav: the closed front door. Log in / Sign up free sit on the right.
const FRONT_DOOR_LINKS = [
  { id: 'about',        label: 'About' },
  { id: 'how-it-works', label: 'How it works' },
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
        data-active={isActive}
        className="fc-nav-item flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium transition-colors"
      >
        {group.label}
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="fc-panel absolute top-full left-0 mt-1.5 rounded-xl shadow-xl z-50 min-w-[168px] py-1.5 overflow-hidden">
          {group.items.map(item => (
            <button
              key={item.id}
              onClick={() => pick(item.id)}
              data-active={active === item.id}
              className="fc-nav-item fc-panel-item w-full text-left px-4 py-2.5 text-sm transition-colors"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Read synchronously on first render so the starting page is right from the
// very first paint: a returning user never sees the landing flash, and a
// logged-out visitor never sees the dashboard flash.
function hasStoredSession() {
  try {
    return Boolean(localStorage.getItem('auth_user') && localStorage.getItem('auth_token'))
  } catch {
    return false
  }
}

function App() {
  const [active, setActive]         = useState(() => hasStoredSession() ? 'dashboard' : 'landing-new')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [selectedNationalTeam, setSelectedNationalTeam] = useState(null)
  const [menuOpen, setMenuOpen]     = useState(false)
  const [user, setUser]             = useState(null)
  const [showAuth, setShowAuth]     = useState(false)
  const [authMode, setAuthMode]     = useState('login')
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
          .then(res => {
            const prof = res.data.profile
            if (prof.odds_format) setOddsFormat(prof.odds_format)
            setUser(u => ({ ...u, ...prof, access_token: token }))
          })
          .catch(() => {
            clearAuthToken()
            setUser(null)
            setActive('landing-new')
          })
      } catch (_) {
        clearAuthToken()
        setActive('landing-new')
      }
    }
    setSessionChecked(true)
  }, [])

  function handleNav(id) {
    setActive(id)
    setSelectedTeam(null)
    setSelectedNationalTeam(null)
    setMenuOpen(false)
  }

  function openAuth(mode = 'login') {
    setAuthMode(mode)
    setMenuOpen(false)
    setShowAuth(true)
  }

  function handleLogin(profile) {
    setUser(profile)
    handleNav('dashboard')
  }

  function handleLogout() {
    setUser(null)
    handleNav('landing-new')
  }

  const loggedIn  = sessionChecked && Boolean(user)
  const loggedOut = sessionChecked && !user

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
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] flex flex-col">
      <header className="fc-shell sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          {/* Logo */}
          <button
            onClick={() => handleNav(user ? 'dashboard' : 'landing-new')}
            className="fc-logo flex items-center gap-2 font-bold text-lg tracking-tight transition-colors shrink-0"
          >
            <BarChart2 className="fc-logo-mark w-5 h-5" />
            FormCast
          </button>

          {/* Desktop nav */}
          {/* Nothing renders until sessionChecked, so neither nav can flash. */}
          <nav className="hidden md:flex items-center gap-1">
            {loggedIn && (
              <>
                <button
                  onClick={() => handleNav('dashboard')}
                  data-active={active === 'dashboard'}
                  className="fc-nav-item flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors"
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
              </>
            )}

            {/* Closed front door: logged-out visitors get no product nav. */}
            {loggedOut && FRONT_DOOR_LINKS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => handleNav(id)}
                data-active={active === id}
                className="fc-nav-item px-3 py-1.5 rounded text-sm font-medium transition-colors"
              >
                {label}
              </button>
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
                <div className="hidden md:flex items-center gap-2">
                  <button
                    onClick={() => openAuth('login')}
                    className="fc-outline-btn flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
                  >
                    <LogIn className="w-4 h-4" />
                    Log in
                  </button>
                  <button
                    onClick={() => openAuth('signup')}
                    className="fc-primary-btn px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors"
                  >
                    Sign up free
                  </button>
                </div>
              )
            )}

            {/* Hamburger */}
            <button
              className="fc-icon-btn md:hidden p-2 transition-colors"
              onClick={() => setMenuOpen(o => !o)}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="fc-mobile-menu md:hidden px-2 py-2 space-y-0.5">
            {loggedIn && (
              <>
                <button
                  onClick={() => handleNav('dashboard')}
                  data-active={active === 'dashboard'}
                  className="fc-nav-item fc-panel-item w-full text-left flex items-center gap-2.5 px-4 py-2.5 rounded text-sm font-medium transition-colors"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </button>

                {NAV_GROUPS.map(group => (
                  <div key={group.label}>
                    <p className="fc-group-label px-4 pt-3 pb-1 text-[9px] font-mono uppercase tracking-[0.18em] select-none">
                      {group.label}
                    </p>
                    {group.items.map(({ id, label }) => (
                      <button
                        key={id}
                        onClick={() => handleNav(id)}
                        data-active={active === id}
                        className="fc-nav-item fc-panel-item w-full text-left flex items-center px-6 py-2.5 rounded text-sm font-medium transition-colors"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                ))}

                <div className="fc-divider mt-2 pt-2">
                  <button
                    onClick={() => handleNav('watchlist')}
                    className="fc-nav-item fc-panel-item w-full text-left px-4 py-2.5 text-sm rounded transition-colors"
                  >
                    My Watchlist
                  </button>
                  <button
                    onClick={() => handleNav('settings')}
                    className="fc-nav-item fc-panel-item w-full text-left px-4 py-2.5 text-sm rounded transition-colors"
                  >
                    Settings
                  </button>
                </div>
              </>
            )}

            {loggedOut && (
              <>
                {FRONT_DOOR_LINKS.map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => handleNav(id)}
                    data-active={active === id}
                    className="fc-nav-item fc-panel-item w-full text-left px-4 py-2.5 rounded text-sm font-medium transition-colors"
                  >
                    {label}
                  </button>
                ))}
                <div className="fc-divider mt-2 pt-2 space-y-1">
                  <button
                    onClick={() => openAuth('login')}
                    className="fc-mobile-signin w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors"
                  >
                    <LogIn className="w-4 h-4" />
                    Log in
                  </button>
                  <button
                    onClick={() => openAuth('signup')}
                    className="fc-primary-btn w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg transition-colors"
                  >
                    Sign up free
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </header>

      {/* The remodelled landing is full-bleed — skip the padded, max-width frame. */}
      <main className={active === 'landing-new' ? 'flex-1 w-full' : 'flex-1 max-w-7xl mx-auto w-full px-4 py-6'}>
        {active === 'landing-new'    && <LandingNew onNavigate={handleNav} onShowAuth={() => openAuth('signup')} />}
        {active === 'about'          && <About />}
        {active === 'proof'          && <ProofPage />}
        {active === 'dashboard'      && <Dashboard onNavigate={handleNav} />}
        {active === 'ratings'        && !selectedTeam && (
          <RatingsTable
            onTeamClick={setSelectedTeam}
            user={user}
            onWatchlistUpdate={handleWatchlistUpdate}
            onShowAuth={() => openAuth('login')}
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
            onShowAuth={() => openAuth('login')}
          />
        )}
        {active === 'matches'        && <Matches />}
        {active === 'live'           && <Live />}
        {active === 'predictions'    && <Predictions />}
        {active === 'backtest'       && <BacktestReport />}
        {active === 'how-it-works'   && <HowItWorks />}
        {active === 'prediction-log' && <PredictionLog />}
        {active === 'h2h'            && <H2H />}
        {active === 'research'       && <MatchResearch />}
        {active === 'international'  && !selectedNationalTeam && (
          <InternationalRatings onTeamClick={setSelectedNationalTeam} />
        )}
        {active === 'international'  && selectedNationalTeam && (
          <InternationalTeamProfile
            team={selectedNationalTeam.name}
            eloRating={selectedNationalTeam.elo}
            confederation={selectedNationalTeam.confederation}
            eloRank={selectedNationalTeam.rank}
            onBack={() => setSelectedNationalTeam(null)}
          />
        )}
        {active === 'worldcup' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-white">🏆 2026 FIFA World Cup</h1>
              <p className="text-gray-400 text-sm mt-1">Elo-based knockout bracket intelligence — 100,000 Monte Carlo simulations</p>
            </div>
            <WorldCupBracket onTeamClick={(name) => { setSelectedNationalTeam({ name, elo: null, confederation: null, rank: null }); setActive('international'); }} />
          </div>
        )}
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
          initialMode={authMode}
          onClose={() => setShowAuth(false)}
          onLogin={handleLogin}
        />
      )}
    </div>
  )
}

export default App
