import { useState } from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import api from '../api'
import { getOddsFormat, setOddsFormat } from '../oddsFormat'

export default function SettingsPage({ user, onUserUpdate }) {
  const [name, setName]             = useState(user?.name || '')
  const [emailAlerts, setEmailAlerts] = useState(user?.email_alerts ?? true)
  const [oddsFormat, setOddsFormatState] = useState(() =>
    user?.odds_format ?? getOddsFormat()
  )
  const [saving, setSaving]         = useState(false)
  const [saved, setSaved]           = useState(false)
  const [error, setError]           = useState(null)

  function handleFormatChange(fmt) {
    setOddsFormat(fmt)
    setOddsFormatState(fmt)
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const res = await api.put('/api/auth/profile', { name, email_alerts: emailAlerts, odds_format: oddsFormat })
      onUserUpdate(res.data.profile)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors'

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <h1 className="text-xl font-semibold text-white">Settings</h1>

      <form onSubmit={handleSave} className="space-y-5">
        {/* Account */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-300">Account</h2>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Your name"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Email</label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full bg-gray-800/40 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-500 cursor-not-allowed"
            />
            <p className="text-xs text-gray-600 mt-1">Email cannot be changed here</p>
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Notifications</h2>

          <label className="flex items-center justify-between cursor-pointer gap-4">
            <div>
              <p className="text-sm text-white font-medium">Email alerts</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Get notified about teams in your watchlist
              </p>
            </div>
            <button
              type="button"
              onClick={() => setEmailAlerts(v => !v)}
              className={`relative shrink-0 w-11 h-6 rounded-full transition-colors duration-200 ${
                emailAlerts ? 'bg-emerald-600' : 'bg-gray-700'
              }`}
              role="switch"
              aria-checked={emailAlerts}
            >
              <div
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                  emailAlerts ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </label>
        </div>

        {/* Display */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Display</h2>

          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-white font-medium">Odds format</p>
              <p className="text-xs text-gray-500 mt-0.5">How odds are displayed across the site</p>
            </div>
            <div className="flex gap-1 shrink-0">
              {[
                ['decimal',    'Decimal',    '2.50'],
                ['fractional', 'Fractional', '6/4'],
                ['american',   'American',   '+150'],
              ].map(([val, label, ex]) => (
                <button
                  key={val}
                  type="button"
                  title={ex}
                  onClick={() => handleFormatChange(val)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    oddsFormat === val
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-gray-800 text-gray-400 border border-gray-700 hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5">
            {error}
          </p>
        )}
        {saved && (
          <p className="text-emerald-400 text-sm bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2.5">
            Settings saved successfully
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Changes
        </button>
      </form>

      {/* Danger zone */}
      <div className="bg-gray-900 border border-red-900/30 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-red-400 flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4" />
          Danger Zone
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Permanently delete your account and all associated data.
        </p>
        <button
          type="button"
          disabled
          className="px-4 py-2 text-sm text-red-400 border border-red-900/50 rounded-lg opacity-40 cursor-not-allowed"
          title="Coming soon"
        >
          Delete Account
        </button>
      </div>
    </div>
  )
}
