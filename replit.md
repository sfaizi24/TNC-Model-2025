# Fantasy Football Analytics Platform

## Overview
A comprehensive fantasy football analytics platform designed for an interactive web dashboard. It integrates web scrapers for aggregating player projections from various sources (Sleeper, ESPN, FantasyPros, FanDuel, FirstDown), performs Monte Carlo simulations for advanced analytics and betting odds generation, and offers an interactive web dashboard built with Flask. The platform's core purpose is to provide sophisticated analytics and a betting interface for fantasy football enthusiasts, including features like lineup optimization and detailed team/player performance insights. The project aims to offer a robust, data-driven tool for fantasy football management and betting.

## Recent Changes
- **November 18, 2025 (Profile Editing Feature)**:
  - **Security**: Implemented CSRF protection using Flask-WTF for form-based endpoints
  - **User Profile**: Added ability for users to edit first name and last name on account page
  - **Form UI**: Added profile edit form with styled input fields matching FanDuel theme
  - **Validation**: Added input validation (100 character limit) and user-friendly error messages
  - **CSRF Configuration**: Disabled default CSRF checks to preserve API endpoint functionality, explicitly protected profile update route
  - **Feedback**: Success and error messages displayed via flash notifications with color-coded styling
- **November 18, 2025 (Betting Speed Optimization)**:
  - **Backend**: Optimized place_bet endpoint by reducing WeeklyStats queries from 4 to 1 per bet
  - **Frontend**: Implemented non-blocking toast notification system with slide-in animations
  - **UX**: Removed all blocking alert() and confirm() dialogs for uninterrupted betting flow
  - **UI**: Added optimistic UI updates - balance and bet list update instantly on click with automatic rollback on errors
  - **Speed**: Added quick bet amount buttons ($10, $25, $50, $100) to all bet types for rapid bet entry
  - **Feedback**: Added success flash animations on cards and toast notifications with icons
- **November 13, 2025 (Performance & UX Optimization)**:
  - Fixed critical migration logic with dialect-aware schema migrations (PostgreSQL vs SQLite compatibility)
  - Optimized image caching: increased cache duration from 1 hour to 24 hours for analytics images
  - Added SQLite connection context managers to prevent resource leaks in high-traffic API endpoints
  - Improved database query patterns with explicit ordering and limits
  - Fixed template rendering issues in analytics.html for better JavaScript compatibility
  - Added null safety checks for user queries in bet settlement endpoints
- **November 13, 2025**: Updated analytics page to dynamically use current week for images instead of hardcoded week 10; optimized Account page with smaller fonts, removed emoji from title, improved table formatting with readable bet types
- **November 12, 2025**: Updated analytics page to use `starting_status` column from projections_rosters table for starter/bench determination; optimized mobile layout with smaller fonts and tighter spacing
- **November 8, 2025**: Integrated TNC branding with transparent logo in header, removed placeholder statistics from analytics dashboard for cleaner presentation

## User Preferences
I want iterative development.
Ask before making major changes.
I prefer detailed explanations.
Do not make changes to the folder `Z`.
Do not make changes to the file `Y`.

## System Architecture
The platform is built around a Flask web server, serving HTML templates located in `frontend/templates/index.html` with static assets in `frontend/static/images/`. The backend utilizes SQLite databases (`projections.db`, `league.db`) for data storage. Data acquisition is handled by multiple web scrapers in `backend/scrapers/`, employing Selenium and Playwright. Data processing and analysis are conducted through a series of 7 Jupyter notebooks in `backend/notebooks/`, which implement a pipeline including league data fetching, projection scraping, data cleaning, player matching, statistical analysis, lineup optimization, and Monte Carlo simulations. The UI/UX features a FanDuel-inspired dark theme with a focus on mobile-responsiveness, using card-based layouts and intuitive navigation. 

### Core Features
- **Real-time Betting System**: Various bet types including matchups, over/unders, highest/lowest scorer
- **Betting Period Management**: Time-based betting deadlines with automatic lock enforcement
- **Admin Settlement Interface**: Complete bet settlement workflow with win/loss tracking
- **Admin Access Control**: Role-based permissions with is_admin column, admin-only navigation and routes
- **Unlock Functionality**: Admins can unlock locked betting periods via dedicated endpoint
- **UTC Timezone Handling**: All datetimes stored and displayed in UTC with clear labeling
- **Performance Tracking**: Separate tracking of active bets vs settled performance in weekly stats
- **Analytics Dashboard**: Team and player performance insights
- **User Account Management**: Profile management, betting history, and weekly performance tracking

### Betting Lifecycle
1. **Betting Period Setup**: Admin sets lock time for a week via `/admin` interface
2. **Open Betting**: Users can place and remove bets until the lock time
3. **Automatic Lock**: System automatically locks bets at the configured deadline
4. **Settlement**: Admin settles individual bets as won/lost, crediting/debiting user balances
5. **Week Closure**: Admin marks week as settled and creates a new betting period for next week

### Database Models
- **User**: Account information, balance, total P&L, is_admin flag (default: False)
- **Bet**: Individual bets with type, amount, odds, status (pending/won/lost), timezone-aware timestamps
- **WeeklyStats**: Performance tracking with active_bets_amount and settled_pnl
- **BettingPeriod**: Week management with UTC lock_time, is_locked, is_settled flags

### Technical Implementation
- **Admin System**: `admin_required` decorator protects admin routes, navigation hidden for non-admins
- **Timezone Handling**: All DateTime columns use `DateTime(timezone=True)` for PostgreSQL TIMESTAMPTZ
- **Dialect-Aware Migrations**: Schema migrations auto-detect database dialect (PostgreSQL/SQLite) and apply appropriate DDL
- **Resource Management**: Critical API endpoints use context managers for SQLite connections to prevent leaks
- **Performance Optimization**: 24-hour browser cache for analytics images, optimized database queries with ordering
- **Dynamic Week Tracking**: Current week determined via `get_current_week()` helper function
- **Security**: Admin privileges must be manually set in database, no self-service admin escalation
- **CSRF Protection**: Flask-WTF configured with `WTF_CSRF_CHECK_DEFAULT=False` to exempt API endpoints, form-based routes explicitly call `csrf.protect()` for security

## External Dependencies
- **Python 3.11**
- **Flask**: Web framework
- **Selenium & Playwright**: Web scraping
- **Pandas**: Data processing
- **Matplotlib & Seaborn**: Data visualization
- **SQLite**: Primary database storage
- **Replit Auth (OpenID Connect OAuth)**: User authentication supporting Google, GitHub, X, Apple, and email/password sign-in.
- **Flask-SQLAlchemy**: ORM for PostgreSQL (used for user database).
- **Flask-Login**: Session management.
- **Flask-Dance**: OAuth2/OpenID Connect integration.
- **Flask-WTF**: CSRF protection for forms.
- **PyJWT**: Token decoding.
- **werkzeug.security**: Password hashing.