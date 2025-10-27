-- Database schema definition for reference and manual migrations.
CREATE TABLE IF NOT EXISTS players (
    sleeper_player_id TEXT PRIMARY KEY,
    full_name TEXT,
    position TEXT,
    team TEXT,
    status TEXT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS leagues (
    league_id TEXT PRIMARY KEY,
    name TEXT,
    season INTEGER,
    settings JSON
);

CREATE TABLE IF NOT EXISTS league_users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    team_name TEXT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS rosters (
    roster_id INTEGER PRIMARY KEY,
    league_id TEXT REFERENCES leagues(league_id),
    owner_id TEXT REFERENCES league_users(user_id),
    players JSON NOT NULL,
    starters JSON,
    reserves JSON,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS projections (
    source TEXT,
    season INTEGER,
    week INTEGER,
    sleeper_player_id TEXT REFERENCES players(sleeper_player_id),
    team TEXT,
    position TEXT,
    proj_points NUMERIC,
    stats JSON,
    fetched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source, season, week, sleeper_player_id)
);

CREATE TABLE IF NOT EXISTS player_actuals (
    season INTEGER,
    week INTEGER,
    sleeper_player_id TEXT REFERENCES players(sleeper_player_id),
    team TEXT,
    position TEXT,
    fantasy_points NUMERIC,
    stats JSON,
    PRIMARY KEY (season, week, sleeper_player_id)
);

CREATE TABLE IF NOT EXISTS player_aliases (
    source TEXT,
    source_player_key TEXT,
    sleeper_player_id TEXT REFERENCES players(sleeper_player_id),
    notes TEXT,
    PRIMARY KEY (source, source_player_key)
);

CREATE INDEX IF NOT EXISTS idx_projections_source_season_week
    ON projections (source, season, week);

CREATE INDEX IF NOT EXISTS idx_player_actuals_season_week_player
    ON player_actuals (season, week, sleeper_player_id);
