# Fantasy Football Analytics Platform

## Overview
A comprehensive fantasy football analytics platform designed for an interactive web dashboard. It integrates web scrapers for aggregating player projections from various sources (Sleeper, ESPN, FantasyPros, FanDuel, FirstDown), performs Monte Carlo simulations for advanced analytics and betting odds generation, and offers an interactive web dashboard built with Flask. The platform's core purpose is to provide sophisticated analytics and a betting interface for fantasy football enthusiasts, including features like lineup optimization and detailed team/player performance insights. The project aims to offer a robust, data-driven tool for fantasy football management and betting.

## User Preferences
I want iterative development.
Ask before making major changes.
I prefer detailed explanations.
Do not make changes to the folder `Z`.
Do not make changes to the file `Y`.

## System Architecture
The platform is built around a Flask web server, serving HTML templates located in `frontend/templates/index.html` with static assets in `frontend/static/images/`. The backend utilizes SQLite databases (`projections.db`, `league.db`) for data storage. Data acquisition is handled by multiple web scrapers in `backend/scrapers/`, employing Selenium and Playwright. Data processing and analysis are conducted through a series of 7 Jupyter notebooks in `backend/notebooks/`, which implement a pipeline including league data fetching, projection scraping, data cleaning, player matching, statistical analysis, lineup optimization, and Monte Carlo simulations. The UI/UX features a FanDuel-inspired dark theme with a focus on mobile-responsiveness, using card-based layouts and intuitive navigation. Key features include a real-time betting system with various bet types (matchups, over/unders, highest/lowest scorer), an analytics page for team and player performance, and user account management.

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
- **PyJWT**: Token decoding.
- **werkzeug.security**: Password hashing.