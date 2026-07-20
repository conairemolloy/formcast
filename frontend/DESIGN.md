# FormCast Design System

> **Every Phase 6 frontend task reads this file first.**
> No hardcoded colours, font sizes, spacings, or radii anywhere in the app.
> If something you need is missing from these tokens, add it here — don't invent it inline.

---

## Aesthetic Direction

**Sportsbook-premium with quant discipline.**

Near-black surfaces. Emerald accent that earns its place — used only where data is "good news." Bold tabular numbers are the hero element; everything else recedes. The product is not a developer dashboard; it's the interface for a quantitative edge. Motion signals live data. Restraint is the differentiator.

---

## 1. Colour Tokens

### Background Layers — Three Elevations

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#09090b` | Page root background — `<body>`, full-bleed sections |
| `--bg-raised` | `#111118` | Cards, panels, nav header, section containers |
| `--bg-overlay` | `#1c1c28` | Dropdowns, modals, tooltips, floating menus |

On a premium dark UI, elevation is conveyed by **background lightness + border**, not by shadows. Use shadows only for overlays (`--bg-overlay` layer).

### Brand — Emerald Ramp

| Token | Value | Usage |
|---|---|---|
| `--brand` | `#34d399` | Primary accent: active nav, selected filter border, icons, edge %, positive EV display |
| `--brand-dim` | `#10b981` | Dimmer brand: hover state on primary buttons, live-dot pulse fill |
| `--brand-subtle` | `rgba(52, 211, 153, 0.12)` | Background tint on active/selected states, value-bet cards |
| `--brand-border` | `rgba(52, 211, 153, 0.25)` | Border on brand-tinted elements (active filter buttons, live badge) |

### Positive / Negative Accents

| Token | Value | Usage |
|---|---|---|
| `--positive` | `#34d399` | Win result, positive CLV, positive EV, high-edge badge — same hue as `--brand` |
| `--positive-subtle` | `rgba(52, 211, 153, 0.12)` | Win badge bg, positive row highlight |
| `--positive-border` | `rgba(52, 211, 153, 0.22)` | Border on positive-tinted elements |
| `--negative` | `#f87171` | Loss result, negative CLV, negative EV, loss icon — restrained red, not alarming |
| `--negative-subtle` | `rgba(248, 113, 113, 0.10)` | Loss badge bg |
| `--negative-border` | `rgba(248, 113, 113, 0.20)` | Border on negative-tinted elements |

**Edge tier distinction only — the one permitted warning colour:**

| Token | Value | Usage |
|---|---|---|
| `--warning` | `#fbbf24` | Low-edge badges (5–10% edge tier) only — signals "proceed with caution" not "bad" |
| `--warning-subtle` | `rgba(251, 191, 36, 0.11)` | Background for warning-tier badge |
| `--warning-border` | `rgba(251, 191, 36, 0.20)` | Border for warning-tier badge |

### Neutral Slate Ramp — Text & Borders

| Token | Hex | Usage |
|---|---|---|
| `--text-primary` | `#f1f5f9` | Main readable content: match names, headline figures, table data |
| `--text-secondary` | `#cbd5e1` | Secondary prose, table row values that aren't the headline number |
| `--text-tertiary` | `#94a3b8` | Column headers, filter labels, metadata |
| `--text-muted` | `#64748b` | Sub-labels, implied probability, "·" separators, timestamps |
| `--text-ghost` | `#475569` | Placeholder text, disabled states, very quiet divider labels |
| `--border` | `#1e2533` | Standard card/panel border (1px — the main workhorse border) |
| `--border-subtle` | `rgba(255, 255, 255, 0.05)` | Dividers within a card (table row separators, internal section dividers) |
| `--border-focus` | `rgba(52, 211, 153, 0.50)` | Keyboard focus ring |

### Semantic Mappings — What Colour Means What

| Concept | Token(s) |
|---|---|
| Value bet found / live bet | `--brand` text + `--brand-subtle` bg + `--brand-border` border |
| Probability bar — home win | `--positive` fill |
| Probability bar — draw | `--text-ghost` fill |
| Probability bar — away win | `--negative` fill |
| Positive CLV | `--positive` |
| Negative CLV | `--negative` |
| Confidence band (uncertainty fill) | `rgba(52, 211, 153, 0.08)` — `rgba(52, 211, 153, 0.03)` gradient |
| High-edge badge (> 10%) | `--positive` text + `--positive-subtle` bg + `--positive-border` |
| Low-edge badge (5–10%) | `--warning` text + `--warning-subtle` bg + `--warning-border` |
| Win result | `--positive` icon/text |
| Loss result | `--negative` icon/text |
| Neutral outcome badge (H/D/A label) | `--text-secondary` text + `--bg-overlay` bg — outcome identity comes from the word, not colour |
| Info/notice box | `--brand-subtle` bg + `--brand-border` border + `--brand` icon — NOT blue |
| Live indicator dot | `--brand-dim` with `animate-pulse` |

### Hard Rule

**No colour outside these tokens, anywhere in the app.** The current violations (`text-blue-400`, `bg-blue-500/10`, `text-yellow-400`, `bg-yellow-500/20`, `text-purple-400`, `bg-purple-500/20`) are eliminated in Phase 6 audits. Outcome badges (H/D/A) become neutral. Info boxes become brand-tinted. Landing use-case icon colours collapse to brand/neutral.

---

## 2. Typography

### Font Families

```css
--font-ui:   -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
--font-code: "JetBrains Mono", "Fira Code", "SF Mono", ui-monospace, monospace;
```

**Inter via CDN** should be added to `index.html` in the font-loading task (Phase 6 item 3). Until then, the system-ui fallback is acceptable.

`--font-code` is reserved for: date strings (`2024-01-15`), identifiers, and code blocks only — **not** for numeric data in tables.

### Tabular Figures — The Cardinal Rule

> Every number in a table, metric card, probability display, odds column, or stake field must carry `font-variant-numeric: tabular-nums`. This keeps decimal points and digits column-aligned without switching to monospace. Apply via the `tabular-nums` Tailwind utility class or the CSS property directly.
>
> Use `--font-code` (monospace) only for date strings, technical codes, and CLI-style content — **not** as a substitute for `tabular-nums` on regular numeric data.

### Type Scale

Exactly five sizes. No other sizes are permitted (the current `text-[10px]` micro usage is grandfathered only for inline chart axis labels; no new uses).

| Role | Size | Weight | Line-height | Usage |
|---|---|---|---|---|
| **display** | `2rem` / 32px | 800 | 1.1 | ONE hero metric per screen — the signature number (e.g. edge %, CLV, hit rate hero). Use sparingly. |
| **heading** | `1.25rem` / 20px | 700 | 1.25 | Page-level H1: "Value Bets", "Dashboard", "Ratings" |
| **subheading** | `0.875rem` / 14px | 600 | 1.35 | Section headings within a page: "Live Value Bets", "Upcoming Fixtures" |
| **body** | `0.875rem` / 14px | 400 | 1.6 | Default prose, table cells, filter labels |
| **small** | `0.75rem` / 12px | 400 | 1.5 | Metadata, timestamps, sub-labels, badge text |

### Decimal-Precision Rules

These are applied globally, no exceptions:

| Data type | Format | Example |
|---|---|---|
| Decimal odds | Always 2dp | `2.50` — never `2.5` |
| Fractional odds | Reduced fraction | `3/2` |
| American odds | Signed integer | `+150`, `-200` |
| Probabilities (model %) | Always 1dp | `67.3%` — never `67%` or `67.32%` |
| Implied probability | Always 1dp | `40.0% impl.` |
| Edge % | Always 1dp | `12.4%` |
| EV | Always 3dp | `+0.124` |
| Elo rating | 0dp (integer) | `1847` |
| CLV | Always 3dp | `+0.032` |
| Hit rate / win rate | Always 1dp | `68.7%` |
| Kelly stake | Always 1dp % | `3.2% of bank` |

---

## 3. Spacing

**8px base grid.** All margins, paddings, gaps, and layout dimensions must be multiples of 4px (Tailwind's default scale already enforces this — stick to named steps, no arbitrary values).

| Step | px | Tailwind equiv | Typical use |
|---|---|---|---|
| 0.5 | 2px | `gap-0.5` | Tight icon-to-label gap |
| 1 | 4px | `p-1`, `gap-1` | Badge internal padding, icon button pad |
| 1.5 | 6px | `px-1.5` | Compact pill padding |
| 2 | 8px | `p-2`, `gap-2` | Row-level inner gaps |
| 3 | 12px | `p-3`, `gap-3` | Card internal section padding |
| 4 | 16px | `p-4`, `gap-4` | Standard card padding, section gaps |
| 5 | 20px | `space-y-5` | Between top-level page sections |
| 6 | 24px | `p-6`, `gap-6` | Generous card padding, modal padding |
| 8 | 32px | `gap-8`, `py-8` | Between major layout blocks |
| 12 | 48px | `py-12` | Section vertical breathing room (landing) |

**No `p-5`, `gap-7`, or arbitrary `px-[13px]`.** If you need a size between steps, choose the nearest step.

---

## 4. Elevation, Radius & Borders

### Border-Radius Scale

| Token | px | Usage |
|---|---|---|
| `--radius-sm` | `6px` | Buttons, filter pills, small badges, select inputs |
| `--radius-md` | `10px` | Cards, panels, section containers, nav dropdown |
| `--radius-lg` | `14px` | Modals, large overlays |
| `--radius-full` | `9999px` | Status pills (LIVE badge), avatar, progress rings |

### Elevation System

Premium dark UIs distinguish layers through **color + border**, not drop-shadows.

| Layer | Background | Border | Shadow |
|---|---|---|---|
| Base (page) | `--bg-base` | none | none |
| Raised (cards, nav) | `--bg-raised` | 1px `--border` | none |
| Overlay (dropdowns, modals) | `--bg-overlay` | 1px `--border` | `0 8px 32px rgba(0,0,0,0.5)` |

Rules:
- Cards are `--bg-raised` with a 1px `--border` border and `--radius-md` corners.
- Dividers inside a card (between rows, between header and body) use `--border-subtle` — lighter than the card border.
- Hover states on interactive rows use `rgba(255,255,255,0.03)` background — enough to register without glowing.
- Never stack the same elevation on itself (no `--bg-raised` card inside a `--bg-raised` section without a border to distinguish them).

---

## 5. Motion

**Motion only where data changes. Movement = "this is live."**

### Permitted Transitions

| Use case | Duration | Easing | Implementation |
|---|---|---|---|
| Hover colour change (text, border, bg) | `120ms` | `ease-out` | `transition-colors duration-[120ms]` |
| Probability bar fill on page load | `400ms` | `cubic-bezier(0, 0, 0.2, 1)` | `transition-[width] duration-400` once-only on mount |
| Number tick on live update | `300ms` | `ease-out` | CSS counter or JS animated value |
| Element entering view (content fade-up) | `500ms` | `cubic-bezier(0, 0, 0.2, 1)` | `animate-fade-up` (existing keyframe — use sparingly, content sections only) |
| Live dot pulse | `2s` | `ease-in-out` | `animate-pulse` — only the live status dot |
| Dropdown/modal open | `150ms` | `ease-out` | Opacity + slight translate |
| Loading spinner | Continuous | Linear | `animate-spin` |

### Disallowed

- The `ticker` keyframe in `index.css` is decorative scrolling — remove it (Phase 6 component audit).
- No looping animations on static content.
- No entrance animations on every render (only first-render / on-mount).
- No bounce, spring, or elastic easing on data elements.
- No parallax, no background movement.

---

## 6. Component Tokens

The canonical spec for primitives. Phase 6 component audit (item 2) enforces these app-wide.

### Card

```
background:    var(--bg-raised)
border:        1px solid var(--border)
border-radius: var(--radius-md)   /* 10px */
padding:       16px               /* p-4 */
```

Card header strip (section title + action link):
```
padding:          12px 16px       /* py-3 px-4 */
border-bottom:    1px solid var(--border)
title font:       subheading weight (600, 14px)
title colour:     var(--text-primary)
action link:      var(--text-muted), hover var(--brand)
```

### Badge / Pill

Three semantic variants sharing the same shape:

```
padding:       2px 8px            /* py-0.5 px-2 */
border-radius: var(--radius-sm)   /* 6px */
font-size:     small (12px)
font-weight:   600
border:        1px solid [variant-border]
```

| Variant | bg | border | text |
|---|---|---|---|
| brand (active filter, LIVE) | `--brand-subtle` | `--brand-border` | `--brand` |
| positive (win, high edge) | `--positive-subtle` | `--positive-border` | `--positive` |
| negative (loss) | `--negative-subtle` | `--negative-border` | `--negative` |
| warning (low edge) | `--warning-subtle` | `--warning-border` | `--warning` |
| neutral (outcome H/D/A, tags) | `--bg-overlay` | `--border` | `--text-secondary` |

LIVE badge uses `--radius-full` (pill shape), all others `--radius-sm`.

### Table

```
border:           1px solid var(--border)
border-radius:    var(--radius-md)
overflow:         hidden

thead row:
  background:     var(--bg-raised)
  border-bottom:  1px solid var(--border)
  cell text:      var(--text-tertiary), font-weight 500, font-size small (12px)
  text-transform: uppercase, letter-spacing: 0.05em

tbody row:
  border-bottom:  1px solid var(--border-subtle)
  hover bg:       rgba(255, 255, 255, 0.03)
  transition:     colors 120ms

All numeric cells:
  font-variant-numeric: tabular-nums
  text-align: right (unless it's the primary "name" column)
```

### Metric Display (StatCard)

Used for headline numbers: win rate, total bets, mean CLV, hit rate.

```
container:    card spec (--bg-raised, --border, --radius-md, p-4)
label:        small (12px), var(--text-muted), uppercase, tracking-wider
value:        subheading or display size depending on prominence
              font-weight: 700 (subheading) or 800 (display)
              tabular-nums
              colour: var(--text-primary) default;
                      var(--positive) for positive metrics;
                      var(--negative) for negative metrics
sub-label:    small (12px), var(--text-ghost)
```

### Probability Bar

```
container height:  6px (h-1.5)
border-radius:     var(--radius-full)
overflow:          hidden

segments:
  home:  background var(--positive)    [--brand works too, same colour]
  draw:  background var(--text-ghost)
  away:  background var(--negative)

fill animation:    width transition 400ms cubic-bezier(0,0,0.2,1) on mount only
                   initial width: 0%; animate to data value

label row below bar:
  font-size:       10px (exception — justified for inline chart labels)
  tabular-nums
  colour:          var(--text-muted)
  space-between layout
```

### Buttons

**Primary** — used for the main conversion action (Sign Up, Confirm):
```
background:    var(--brand)
color:         var(--bg-base)          /* dark text on emerald — high contrast */
border:        none
border-radius: var(--radius-sm)
padding:       8px 16px
font-size:     body (14px), font-weight 600
hover bg:      var(--brand-dim)
transition:    colors 120ms
```

**Secondary** — supporting actions (View All →, Export):
```
background:    transparent
border:        1px solid var(--border)
color:         var(--text-secondary)
border-radius: var(--radius-sm)
padding:       6px 12px
font-size:     small (12px), font-weight 500
hover border:  var(--text-ghost)
hover color:   var(--text-primary)
transition:    colors 120ms
```

**Ghost** — inline navigation actions, "Full backtest →":
```
background:    transparent
border:        none
color:         var(--text-muted)
font-size:     small (12px)
hover color:   var(--brand)
transition:    colors 120ms
padding:       2px 0   /* minimal, for alignment */
```

**Filter toggle** (active/inactive state — used in league/outcome/format buttons):
```
inactive:  bg var(--bg-raised),  border var(--border),  text var(--text-muted)
active:    bg var(--brand-subtle), border var(--brand-border), text var(--brand)
border-radius: var(--radius-sm)
padding:   6px 12px
font-size: small (12px), font-weight 500
transition: colors 120ms
```

---

## 7. CSS Custom Property Block

Drop this block into `frontend/src/index.css` (inside the `:root` selector) when Phase 6 wiring begins. **Do not wire it in yet** — this is the pre-approved block, ready to go.

```css
:root {
  /* ── Background layers ─────────────────────────────────── */
  --bg-base:             #09090b;
  --bg-raised:           #111118;
  --bg-overlay:          #1c1c28;

  /* ── Brand — emerald ──────────────────────────────────── */
  --brand:               #34d399;
  --brand-dim:           #10b981;
  --brand-subtle:        rgba(52, 211, 153, 0.12);
  --brand-border:        rgba(52, 211, 153, 0.25);

  /* ── Positive ─────────────────────────────────────────── */
  --positive:            #34d399;
  --positive-subtle:     rgba(52, 211, 153, 0.12);
  --positive-border:     rgba(52, 211, 153, 0.22);

  /* ── Negative ─────────────────────────────────────────── */
  --negative:            #f87171;
  --negative-subtle:     rgba(248, 113, 113, 0.10);
  --negative-border:     rgba(248, 113, 113, 0.20);

  /* ── Warning — edge tier badge only ───────────────────── */
  --warning:             #fbbf24;
  --warning-subtle:      rgba(251, 191, 36, 0.11);
  --warning-border:      rgba(251, 191, 36, 0.20);

  /* ── Neutral text ramp ────────────────────────────────── */
  --text-primary:        #f1f5f9;
  --text-secondary:      #cbd5e1;
  --text-tertiary:       #94a3b8;
  --text-muted:          #64748b;
  --text-ghost:          #475569;

  /* ── Borders ──────────────────────────────────────────── */
  --border:              #1e2533;
  --border-subtle:       rgba(255, 255, 255, 0.05);
  --border-focus:        rgba(52, 211, 153, 0.50);

  /* ── Typography ───────────────────────────────────────── */
  --font-ui:    -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
  --font-code:  "JetBrains Mono", "Fira Code", "SF Mono", ui-monospace, monospace;

  --text-display:        2rem;       /* 32px — hero metric only */
  --text-heading:        1.25rem;    /* 20px — page H1 */
  --text-subheading:     0.875rem;   /* 14px — section heading */
  --text-body:           0.875rem;   /* 14px — default */
  --text-small:          0.75rem;    /* 12px — labels, meta */

  --weight-display:      800;
  --weight-heading:      700;
  --weight-subheading:   600;
  --weight-body:         400;

  /* ── Border-radius ────────────────────────────────────── */
  --radius-sm:           6px;
  --radius-md:           10px;
  --radius-lg:           14px;
  --radius-full:         9999px;

  /* ── Motion ───────────────────────────────────────────── */
  --duration-fast:       120ms;
  --duration-data:       400ms;
  --duration-enter:      500ms;
  --duration-number:     300ms;
  --ease-standard:       cubic-bezier(0.4, 0, 0.2, 1);
  --ease-decelerate:     cubic-bezier(0, 0, 0.2, 1);
}
```

---

## Appendix: Colour Violation Inventory (to fix in Phase 6 item 2)

These are the ad-hoc colours currently in the codebase that conflict with the token system above. Each is replaced by the token mapping shown.

| File | Current class | Replace with |
|---|---|---|
| `ValueBets.jsx` | `bg-blue-500/10 border-blue-500/20 text-blue-300` (info box) | `--brand-subtle`, `--brand-border`, `--brand` |
| `ValueBets.jsx` | `OUTCOME_COLORS` — `bg-blue-500/20 text-blue-300`, `bg-yellow-500/20 text-yellow-300`, `bg-purple-500/20 text-purple-300` | neutral badge: `--bg-overlay`, `--border`, `--text-secondary` |
| `Dashboard.jsx` | `bg-red-500` in `MiniProbBar` away segment | `--negative` (same colour, just via token) |
| `Landing.jsx` | `bg-blue-500/10 border-blue-500/20 text-blue-400` (Analyse Any Match icon) | collapse to brand or neutral |
| `Landing.jsx` | `bg-purple-500/10 border-purple-500/20 text-purple-400` (Track Team Form icon) | collapse to brand or neutral |
| `Landing.jsx` | inline `style={{ backgroundColor: '#0a0a0f' }}` | `var(--bg-base)` |
| `Dashboard.jsx` | `text-blue-400` (Brier score colour in MODEL_STATS) | `var(--text-secondary)` — it's not positive/negative |
| `index.css` | `ticker` keyframe | remove entirely |
