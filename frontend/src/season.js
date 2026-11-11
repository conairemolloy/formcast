// Mirrors scripts/season_utils.py current_season(): July rollover rule
// (the 2026-27 data starts 2026-07-31). Keep the two in sync.
export function currentSeason(d = new Date()) {
  const y = d.getFullYear()
  const start = d.getMonth() >= 6 ? y : y - 1 // getMonth() is 0-based: 6 = July
  return `${start}-${String(start + 1).slice(-2)}`
}

// Current season plus the `count - 1` seasons before it, newest first.
export function recentSeasons(count = 4, d = new Date()) {
  const start = Number(currentSeason(d).slice(0, 4))
  return Array.from({ length: count }, (_, i) => {
    const s = start - i
    return `${s}-${String(s + 1).slice(-2)}`
  })
}
