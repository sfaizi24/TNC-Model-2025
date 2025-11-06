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
