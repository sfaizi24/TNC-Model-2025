# TNCasino redesign spec

Approved 2026-05-09 from the Claude Design handoff bundle. Scope is the four user-facing pages (Login / Betting / Leaderboard / Account) plus a CSS token rename. `/analytics`, `/admin`, error pages, routing, and `betting.js` data plumbing are out of scope.

---

## Login (`/login`)

The redesign updates the `/login` template only. Routing is unchanged — `/` still resolves to Betting; `/login` is reached by clicking a "Login" link.

- **L1.** Add `tnc-logo-shield.png` centered above the H1.
- **L2.** Add a small `TNCasino` eyebrow label above the H1.
- **L3.** Replace the H1: `⚡ Welcome to TNCasino` (blue, 48px) → `Fantasy Football Betting / with real odds.` (white, two lines, no emoji).
- **L4.** Replace the subhead: generic platform copy → `Powered by The Model™ V3. Aggregated projections from FanDuel, FantasyPros, ESPN & FirstDown — run through 50,000 Monte Carlo simulations per matchup.`
- **L5.** Delete the green prize banner entirely.
- **L6.** Replace the three feature cards (📊 / 💰 / 🏆) with a 3-stat strip: **$1,000** free balance · **$120** weekly + season prize pool · **50K** Monte Carlo sims/matchup. No emojis, no descriptions.
- **L7.** CTA copy: `Sign In with Google` → `Sign in with Google`.

---

## Betting (`/betting`)

- **Signed-out parity.** Logged-out users see the full page (matchups, odds, lineups, prize info). Two differences only: (1) no balance chip in the header, (2) every "Place Bet" button reads "Login" and links to `/login`. The existing signed-out hero banner is deleted.
- **B1.** Add a `[•] Powered by The Model™ V3 · How it works` strip directly below the page title; "How it works" links to `/about`.
- **B2.** Move the balance into the page header as a compact `Balance $X.XX` chip top-right; the `betting-info-bar` block goes away.
- **B3.** Replace the prize info with a two-column compact strip — left: `Net Profit Leader Eligible for IRL Prizes` (Weekly **$20** · Season **$100**) | right: `Bets Open Until` (Thursday Night kickoff time).
- **B4.** Restyle the Active Bets bar: bets grouped under labels **ML / O/U / HIGH / LOW**, each as a chip showing name + odds + stake + inline `Cancel` button.
- **B5.** Inline `Bet Placed · $X.XX · Cancel bet` strip at the top of each card after a bet is placed; persists until cancelled or settled.
- **B6.** Quick-stake chips above the stake input: `$10 / $25 / $50 / $100`.
- **B7.** Inline `Pays out $X.XX` preview next to the stake input as the user types (calculated from American odds).
- **B8.** Centered `VS` label between the two team names in matchup cards.
- **B9.** Lineups expansion: `▼ Show lineups` → both team lineups side-by-side in two columns separated by a divider.
- **B10.** Tab copy: `Matchups Moneyline` → `Moneyline`; `Over/Unders` → `Over/Under`.
- **B11.** Highest/Lowest Scorer cards: single button shows **odds · win % · projected pts** in one row.
- **B12.** Cards disable both odds buttons after a bet is placed; cancellation goes through the `Bet Placed` strip (B5).

---

## Leaderboard (`/leaderboard`)

- **LB1.** Card-title decorations are **plain text only** — drop both the existing emojis (👑 🏆 🔥 💩 📊 💀) and any SVG icons. Headers read: `All-Time Leaders`, `Weekly Leaders`, `Best Bets`, `Worst Bets`, `Most Popular Bets`. Bottom-performer rank cell shows just the rank number, no skull.
- **LB2.** Top-3 podium rows get a 5%-opacity gold/silver/bronze background and a matching colored border. Bottom-performer rows get the same treatment in red (`rgba(255,68,68,0.05)` bg + `#FF4444` border).
- **LB3.** Bottom-performers separator: dashed line with a centered uppercase letter-spaced `BOTTOM PERFORMERS` pill sitting on top.
- **LB4.** Most Popular Bets entries show a single status badge per bet (`Won` / `Lost` / `Pending`) plus the existing `Times` count. Drop the per-status numeric counts (`3 Won` / `2 Pending`) — every instance of the same bet has the same outcome, so a single badge suffices.

---

## Account (`/account`)

- **A1.** Page title: `My Account` → `Account`.
- **A2.** Logout: inline link → ghost-style button in the header.
- **A3.** Balance card: `Account Balance` → uppercase letter-spaced `AVAILABLE BALANCE` micro-label; `Total P&L: +$X.XX` → `+$X.XX all-time` line beneath the amount.
- **A4.** Profile card: shows **Name** and **Email** only. Drop User ID, Member Since, Starting Balance, and Admin status.
- **A5.** Section heading: `Edit Profile` → `Update Profile`.
- **A6.** Weekly Performance: 3-column table → responsive grid of small (~110px) tiles, one per **settled** week, showing `Week N` + colored P&L. Unsettled weeks (current week before Monday Night ends) do not appear.
- **A7.** Bet History: 7-column table → 4 columns (`Bet · Odds · Stake · Result`) grouped under `Week N` section headers. **Settled bets only** (`won` / `lost`); pending bets never appear here. One row per bet, single line.

---

## Tokens

- **T1.** Rename all CSS custom properties from `--fanduel-*` (and the unprefixed text/color names) to `--tnc-*`:

  | Old | New |
  | --- | --- |
  | `--fanduel-blue` | `--tnc-blue` |
  | `--fanduel-dark` | `--tnc-bg` |
  | `--fanduel-darker` | `--tnc-bg-deep` |
  | `--fanduel-gray` | `--tnc-surface` |
  | `--fanduel-light-gray` | `--tnc-border` |
  | `--text-primary` | `--tnc-fg` |
  | `--text-secondary` | `--tnc-fg-muted` |
  | `--success-green` | `--tnc-win` |
  | `--warning-yellow` | `--tnc-pending` |
  | `--error-red` | `--tnc-loss` |
  | `--text-danger` | `--tnc-loss-soft` |
  | `--primary-color` | `--tnc-blue` (alias dropped) |

- **T2.** Define the full token scaffold (typography, spacing, radii, shadows, motion) in `base.css` from the design system's `colors_and_type.css`. Do not retrofit existing CSS — adopt these tokens lazily as each page is touched during the redesign.
- **T3.** Adopt only `.tnc-num-balance` and `.tnc-num-hero` helper classes for balance displays. Skip all other helpers (`.tnc-page-title`, `.tnc-card-title`, etc.); existing per-page class names are kept.

---

## Out of scope

- `/analytics` page (Plotly-rendered, design system explicitly excluded it).
- `/admin` pages.
- `403.html` / `403.css`.
- Routing changes.
- Auth flow.
- `betting.js` data plumbing — restyling only, no rewiring of API calls or state machines.

---

## Implementation order

1. T1 token rename + T2 scaffold (no visual change).
2. Login (smallest, isolated).
3. Account (medium, isolated).
4. Leaderboard (medium, mostly text/styling).
5. Betting (largest, hits the most logic in `betting.js`).

Each step gets its own commit and is pushed after browser verification.
