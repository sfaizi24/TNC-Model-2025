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
  - **Replit Auth Integration**:
    - Migrated from custom username/password authentication to Replit Auth (OpenID Connect)
    - Authentication now supports Google, GitHub, X, Apple, and email/password login methods
    - User database migrated from SQLite to PostgreSQL for production reliability
    - Database Models:
      - `User`: Replit user profile with balance tracking (starts at $1,000)
      - `OAuth`: OAuth token storage for Replit Auth sessions
      - `Bet`: User betting history with week tracking
      - `WeeklyStats`: Weekly performance metrics (PnL, bets placed, bets won)
    - Tech Stack Updates:
      - Added Flask-SQLAlchemy for PostgreSQL ORM
      - Added Flask-Login for session management
      - Added Flask-Dance for OAuth2/OpenID Connect
      - Added PyJWT for token decoding
    - Auth Endpoints:
      - `/auth`: Initiates Replit Auth login flow
      - `/auth/logout`: Logs out and redirects to Replit logout
      - All protected routes use `@require_login` decorator
    - User Experience:
      - Single sign-on with Replit account
      - Automatic $1,000 balance for new users
      - Profile info from Replit (name, email, profile picture)
  
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
