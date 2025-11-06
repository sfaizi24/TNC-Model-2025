# Fantasy Football Analytics Platform

A comprehensive fantasy football analytics platform with web scrapers, Monte Carlo simulations, betting odds analysis, and an interactive dashboard.

## Features

- **Light & Fast**: SQLite database for quick queries
- **Multiple Sources**: Currently supports:
  - ✅ **First Down Studio** - Vegas-driven projections with manual PPR calculation  
  - ✅ **FanDuel** - Direct PPR projections from their GraphQL API (100% team data)
  - ✅ **Sleeper** - Undocumented REST API with ~400 projections (100% team data, "FA" for free agents)
  - ✅ **FantasyPros** - Expert consensus rankings with ~300 projections (75-98% team coverage via multi-strategy extraction)
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

## Project Structure

```
├── backend/
│   ├── notebooks/              # Jupyter notebooks for data processing
│   │   ├── 01_league_control.ipynb
│   │   ├── 02_projections_control.ipynb
│   │   ├── 03_post_scraping_processing.ipynb
│   │   ├── 04_match_projections_to_sleeper.ipynb
│   │   ├── 05_compute_player_week_stats.ipynb
│   │   ├── 06_team_lineup_optimizer.ipynb
│   │   └── 07_monte_carlo_simulations.ipynb
│   ├── scrapers/               # Web scraper modules
│   │   ├── scraper_*.py        # Individual scrapers
│   │   ├── database.py         # Projections database
│   │   └── database_league.py  # League database
│   └── data/
│       ├── csv/                # CSV exports
│       ├── images/             # Generated visualizations
│       └── databases/          # SQLite databases
├── frontend/
│   ├── templates/
│   │   └── index.html          # Dashboard web interface
│   └── static/
│       └── images/             # Web-accessible images
├── requirements.txt
├── .env                        # Configuration (Sleeper credentials)
└── README.md
```

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

3. Configure environment variables:
   - Copy `.env.example` to `.env` (if provided) or create a new `.env` file
   - Add your Sleeper username and league ID:
   ```
   SLEEPER_USERNAME=your_username
   LEAGUE_ID=your_league_id
   ```

4. For Jupyter notebooks:
   - The FanDuel scraper runs via subprocess to avoid Playwright/asyncio conflicts
   - Other scrapers (Selenium-based) run directly in the notebook
   - All notebooks are in `backend/notebooks/` and should be run in order

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
- **Team extraction**: Uses 4-strategy approach (parentheses, dedicated column, cell position, pattern matching)
- **Coverage**: 75-98% team data depending on position (WR: 98%, QB: 90%, RB: 75%)

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

## Data Validation & Management

### Master Control Panel

Use the master control notebook for complete database management:

```bash
jupyter notebook master_control.ipynb
```

The notebook includes:
- 🗑️ **Database management** - Clear entire database, specific sources, or weeks
- 📊 **Run scrapers** - Execute each scraper individually with status updates
- 📈 **Data quality checks** - View team coverage, record counts, and metrics
- 🔍 **Quick reference** - All commands in one place

### Data Validation

Explore and validate your scraped data:

```bash
jupyter notebook data_validation.ipynb
```

The validation notebook includes:
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

## Sleeper League Data System

In addition to projections, this project now includes a comprehensive **Sleeper League Data System** for analyzing your actual fantasy league!

### Features

- 📊 **League Data**: Teams, rosters, matchups, standings
- 👥 **User Management**: Track all league members and their teams
- 🏈 **NFL Player Database**: Complete player info, injuries, depth charts
- 📈 **Player Stats**: Historical performance data (passing, rushing, receiving)
- 📅 **Schedules & Bye Weeks**: NFL team schedules and bye week tracking
- 💹 **Transactions**: Trade and waiver wire history
- 🎮 **Interactive Control**: Jupyter notebook for easy data management

### Quick Start

```python
from scraper_sleeper_league import SleeperLeagueScraper
from database_league import LeagueDB

# Find your leagues
with SleeperLeagueScraper() as scraper:
    user = scraper.get_user("your_username")
    leagues = scraper.get_user_leagues(user['user_id'], "2024")
    
    # Load league data
    scraper.save_league_data(
        league_id=leagues[0]['league_id'],
        weeks=list(range(1, 10)),
        include_transactions=True
    )
    
    # Load NFL data
    scraper.save_nfl_players()
    scraper.save_player_stats("2024", 1, 9)
    scraper.save_nfl_schedule("2024")

# Query your data
with LeagueDB() as db:
    # Get standings
    rosters = db.get_rosters(league_id)
    
    # Get matchups
    matchups = db.get_matchups(league_id, week=9)
    
    # Check player stats
    stats = db.get_player_stats(player_id="player_id", season="2024")
    
    # Check bye weeks
    bye_weeks = db.get_bye_weeks("2024")
```

### Control Notebook

Use `league_control.ipynb` for an interactive interface:

```bash
jupyter notebook league_control.ipynb
```

The notebook includes:
- 🔍 League discovery by username
- 📊 Database status and metrics
- 🏆 League standings viewer
- 🎮 Matchup results by week
- 🏥 Injury reports
- 📈 Player performance lookup
- 📅 Bye week checker
- 🗑️ Database management tools

### Documentation

See **[LEAGUE_DATA_GUIDE.md](LEAGUE_DATA_GUIDE.md)** for complete documentation including:
- Database schema details
- Python API examples
- Advanced queries
- Tips and best practices

### Database Tables

- `leagues` - League information and settings
- `users` - League owners/members
- `rosters` - Teams and their players
- `matchups` - Weekly game results
- `nfl_players` - Complete NFL player database (~8000+ players)
- `player_stats` - Weekly player performance
- `nfl_schedules` - Team schedules and bye weeks
- `transactions` - Trades, adds, drops

## Workflow

The platform follows a sequential workflow:

1. **League Control** (`01_league_control.ipynb`) - Fetch Sleeper league data
2. **Projections Control** (`02_projections_control.ipynb`) - Run scrapers for player projections
3. **Post-Scraping Processing** (`03_post_scraping_processing.ipynb`) - Clean and standardize data
4. **Match to Sleeper** (`04_match_projections_to_sleeper.ipynb`) - Link projections to Sleeper player IDs
5. **Player Stats** (`05_compute_player_week_stats.ipynb`) - Calculate mean/variance for each player
6. **Lineup Optimizer** (`06_team_lineup_optimizer.ipynb`) - Generate optimal lineups for each team
7. **Monte Carlo** (`07_monte_carlo_simulations.ipynb`) - Run 50,000 simulations and generate betting odds

## Web Dashboard

A simple web dashboard displays all generated visualizations:

```bash
# Open in browser
open frontend/templates/index.html
```

Or serve with a simple HTTP server:
```bash
cd frontend
python -m http.server 8000
# Visit http://localhost:8000/templates/index.html
```

The dashboard shows:
- Monte Carlo simulation results (distributions, box plots, violin plots)
- Win probability heatmaps
- Percentile ranges
- Cumulative distribution functions
- Betting odds analysis (highest/lowest scorer, moneylines)

## Future Enhancements

- [ ] Add more projection sources
- [x] **Web dashboard for visualizations**
- [x] **Monte Carlo simulations**
- [x] **Betting odds calculator**
- [ ] Add API endpoint for dynamic data
- [ ] Add scheduling for automatic daily updates
- [ ] Export functionality (CSV, JSON)
- [ ] Historical projection tracking
- [ ] Calculate QB PPR points from component stats as well
- [ ] Add confidence scoring based on projection agreement
- [x] **Sleeper league data integration**
- [ ] Advanced analytics dashboard
- [ ] Trade analyzer
- [ ] Playoff probability calculator

