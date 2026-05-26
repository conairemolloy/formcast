import { useState, useRef, useEffect } from 'react'
import { ChevronDown, LogOut, Settings, Bookmark } from 'lucide-react'
import api, { clearAuthToken } from '../api'

function initials(name, email) {
  if (name) {
    const parts = name.trim().split(/\s+/)
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].slice(0, 2).toUpperCase()
  }
  return email ? email[0].toUpperCase() : '?'
}

const TIER_BADGE = {
  free:  'text-gray-400 bg-gray-700/80 border border-gray-600',
  pro:   'text-blue-400 bg-blue-500/20 border border-blue-500/30',
  elite: 'text-amber-400 bg-amber-500/20 border border-amber-500/30',
}

export default function UserMenu({ user, onLogout, onNavigate }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  async function handleLogout() {
    setOpen(false)
    try { await api.post('/api/auth/logout') } catch (_) {}
    clearAuthToken()
    onLogout()
  }

  const badge = TIER_BADGE[user.tier] || TIER_BADGE.free

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 focus:outline-none"
        aria-label="User menu"
      >
        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-xs font-bold text-white select-none">
          {initials(user.name, user.email)}
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden py-1">
          {/* User info */}
          <div className="px-4 py-3 border-b border-gray-800">
            <p className="text-sm font-semibold text-white truncate">{user.name || 'User'}</p>
            <p className="text-xs text-gray-500 truncate mt-0.5">{user.email}</p>
            <span className={`inline-block mt-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${badge}`}>
              {user.tier || 'free'}
            </span>
          </div>

          <button
            onClick={() => { setOpen(false); onNavigate('watchlist') }}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <Bookmark className="w-4 h-4" />
            My Watchlist
          </button>

          <button
            onClick={() => { setOpen(false); onNavigate('settings') }}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>

          <div className="border-t border-gray-800 my-1" />

          <button
            onClick={handleLogout}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  )
}
