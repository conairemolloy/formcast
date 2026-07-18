import { useState } from 'react'

// Mirror of COMMON_FRACTIONS in scripts/dutching_arbitrage.py — same 40 entries, same order.
// JS and Python nearest-fraction logic are identical so both always return the same fraction.
const COMMON_FRACTIONS = [
  [1, 4], [1, 3], [4, 9], [1, 2], [8, 15], [4, 6], [8, 11], [4, 5], [5, 6],
  [10, 11], [1, 1], [11, 10], [6, 5], [5, 4], [11, 8], [6, 4], [13, 8], [7, 4],
  [15, 8], [2, 1], [9, 4], [5, 2], [11, 4], [3, 1], [10, 3], [4, 1], [9, 2],
  [5, 1], [6, 1], [7, 1], [8, 1], [10, 1], [12, 1], [16, 1], [20, 1], [25, 1],
  [33, 1], [50, 1], [66, 1], [100, 1],
]

// target = decimal - 1 is equivalent to (1 - implied_prob) / implied_prob
export function decimalToFractional(decimal) {
  if (!decimal || decimal <= 1) return '—'
  const target = decimal - 1
  const best = COMMON_FRACTIONS.reduce((b, f) =>
    Math.abs(f[0] / f[1] - target) < Math.abs(b[0] / b[1] - target) ? f : b
  )
  return `${best[0]}/${best[1]}`
}

export function decimalToAmerican(decimal) {
  if (!decimal || decimal <= 1) return '—'
  if (decimal >= 2.0) return `+${Math.round((decimal - 1) * 100)}`
  return `-${Math.round(100 / (decimal - 1))}`
}

export function impliedProbability(decimal) {
  if (!decimal || decimal <= 0) return null
  return 1 / decimal
}

export function formatOdds(decimal, format) {
  if (!decimal || decimal <= 1) return '—'
  if (format === 'fractional') return decimalToFractional(decimal)
  if (format === 'american')   return decimalToAmerican(decimal)
  return Number(decimal).toFixed(2)
}

const LS_KEY = 'odds_format'
const VALID  = ['decimal', 'fractional', 'american']

export function getOddsFormat() {
  const v = localStorage.getItem(LS_KEY)
  return VALID.includes(v) ? v : 'decimal'
}

export function setOddsFormat(fmt) {
  if (VALID.includes(fmt)) localStorage.setItem(LS_KEY, fmt)
}

export function useOddsFormat() {
  const [format, setFormat] = useState(() => getOddsFormat())
  function update(fmt) {
    setOddsFormat(fmt)
    setFormat(fmt)
  }
  return [format, update]
}
