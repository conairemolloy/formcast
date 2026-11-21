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
  free:  'text-[var(--muted-foreground)] bg-[var(--muted)] border border-[var(--border)]',
  pro:   'text-[var(--primary)] bg-[var(--primary)]/12 border border-[var(--primary)]/30',
  elite: 'text-[var(--chart-3)] bg-[var(--chart-3)]/15 border border-[var(--chart-3)]/30',
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
        <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-xs font-bold text-[var(--primary-foreground)] select-none">
          {initials(user.name, user.email)}
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-[var(--muted-foreground)] transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 fc-card shadow-2xl z-50 overflow-hidden py-1">
          {/* User info */}
          <div className="px-4 py-3 border-b border-[var(--border)]">
            <p className="text-sm font-semibold text-[var(--foreground)] truncate">{user.name || 'User'}</p>
            <p className="text-xs text-[var(--muted-foreground)] truncate mt-0.5">{user.email}</p>
            <span className={`inline-block mt-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${badge}`}>
              {user.tier || 'free'}
            </span>
          </div>

          <button
            onClick={() => { setOpen(false); onNavigate('watchlist') }}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <Bookmark className="w-4 h-4" />
            My Watchlist
          </button>

          <button
            onClick={() => { setOpen(false); onNavigate('settings') }}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>

          <div className="border-t border-[var(--border)] my-1" />

          <button
            onClick={handleLogout}
            className="w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm text-[var(--chart-5)] hover:text-[var(--chart-5)] hover:bg-[var(--chart-5)]/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  )
}
