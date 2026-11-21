/*
 * Chart theme — DESIGN.md §2 chart palette as real hex.
 *
 * Recharts writes colours into SVG attributes, where var(--x) isn't reliable
 * across browsers, so charts take hex from here instead of CSS vars. Keep these
 * in step with the :root tokens in shell.css. This is the only place chart
 * colours are defined; components import from here, never inline hex.
 */
export const CHART = {
  coral:         '#ed5238', // --primary: the hero series / the edge
  green:         '#b6d294', // --chart-2: positive edge, settled win
  amber:         '#e8b64c', // --chart-3: pending / caution
  purple:        '#9c6bdf', // --chart-4: categorical accent
  red:           '#d17261', // --chart-5: negative / loss figure
  cream:         '#f1eee4', // --foreground
  grid:          'rgba(241,238,228,0.08)',
  axis:          '#a5aca2', // --muted-foreground
  tooltipBg:     '#1c2420', // --card
  tooltipBorder: 'rgba(241,238,228,0.13)', // hairline --border
}

// Spread onto <XAxis>/<YAxis>: sage mono ticks, no axis or tick lines.
export const AXIS = {
  tick: { fill: CHART.axis, fontSize: 10, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
  axisLine: false,
  tickLine: false,
}

// Spread onto <CartesianGrid>: faint horizontal hairlines only.
export const GRID = {
  stroke: CHART.grid,
  vertical: false,
}

// Inline style for custom tooltip containers.
export const TOOLTIP_STYLE = {
  background: CHART.tooltipBg,
  border: `1px solid ${CHART.tooltipBorder}`,
  borderRadius: 8,
  padding: '6px 10px',
  fontSize: 12,
  color: CHART.cream,
}
