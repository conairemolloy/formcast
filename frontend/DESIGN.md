# FormCast — Design System (DESIGN.md)

*Rewritten Nov 13 2026 from the approved v0 landing-page design (v0/formcast-landing, commit 73b59a5). Supersedes the old emerald-on-black system. Every frontend task references this file; when a component disagrees with it, the component is wrong.*

> **Source of truth for VISUALS.** For what we're allowed to *say* (claims, banned stats), the authority is "Current State & Honest Claims" in ROADMAP.md. This file governs how it looks; that file governs what it says.

---

## 1. Direction in one line

Warm near-black, premium/editorial, built to read like a quant research desk — **not** a betting site and **not** a cold Bloomberg terminal. The tell we're escaping ("obviously AI-designed"): uniform emerald-on-black, equal rounded cards, generic Tailwind defaults. We break it with a warm green-black base, a single confident coral accent, a serif display face used sparingly for emotional emphasis, and editorial/asymmetric layout.

---

## 2. Colour tokens

All colours are warm — the "blacks" are green-tinted, never cold grey. Define these as CSS custom properties on `:root` and reference them everywhere. No ad-hoc hex anywhere in components.

### Core
| Token | Hex | Use |
|---|---|---|
| `--background` | `#171e19` | Page background (warm near-black, green-tinted) |
| `--foreground` | `#f1eee4` | Primary text (warm cream, NOT pure white) |
| `--card` | `#1c2420` | Card / panel / popover / sidebar surface |
| `--muted` | `#222c25` | Muted surface (slightly lifted from bg) |
| `--secondary` / `--accent` | `#26302a` | Secondary surface, hover states, pill backgrounds |
| `--muted-foreground` | `#a5aca2` | Secondary text, labels, captions (sage-grey) |
| `--border` | `rgba(241,238,228,0.13)` | Hairline dividers and card borders (cream at ~13% — shown as `#f1eee421`) |
| `--input` | `rgba(241,238,228,0.15)` | Input borders (`#f1eee426`) |

### Accent (the ONE brand colour)
| Token | Hex | Use |
|---|---|---|
| `--primary` | `#ed5238` | THE coral/orange accent. Primary buttons, the serif-italic emphasis word, logo mark, active labels, the edge-meter fill, section eyebrow labels. |
| `--primary-foreground` | `#171e19` | Text on a coral button (the near-black, for contrast) |
| `--ring` | `#ed7559` | Focus rings, lighter coral hover (slightly brighter than primary) |

**Discipline:** coral is the *only* chromatic colour in the UI chrome. It marks the single most important thing on a screen and nothing else. If two things are coral, one of them is wrong.

### Semantic (bet outcomes / data)
| Token | Hex | Use |
|---|---|---|
| positive / edge | `#b6d294` (chart-2, soft green) | A positive edge, a settled win, "+11.0% EDGE". The ONLY positive-signal colour. |
| negative | derive a muted warm red (e.g. desaturated `#ed5238` family) | A loss, a negative figure. Use sparingly. |
| pending / caution | `#e8b64c` (chart-3, amber) | "PENDING" badges, caution states |

### Chart palette (categorical, in order)
`#ed5238` · `#b6d294` · `#e8b64c` · `#9c6bdf` · `#f1eee4`
Follow the dataviz skill for sequential/diverging needs; this is the categorical set. Never rely on colour alone to carry meaning (accessibility) — pair with labels.

### Dark-only
The product is **all-dark**. There is no light mode and no dark/light toggle (dropped — see ROADMAP backlog). Do not author light-mode token blocks.

---

## 3. Typography

Two families. A serif for *display emphasis only*, a grotesk for everything else. This split is the single biggest "not-AI-designed" lever — most generated sites are grotesk-only.

### Families
- **Display serif — Fraunces** (or the exact face in the v0 code; confirm weights at integration). Used for: large hero/section headlines, and specifically the *italic* emphasis word in a headline ("a *starting point*", "Even on a *bad day*", "[*title*]"). The italic is set in `--primary` coral or the sage `--muted-foreground` for the softer variant. Big display numbers on the stat strip are also serif (608, 128k).
- **Body grotesk — a clean sans** (the v0 default grotesk; confirm at integration — likely Geist or similar). Used for: all body copy, UI, data, tables, labels, buttons.
- **Mono** — for the uppercase tracked eyebrow labels and tabular data where it reads as "terminal". Labels like `MATCHDAY, MADE MEASURABLE`, `WHO BUILT THIS`, `02 — OUR MOST IMPORTANT FEATURE`, `RECORD #008,241`.

### Scale (two heading sizes, one body, one small — per the restraint principle)
- **Display XL** — hero headline, serif, clamp(40px → 80px), tight leading (~0.95), tracking -0.02em.
- **Display / H2** — section headline, serif, clamp(28px → 56px).
- **H3 / card title** — grotesk, ~18–20px, medium weight.
- **Body** — grotesk, 16px (1rem), line-height 1.6, `--muted-foreground` for secondary paragraphs, `--foreground` for primary.
- **Small / caption** — grotesk, ~13–14px, `--muted-foreground`.
- **Eyebrow label** — mono, ~11–12px, uppercase, letter-spacing ~0.15–0.2em, `--primary` coral.

**Numbers:** always `font-variant-numeric: tabular-nums` in tables and stat displays. Consistent decimal places site-wide — odds always 2dp (2.50 never 2.5), percentages 1dp, probabilities consistent.

---

## 4. Layout & spacing

- **Spacing base** `0.25rem` (4px). Use a consistent scale (4/8/12/16/24/32/48/64/96).
- **Radius** `0.625rem` (10px) default for cards/buttons; pills (eyebrow labels, badges) fully rounded.
- **Editorial, not a grid of equal cards.** Break the uniform-card tell: real hero with asymmetry, varied density (big where it matters, tight elsewhere), some full-bleed sections, **bordered-not-boxed** (hairline dividers and borders rather than heavy filled cards), confident whitespace contrast.
- **Hairline dividers** (`--border`) separate sections and list rows — this is a signature of the look (see the numbered feature list, the "NOT A TIPSTER →" row).
- **Numbered rows** for feature/step lists: a coral index number (`01`, `02`…) + title + muted description, divided by hairlines.
- **Mobile-first.** Every layout must work single-column at 375px and stack cleanly. The core land → tips → signup flow is judged on a phone.

---

## 5. Signature elements (over-invest in these)

1. **The edge meter** — THE screenshot asset. A horizontal stacked bar: bookmaker-implied probability in a muted/grey segment, the model's *additional* edge in `--primary` coral. The coral segment literally IS the edge. Lives on every value-bet card and the lead Today's Tips card. (Not yet in the mockup's hero cards — build it as the core card primitive.)
2. **The public ledger panel** — the dark card with `SHA-256 sealed · 0x8f2a…d91c4b`, `RECORD #008,241`, `PENDING` badge, model-vs-market price tiles. This is the trust centrepiece; the animated version is the hero demo.
3. **Serif-italic emphasis word** — one coral/sage italic word per major headline. Used sparingly, it carries all the brand personality.

---

## 6. Motion

Motion only where data changes (restraint principle):
- Probability/edge bars fill once on load.
- Numbers tick on live update.
- The public-ledger hero animates (new rows seal in).
- Nothing decorative. No parallax, no float-in-on-scroll everywhere, no animated gradients. Movement means "this is live," so it must be rare and meaningful.

---

## 7. Voice & copy (design-adjacent, but part of the brand)

Opinionated and specific, never generic AI copy:
- ✅ "The odds are a *starting point*." / "We make Villa 68%. The book says 49%." / "No deleted losing streaks." / "No black-box locks." / "Probabilities, not promises."
- ❌ "Track your favourite teams." / "Powered by AI." / "The future of betting."
- Bake in the honesty angle everywhere: "logged — win or lose," "Even on a bad day," "Nothing quietly disappears when the final whistle goes."
- Eyebrow labels are terse and declarative: `WHO BUILT THIS`, `A NOTE WHEN THERE'S VALUE`, `OUR MOST IMPORTANT FEATURE`.

---

## 8. Claims rules (hard constraint — defers to ROADMAP Current State)

The approved mockup contains placeholder/banned copy that MUST be swapped at integration:
- 🚫 **"+8.4% RETURN PER BET, LOGGED"** — BANNED (not a real figure; no ROI headline). Replace the stat strip's first tile with the verifiable record (e.g. "1,110+ / published pre-kickoff" or "608 / settled & verified"). No ROI, no CLV, no bare hit-rate.
- 🚫 **"500+ teams across 14 competitions"** — retire. Real counts: **446 teams, 11 competitions** (recounted Nov 12). Use "440+ teams · 11 leagues" or similar honest phrasing.
- 🚫 **"128k matches modelled"** — the honest count is 128,592 rows (~127,370 unique). "128k" is acceptable as a rounded figure; prefer "127k matches" or keep "128k" only if it's not paired with a false precision.
- ✅ Keep: "608 bets settled this season", the SHA-256 ledger framing, "NOT A TIPSTER", "No deleted losing streaks", "No black-box locks".
- The `[Your name] — [title]` / "your photo" About block holds Conaire's real bio + photo (placeholder until supplied).

---

## 9. Integration notes

- The v0 project outputs React + Tailwind (+ shadcn) = the FormCast stack. At integration, read the exact Tailwind config / globals.css from the v0 code and reconcile any token here that the code specifies more precisely (especially the exact Fraunces + grotesk font files/weights, and the negative-red value).
- Map these tokens into the existing `frontend` Tailwind theme so the whole app — not just the landing page — adopts them. The 25 component files currently using `emerald-*` get migrated to these tokens.
- This file is the spec; the component library audit (ROADMAP queue b) standardises cards/badges/tables/filters against it.
