import { useState } from 'react'
import { BarChart2 } from 'lucide-react'
import RatingsTable from './components/RatingsTable'
import BacktestReport from './components/BacktestReport'
import ValueBets from './components/ValueBets'
import Predictions from './components/Predictions'
import Accumulators from './components/Accumulators'

const NAV_ITEMS = [
  { id: 'ratings',      label: 'Ratings' },
  { id: 'predictions',  label: 'Predictions' },
  { id: 'backtest',     label: 'Backtest' },
  { id: 'value-bets',   label: 'Value Bets' },
  { id: 'accumulators', label: 'Accumulators' },
]

function App() {
  const [active, setActive] = useState('ratings')

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-8">
          <button
            onClick={() => setActive('ratings')}
            className="flex items-center gap-2 text-white font-bold text-lg tracking-tight hover:text-emerald-400 transition-colors"
          >
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            FormCast
          </button>

          <nav className="flex items-center gap-1 ml-4">
            {NAV_ITEMS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActive(id)}
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
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {active === 'ratings'      && <RatingsTable />}
        {active === 'predictions'  && <Predictions />}
        {active === 'backtest'     && <BacktestReport />}
        {active === 'value-bets'   && <ValueBets />}
        {active === 'accumulators' && <Accumulators />}
      </main>
    </div>
  )
}

export default App
