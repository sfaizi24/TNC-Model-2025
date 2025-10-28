# Fantasy Football Projections Database

A lightweight SQLite database and web scrapers for fantasy football projections from multiple sources.

## Features

- **Light & Fast**: SQLite database for quick queries
- **Multiple Sources**: Currently supports:
  - ✅ **First Down Studio** - Vegas-driven projections with manual PPR calculation  
  - ✅ **FanDuel** - Direct PPR projections from their GraphQL API (100% team data)
  - ✅ **Sleeper** - Undocumented REST API with ~400 projections (100% team data, "FA" for free agents)
  - ✅ **FantasyPros** - Expert consensus rankings with ~300 projections (team data from player names)
  - ✅ **ESPN** - ~230 player projections by position (100% team data)
- **Flexible Schema**: Easily add more projection sources
- **PPR Projections**: Configurable scoring format (PPR, Half PPR, Standard)
- **Automated Scraping**: Selenium and Playwright-based scrapers for dynamic websites
- **Easy to Extend**: Add new sources without changing database schema

## Database Schema

The database includes:
- `source_website`: Source of projections (e.g., "firstdown.studio")
- `week`: NFL week (e.g., "Week 8")
- `player_first_name`: Player's first name
- `player_last_name`: Player's last name
- `position`: Position (QB, RB, WR, TE, etc.)
- `team`: Team abbreviation (3 letters, uppercase, e.g., "KC", "SF") - available from ESPN source
- `projected_points`: Projected fantasy points
- `created_at`: Timestamp when record was created
- `updated_at`: Timestamp when record was last updated

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install browsers:
   - **First Down Studio**: Uses Chrome. Make sure Chrome is installed (ChromeDriver managed automatically)
   - **FanDuel**: Uses Playwright. After installing dependencies, run:
   ```bash
   playwright install chromium
   ```

## Usage

### Command Line

```bash
# Scrape from First Down Studio (default)
python main.py --week "Week 8" --source firstdown.studio

# Scrape from FanDuel
python main.py --week "Week 8" --source fanduel.com

# Scrape from Sleeper (specify season year)
python main.py --week "Week 9" --source sleeper.com --season 2024

# Scrape from FantasyPros
python main.py --week "Week 8" --source fantasypros.com

# Scrape from ESPN
python main.py --week "Week 8" --source espn.com

# Scrape from all sources
python main.py --week "Week 8" --source all

# Show browser while scraping
python main.py --week "Week 8" --source all --show-browser

# View stored projections
python main.py --view --week "Week 8" --source all

# View only RBs from a specific source
python main.py --view --week "Week 8" --source fanduel.com --position RB
```

### Python API

```python
from scraper_firstdown import FirstDownStudioScraper
from scraper_fanduel import FanDuelScraper
from scraper_sleeper import SleeperScraper
from scraper_fantasypros import FantasyProsScraper

# Scrape First Down Studio
with FirstDownStudioScraper(headless=True) as scraper:
    scraper.scrape_and_save(week="Week 8", scoring="PPR")

# Scrape FanDuel
with FanDuelScraper(headless=True) as scraper:
    scraper.scrape_and_save(week="Week 8")

# Scrape Sleeper
with SleeperScraper() as scraper:
    scraper.scrape_and_save(week="Week 9", season="2024")

# Scrape FantasyPros
with FantasyProsScraper(headless=True) as scraper:
    scraper.scrape_and_save(week="Week 8")

# Scrape ESPN
with ESPNScraper(headless=True) as scraper:
    scraper.scrape_and_save(week="Week 8", season="2024")
```

### Database Operations

```python
from database import ProjectionsDB

# Query projections
with ProjectionsDB() as db:
    # Get all Week 8 projections from all sources
    all_projections = db.get_projections(week="Week 8")
    
    # Get Week 8 projections from FanDuel only
    fanduel_projections = db.get_projections(
        source="fanduel.com",
        week="Week 8"
    )
    
    # Get all RB projections across all sources
    rb_projections = db.get_projections(position="RB")
    
    # Get specific player from specific source
    player = db.get_player_projection(
        first_name="Bijan",
        last_name="Robinson",
        source="firstdown.studio",
        week="Week 8"
    )
    
    # Insert single projection from a new source
    db.insert_projection(
        source="another-source.com",
        week="Week 8",
        first_name="Patrick",
        last_name="Mahomes",
        position="QB",
        projected_points=24.5
    )
```

## Adding New Sources

The database is designed to accommodate multiple projection sources:

```python
from database import ProjectionsDB

with ProjectionsDB() as db:
    db.insert_projection(
        source="fantasypros.com",  # New source
        week="Week 8",
        first_name="Josh",
        last_name="Allen",
        position="QB",
        projected_points=25.3
    )
```

## Database Location

The database file `projections.db` will be created in the project root directory.

## Notes

### First Down Studio
- Uses Selenium to handle JavaScript-rendered content
- **PPR scoring is calculated manually** for FLEX players using: `((Rush Yds + Rec Yds) / 10) + Receptions + (TDs × 6)`
- QB projections are taken directly from the site
- Missing or "-" values in stat columns are treated as zeros
- Gets all players by visiting QB and FLEX tabs

### FanDuel
- Uses Playwright to intercept network requests from their GraphQL API
- PPR projections are provided directly by FanDuel
- Automatically parses player names into first and last names
- Handles injury designations in player names (e.g., "Player Name (Q)")

### Sleeper
- Uses undocumented REST API endpoint: `/v1/projections/nfl/regular/{season}/{week}`
- Based on the [sleeper-go](https://pkg.go.dev/github.com/lum8rjack/sleeper-go#section-readme) library documentation
- Provides `pts_ppr` directly - no calculation needed!
- Returns ~400 projections per week (filters out IDP positions)
- **Team data**: Extracted from player metadata, "FA" for free agents
- **Note**: Requires using `/regular/` in the endpoint path (not documented in the Go library)

### FantasyPros
- Scrapes consensus rankings from expert aggregation site
- Uses Selenium to scrape tables from [FantasyPros rankings pages](https://www.fantasypros.com/nfl/rankings/)
- Covers all positions: QB, RB, WR, TE, K, DST
- Provides projected fantasy points directly
- Returns ~300 projections (top-ranked players at each position)

### ESPN
- Scrapes from [ESPN's Sortable Projections view](https://fantasy.espn.com/football/players/projections)
- Uses Selenium to scrape 3 parallel tables (Players, Stats, FPTS)
- Filters by each position (QB, RB, WR, TE, K, D/ST) to get ~50 per position
- Based on their undocumented API documented by [Steven Morse](https://stmorse.github.io/journal/espn-fantasy-v3.html)
- Returns ~230 player projections with **team data** (3-letter abbreviations like "KC", "ATL")
- Uses JavaScript click to navigate position filters
- Provides PPR scoring
- Handles missing values ("--", "-") as 0.0

### General
- Projections are unique per source/week/player/position combination
- Duplicate entries are automatically updated with new values
- All projections flow into the same unified database schema

## Data Validation

Use the Jupyter notebook to validate and explore your scraped data:

```bash
jupyter notebook data_validation.ipynb
```

The notebook includes:
- Database overview and schema validation
- Source and position breakdowns
- Data quality checks (missing values, duplicates, formatting)
- Top players by position
- Cross-source comparison analysis
- Interactive visualizations
- Custom query templates

## Comparing Projections

Use the included comparison tool to analyze differences between sources:

```bash
# Compare all projections for Week 8
python compare_sources.py --week "Week 8"

# Compare only RB projections
python compare_sources.py --week "Week 8" --position RB

# Show players with biggest differences
python compare_sources.py --week "Week 8" --differences

# Show top 20 biggest differences
python compare_sources.py --week "Week 8" --differences --top 20
```

This tool helps you identify consensus vs. contrarian plays by comparing projections across multiple sources.

## Future Enhancements

- [ ] Add more projection sources (ESPN, FantasyPros, Sleeper, etc.)
- [ ] Add API endpoint for web app integration
- [ ] Add scheduling for automatic daily updates
- [ ] Export functionality (CSV, JSON)
- [ ] Historical projection tracking
- [ ] Calculate QB PPR points from component stats as well
- [ ] Add confidence scoring based on projection agreement

