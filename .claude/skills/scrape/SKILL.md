---
name: scrape
description: Scrape fantasy football projections from all sources, validate data quality, handle failures, and report results. Use for weekly data collection.
disable-model-invocation: true
---

Run TNCasino projection scrapers for a given NFL week. Parse `$ARGUMENTS` for:
- First number = week number (required)
- Second number = season year (optional, default 2025)
- Source names (sleeper, espn, fantasypros, firstdown, fanduel) = run only those sources

Examples: `/scrape 17`, `/scrape 17 2025`, `/scrape espn 17`, `/scrape fanduel firstdown 17`

## Step 1: Run scrapers

```bash
python scrape.py --week <N> --season <YEAR>
```

Or for specific sources:
```bash
python scrape.py --week <N> --sources sleeper,espn
```

Read the summary output. Each source shows OK, EMPTY, or FAILED with row counts and timing.

## Step 2: Validate

```bash
python validate_scraping.py --week <N>
```

Check the result: PASS, WARN, or FAIL. PASS means 3+ sources, 150+ projections, all positions covered.

## Step 3: Handle failures

**Decision framework:**
- 4-5 sources OK: report results, done
- 3 sources OK: report which failed, ask the user if they want to retry or proceed
- 2 or fewer: investigate before proceeding

**To retry a single source:**
```bash
python -m backend.scrapers.scraper_sleeper --week "Week 17" --season 2025
python -m backend.scrapers.scraper_espn --week "Week 17" --season 2025
python -m backend.scrapers.scraper_fantasypros --week "Week 17"
python -m backend.scrapers.scraper_firstdown --week "Week 17"
python -m backend.scrapers.scraper_fanduel --week "Week 17"
```

Note: only Sleeper and ESPN accept `--season`. Add `--no-headless` to any browser-based scraper to watch it.

## Debugging scraper failures

When a scraper fails, read the scraper source file to understand what broke. Common patterns:

**SleeperScraper** (`backend/scrapers/scraper_sleeper.py`) — rarely fails
- API-based, no browser. If it fails, the Sleeper API endpoint may have changed.
- Check: `https://api.sleeper.app/v1/projections/nfl/regular/{season}/{week_number}`

**ESPNScraper** (`backend/scrapers/scraper_espn.py`) — fragile
- Uses Selenium with JavaScript position filters on ESPN's projection page.
- "Could not filter after 5 attempts": ESPN changed their filter buttons. Look at `_scrape_position()` and update the JavaScript `click_script`.
- "No tables found": table CSS classes changed. Look for `Table--fixed-left`, `Table--fixed-right`.
- 0 projections for a position: the FPTS column may have moved between the three HTML tables.
- Run with `--no-headless` to see what the browser is doing.

**FantasyProsScraper** (`backend/scrapers/scraper_fantasypros.py`) — moderate
- Selenium-based, scrolls to load all players, position-specific URLs.
- Timeout: FantasyPros may be rate-limiting. Wait 30s and retry.
- 0 players parsed: table row structure changed. Check `_scrape_position()` — expects `td` cells with player name in cells 1-3 containing `(TEAM)`, projected points in last cell.
- Status indicators (Q, O, IR) in names: the cleanup regex may need updating.

**FirstDownStudioScraper** (`backend/scrapers/scraper_firstdown.py`) — moderate
- Selenium-based, scrapes QB/RB/WR/TE/K pages separately.
- "Could not find points column": column headers changed. Look for "Proj. Pts" or "Kicking Pts" in table headers.
- Team parsing fails: matchup format `(TEAM @ OPP)` may have changed.
- Site redesigns happen periodically — may need larger scraper updates.

**FanDuelScraper** (`backend/scrapers/scraper_fanduel.py`) — fragile
- Uses Playwright (not Selenium) with network interception of GraphQL API.
- "Did not intercept any valid projection data": the GraphQL schema or endpoint changed. The scraper intercepts POST requests to `api.fanduel.com/graphql` and looks for `data.getProjections`.
- Subprocess timeout: FanDuel is slow. Check if the page loads at all with `--no-headless`.
- "Playwright not installed": run `playwright install chromium`.

## Fixing a broken scraper

1. Read the scraper source file
2. Run it with `--no-headless` to see the browser
3. Identify what changed (selector, API response, page structure)
4. Edit the scraper to fix the issue
5. Retry just that source: `python scrape.py --week <N> --sources <name>`
6. Re-validate: `python validate_scraping.py --week <N>`

## After scraping

Report to the user:
1. Which sources succeeded/failed and row counts
2. Whether validation passed
3. Any data quality concerns
4. If failures occurred: what went wrong and whether a retry is worth it
