# Fantasy Football Analytics Platform

## Overview
A comprehensive fantasy football analytics platform featuring web scrapers, Monte Carlo simulations, betting odds analysis, and an interactive web dashboard. The platform aggregates player projections from multiple sources (Sleeper, ESPN, FantasyPros, FanDuel, FirstDown) and provides sophisticated analytics through Jupyter notebooks.

## Current State
- **Status**: Fully operational web dashboard running on Flask
- **Port**: 5000 (frontend server)
- **Last Updated**: November 6, 2025

## Project Architecture

### Frontend
- **Technology**: Flask web server serving HTML templates
- **Location**: `frontend/templates/index.html`
- **Static Assets**: `frontend/static/images/` (Monte Carlo visualizations, betting odds charts)
- **Entry Point**: `app.py` - Flask application bound to 0.0.0.0:5000

### Backend
- **Data Storage**: SQLite databases (`projections.db`, `league.db`)
- **Scrapers**: Multiple web scrapers in `backend/scrapers/`
  - ESPN, FanDuel, FantasyPros, FirstDown Studio, Sleeper
  - Uses Selenium and Playwright for dynamic content
- **Notebooks**: 7 Jupyter notebooks in `backend/notebooks/` for data processing workflow
- **Data**: CSV exports and generated visualizations in `backend/data/`

### Key Technologies
- **Python 3.11**: Core language
- **Flask**: Web framework for dashboard
- **Selenium & Playwright**: Web scraping
- **Pandas**: Data processing
- **Matplotlib & Seaborn**: Data visualization
- **SQLite**: Database storage

## Workflow Configuration
- **Name**: web-server
- **Command**: `python app.py`
- **Output**: webview on port 5000
- **Status**: Running

## Data Processing Pipeline
1. **League Control** - Fetch Sleeper league data
2. **Projections Control** - Run scrapers for player projections
3. **Post-Scraping Processing** - Clean and standardize data
4. **Match to Sleeper** - Link projections to Sleeper player IDs
5. **Player Stats** - Calculate mean/variance for each player
6. **Lineup Optimizer** - Generate optimal lineups
7. **Monte Carlo** - Run 50,000 simulations and generate betting odds

## Environment Variables
- `SLEEPER_USERNAME`: Your Sleeper username (optional, for league features)
- `LEAGUE_ID`: Your Sleeper league ID (optional, for league features)

## Recent Changes
- **November 7, 2025** (Latest):
  - **Horizontal Matchup Card Layout**:
    - **Redesigned matchup cards to be fully horizontal** - minimizes vertical space usage:
      - Teams side-by-side with odds buttons inline (Team 1 + Odds | VS | Team 2 + Odds)
      - Bet input, potential win display, and Place Bet button all on same row
      - Fixed card height (60px desktop, 54px mobile) prevents dimension changes
      - Matchup title positioned absolutely at top of card
    - **Ultra-compact sizing**:
      - Card padding: 10px 12px (desktop), 8px 10px (mobile)
      - Team names: 12px (desktop), 11px (mobile)
      - Win probabilities: 9px (desktop), 8px (mobile)
      - Odds buttons: 13px font, 6px padding (desktop)
      - Bet input: 90px width (desktop), 75px (mobile)
      - Potential win: 10px font with fixed 140px width
    - **Compact text labels**:
      - Win probability: "X.X% win" (shortened from "X.X% Win Prob")
      - Potential win: "Win: $X (Total: $Y)" (shortened, whole dollars)
      - Button text: "Place Bet" (shortened from "Select Team & Enter Amount")
  
  - **Simplified Active Bets at Top**:
    - Removed "Betting Lines" header and subtitle for cleaner layout
    - Active bets now display at top in compact format: "Owner Moneyline $520"
    - Small, minimalist design with Remove button
    - Automatically hidden when no active bets
  
  - **Owner Names Throughout**:
    - Bet descriptions now use owner names (e.g., "sfaizi24 vs xavierking4")
    - Instead of team numbers (e.g., "Team 6 vs Team 8")
    - place_bet endpoint maps team IDs to owner names from league database
    - Backward compatible with legacy bets (supports both formats)
    - Improved multi-word name support using lastIndexOf parsing
  
  - **Mobile UI Optimizations**:
    - Fixed hamburger menu z-index (z-index: 999) to prevent coverage by scrolling content
    - Fixed bet indicator matching logic by trimming whitespace from matchup descriptions
    - Added mobile-specific CSS for betting page (max-width: 767px):
      - Matchup cards stack vertically instead of side-by-side
      - Hidden "VS" text divider on mobile for cleaner layout
      - Added background to individual team sections
      - Centered and sized cards appropriately for mobile screens
    - Verified green outline and "Bet Placed" badge now display correctly for active bets
  
  - **Fixed JavaScript Syntax Error**: Corrected template string closure in renderMatchups() function
  - **Matchups Moneyline Betting System**:
    - Built complete betting interface with real matchup data from odds.db
    - Features:
      - 6 real matchups from Week 10 with live moneyline odds
      - Interactive odds selection (selectable buttons for each team)
      - Bet amount input with real-time potential win calculation
      - Place bet functionality with database transaction
      - Active bets display on same page with remove/edit capability
      - Live account balance updates after each bet
      - Horizontal tab navigation for future betting types (Over/Under, Player Props, etc.)
    - API Endpoints:
      - `GET /api/matchups`: Fetches Week 10 matchups from betting_odds_matchup_ml table
      - `POST /api/place_bet`: Places bet, updates balance, creates weekly stats
      - `GET /api/my_bets`: Returns user's pending bets
      - `DELETE /api/remove_bet/<id>`: Removes bet and refunds amount
    - Data Sources:
      - Matchup odds: `backend/data/databases/odds.db` (betting_odds_matchup_ml table)
      - Team names in format "Team 2", "Team 5", etc.
      - American odds format (+123, -123, etc.)
      - Win probabilities from Monte Carlo simulations
    - User Experience:
      - Clean card-based layout for each matchup
      - Win probability display for each team
      - Green positive odds (+), standard negative odds (-)
      - Real-time validation (insufficient balance alerts)
      - Bets are editable/removable before settlement

- **November 7, 2025**:
  - **Replit Auth Integration**:
    - Migrated to Replit Auth (OpenID Connect OAuth)
    - Authentication supports multiple login methods via Replit:
      - Google, GitHub, X (Twitter), Apple sign-in
      - Email/password authentication
    - User database using PostgreSQL
    - Database Models:
      - `User`: Replit user ID (String), profile info, balance tracking (starts at $1,000)
      - `OAuth`: OAuth token storage for Replit Auth sessions
      - `Bet`: User betting history with week tracking
      - `WeeklyStats`: Weekly performance metrics (PnL, bets placed, bets won)
    - Tech Stack:
      - Flask-SQLAlchemy for PostgreSQL ORM
      - Flask-Login for session management
      - Flask-Dance for OAuth2/OpenID Connect
      - PyJWT for token decoding
    - Auth Routes:
      - `/auth/login`: Initiates Replit Auth login flow
      - `/auth/logout`: Logs out and redirects to Replit logout
      - All protected routes use `@require_login` decorator
    - User Experience:
      - Single sign-on with Replit account
      - Automatic $1,000 balance for new users
      - Landing page with login button and feature highlights
      - Navigation shows/hides based on authentication status
  
  - **Analytics Page Integration with Real Data**:
    - Added team dropdown populated from `backend/data/databases/league.db` (12 teams)
    - "All Teams" displays `simulation_distributions_overlay_week_10.png`
    - Individual team selection shows `dist_Team_{owner}_week_10.png`
    - Player roster table displays when team is selected:
      - Shows player names, positions from `player_week_stats` table
      - Displays mean projected points (mu) from Monte Carlo simulations
      - Players sorted by projected points (descending)
    - Data sources:
      - Team rosters: `backend/data/databases/league.db` (rosters + users tables)
      - Player stats: `backend/data/databases/projections.db` (player_week_stats table)
    - New API endpoints:
      - `/api/teams`: Returns all 12 team owners from league database
      - `/api/team_players?team={owner}`: Returns starters with stats for selected team
  
- **November 7, 2025**:
  - **TNCasino Transformation**: Rebranded as fantasy football betting platform
  - **User Authentication System**:
    - Email/username + password authentication with secure password hashing (werkzeug.security)
    - Session-based login with Flask sessions
    - Signup with $1,000 starting balance
    - Welcome popup announcing prizes and free bets
    - Login required decorators protect all authenticated routes
  - **Betting Features**:
    - Users start with $1,000 in free bets
    - Weekly prize: $20 for PnL leader
    - Season prize: $100 for overall PnL leader
    - Betting page as default front page with live matchup odds
    - Real-time account balance updates
  - **Account Management**:
    - Profile information display (username, email, join date)
    - Complete betting history with status tracking (pending/won/lost)
    - **Accurate Weekly P&L Tracking**:
      - Captures starting balance before first bet of week
      - Correctly calculates P&L as: ending_balance - starting_balance
      - Auto-updates on bet placement and settlement
      - Tracks bets placed and bets won per week
  - **Database**: SQLite `users.db` with three tables:
    - `users`: Account credentials and balance
    - `bets`: Complete betting history with results
    - `weekly_stats`: Week-by-week performance tracking

- **November 6, 2025**: 
  - Migrated project to Replit environment
  - Created Flask web server (`app.py`) to serve the dashboard
  - Configured workflow to run on port 5000
  - Verified all visualizations load correctly
  - **Complete UI Redesign**: Implemented FanDuel-inspired design system
    - Dark theme with FanDuel Blue (#1493FF) as primary color
    - Mobile-responsive navigation (hamburger menu on mobile, tabs on desktop)
    - Four main pages: Login, Analytics, Betting, Account
    - Clean, modern card-based layouts
    - Optimized for mobile-first experience

## Notes
- The dashboard displays pre-generated visualizations from Week 10
- To generate new data, run the Jupyter notebooks in sequence (01-07)
- Databases are excluded from git via `.gitignore`
- Browser dependencies (ChromeDriver, Playwright) may need additional setup for scraping features
