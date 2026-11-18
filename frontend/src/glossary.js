/*
 * Plain-language glossary — the single source of truth for every InfoTip and
 * explanation on the site. Wording is checked against the honest-claims rules
 * (DESIGN.md §8 / ROADMAP "Current State & Honest Claims"): no ROI/CLV, edge is
 * never profit, hit rate is always a backtest figure. Don't paraphrase per page.
 */
export const GLOSSARY = {
  'value-bet': {
    term: 'Value bet',
    short: 'A match where our model rates an outcome more likely than the bookmaker’s odds imply. That gap is the “value” — it’s a disagreement with the market, not a guaranteed win.'
  },
  'edge': {
    term: 'Edge',
    short: 'How much more likely we think an outcome is than the odds imply. +10% means we rate it 10 percentage points higher than the book does. A bigger edge means a bigger disagreement — not a bigger guarantee.'
  },
  'model': {
    term: 'Model probability',
    short: 'Our estimated chance of the outcome. The ensemble learns from 50,298 matches (2014 onwards, the xG era); its Elo ratings draw on our full 128,602-match history. “49%” means we’d expect it to happen about 49 times in 100.'
  },
  'book-price': {
    term: 'Book price',
    short: 'The probability the bookmaker’s odds imply (odds of 2.58 → about 38.8%). It includes the bookmaker’s built-in margin, so it’s not a “true” probability — just what the market is pricing.'
  },
  'odds': {
    term: 'Odds',
    short: 'The bookmaker’s payout. Odds of 2.58 mean a winning £1 bet returns £2.58 (your £1 back plus £1.58 profit).'
  },
  'settled': {
    term: 'Settled',
    short: 'A prediction whose match has finished, so we know if it was right or wrong. Every settled prediction so far was logged, with a timestamp, before kick-off.'
  },
  'pending': {
    term: 'Pending',
    short: 'A prediction that’s been logged but whose match hasn’t finished yet.'
  },
  'hit-rate': {
    term: 'Hit rate',
    short: 'Elo model, backtest: across 2026/27 matches that didn’t end in a draw, the share where the Elo model’s favourite won. It’s a backtest of our baseline model — not the full ensemble, and not a live betting return.'
  },
  'brier': {
    term: 'Brier score',
    short: 'How close our probabilities are to what actually happened, across home win, draw and away win. It runs from 0 (perfect) to 2 — lower is better. Guessing ⅓ for every outcome scores 0.667.'
  },
  'matches-modelled': {
    term: 'Matches modelled',
    short: 'Our database holds 128,602 historical matches (1993 onwards), which drive the Elo ratings. The full ensemble learns from the 50,298 since 2014, when xG data begins.'
  }
};
