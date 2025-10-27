# instructions.md — LLM Agent Build Guide

## 🎯 Goal
Build a small web app + data ingestor that:
1) Pulls exact **teams/rosters** for Sleeper league **1226433368405585920** (current season).  
2) Maintains a **projections warehouse** (multiple free sources per NFL player).  
3) Maintains **historical actuals** (player game logs & fantasy points).

MVP UI now: list each franchise and its current roster.  
Non-UI: still ingest & store projections + historicals for future features.  
Manual run: a backend CLI task to (re)load everything on demand.

---

## 🗂️ Architecture (suggested)
- Backend: **Python + FastAPI** (API), **Typer** (CLI), **Requests**, **Pandas** (parsing CSV/HTML).
- DB: **PostgreSQL** (SQLite OK in dev).
- Caching: local JSON for large endpoints (Sleeper `/players/nfl`).
- Services:
  - `/api/teams`, `/api/teams/{id}/roster` (MVP)
  - CLI `manage.py` with `ingest_*` commands.
- IDs: normalize all sources to **Sleeper `player_id`**; fall back to `(name, team, position)` + alias table.

---

## 🔧 Environment
.env (example)
    SLEEPER_LEAGUE_ID=1226433368405585920

---

## 🌐 Data Sources (free/scriptable)
Sleeper (official/undoc mix; no auth):
- /v1/league/{league_id}, /v1/league/{league_id}/users, /v1/league/{league_id}/rosters
- /v1/league/{league_id}/matchups/{week}, /v1/state/nfl
- /v1/players/nfl (large; cache daily)
- Undocumented projections (unstable): /projections/nfl/{season}/{week}?season_type=regular&position[]=QB&...

Free projections (scriptable):
- **FanDuel Research**: per-slate/position CSV (direct link; no login).
- **DailyFantasyFuel**: projections CSV (direct link).
- **ESPN (unofficial)**: JSON endpoints used by community wrappers.
- **WalterFootball**: positional HTML tables (parse).

Note: schemas vary and can change—parsers must be tolerant.

---

## 🧾 Database Schema (Postgres)
    CREATE TABLE players (
      sleeper_player_id TEXT PRIMARY KEY,
      full_name TEXT, position TEXT, team TEXT, status TEXT, metadata JSONB
    );

    CREATE TABLE leagues (
      league_id TEXT PRIMARY KEY, name TEXT, season INT, settings JSONB
    );

    CREATE TABLE league_users (
      user_id TEXT PRIMARY KEY, display_name TEXT, team_name TEXT, metadata JSONB
    );

    CREATE TABLE rosters (
      roster_id INT PRIMARY KEY,
      league_id TEXT REFERENCES leagues(league_id),
      owner_id TEXT REFERENCES league_users(user_id),
      players TEXT[] NOT NULL, starters TEXT[], reserves TEXT[], metadata JSONB
    );

    CREATE TABLE projections (
      source TEXT, season INT, week INT,
      sleeper_player_id TEXT REFERENCES players(sleeper_player_id),
      team TEXT, position TEXT, proj_points NUMERIC, stats JSONB,
      fetched_at TIMESTAMPTZ DEFAULT now(),
      PRIMARY KEY (source, season, week, sleeper_player_id)
    );

    CREATE TABLE player_actuals (
      season INT, week INT,
      sleeper_player_id TEXT REFERENCES players(sleeper_player_id),
      team TEXT, position TEXT, fantasy_points NUMERIC, stats JSONB,
      PRIMARY KEY (season, week, sleeper_player_id)
    );

Indexes recommended on:
- projections(source, season, week), player_actuals(season, week, sleeper_player_id)

---

## 🔄 Ingestion Workflows

A) Sleeper (league + rosters + directory)
1. GET `/v1/state/nfl` → current `season`, `week`.
2. GET `/v1/league/{LEAGUE}` → upsert `leagues`.
3. GET `/v1/league/{LEAGUE}/users` → upsert `league_users`.
4. GET `/v1/league/{LEAGUE}/rosters` → upsert `rosters`.
5. GET `/v1/players/nfl` → cache at `CACHE_DIR/players_nfl.json` (refresh daily) → upsert `players`.

B) Projections (multi-source; per week)
- Sleeper projections (undoc): pull JSON for all positions → map → upsert `projections`.
- FanDuel CSV: HTTP GET CSV link → parse → map → upsert.
- DailyFantasyFuel CSV: same.
- ESPN JSON: request → parse → map → upsert.
- WalterFootball HTML: parse first table with Pandas → clean → map → upsert.

Store full numeric statlines in `stats` JSON; keep `proj_points` if provided (else compute later).

C) Actuals (historical)
- ESPN JSON (unofficial) for league/boxscore endpoints → upsert `player_actuals`.
- Optionally combine Sleeper `matchups/{week}` (league coverage) + public stats to fill gaps.

---

## 🧮 Scoring (future feature)
- Read league scoring from `leagues.settings` (Sleeper).
- Maintain map (e.g., pass_yd=0.04, pass_td=4, int=-2, rush_yd=0.1, etc.).
- Function: compute_points(stats_json, scoring_rules) → decimal.
- Use to fill `player_actuals.fantasy_points` or derive `projections.proj_points` when source lacks.

---

## 🧰 CLI (manual runner)
`manage.py` (Typer commands)
- `ingest_sleeper --league 1226433368405585920`
- `ingest_projections --season 2025 --week 8 [--sources sleeper,fanduel,dff,espn,walter]`
- `ingest_actuals --season 2025 --weeks 1-8`
- `ingest_all --season 2025 --league 1226433368405585920`

Flags respected: `--concurrency`, `--timeout`, `--retries`, `--dry-run`, `--since-cache`.

---

## 🌐 API (MVP)
- GET `/teams` → `[ { roster_id, owner: { user_id, display_name, team_name } } ]`
- GET `/teams/{roster_id}/roster` → `{ starters: [player...], bench: [...], reserves: [...] }` (players expanded from `players` table)

Future:
- GET `/players/{id}/projections?season=&week=&source=`
- GET `/players/{id}/actuals?season=&week=`
- GET `/teams/{roster_id}/projections?week=`

---

## 🧩 Entity Resolution
Order of preference:
1) Use `sleeper_player_id` when source provides it.  
2) Else normalize `(name, team, position)`:
   - Name normalization: strip punctuation, middle initials, “Jr/Sr/III”, dots in initials.
   - Team code normalization (JAX↔JAC, LA↔LAR/LAC).
   - Keep overrides in `overrides.yml`.
3) Persist mappings in `player_aliases(source, source_player_key, sleeper_player_id, notes)`.

---

## 🚦 Rate & Resilience
- Cache `/v1/players/nfl` daily; stagger polling; exponential backoff with jitter on 429/5xx.
- Log each run to `logs/ingest-YYYYMMDD.log`; continue on partial failures; schema-diff guardrails per source.

---

## 🧪 Smoke Tests
- `players` count ≥ 2,000.
- `rosters` count equals Sleeper response count.
- Each projection source inserts ≥ 1 QB row for a test week.
- ≤ 2% rows unmapped after entity resolution.

---

## 📁 Layout
    /app
      /api        (FastAPI routes)
        teams.py
        players.py
      /ingest     (ingestors by source)
        sleeper.py
        proj_sleeper.py
        proj_fanduel.py
        proj_dff.py
        proj_espn.py
        proj_walter.py
        actuals_espn.py
        mapping.py
      /db
        models.py
        schema.sql
      manage.py
    /cache
    /logs

---

## 🔍 Pseudocode (indicative)

Load & cache Sleeper players
    def load_players_directory(cache_path):
        if is_fresh(cache_path, days=1):
            data = json.load(open(cache_path))
        else:
            data = http_get_json("https://api.sleeper.app/v1/players/nfl")
            json.dump(data, open(cache_path, "w"))
        upsert_players(data)

Ingest FanDuel CSV
    url = resolve_fanduel_csv(season, week, position="ALL")
    df = pd.read_csv(http_get_stream(url))
    for row in df.itertuples():
        pid = resolve_to_sleeper(row.Player, row.Team, row.Pos)
        upsert_projection("fanduel", season, week, pid, row.Pos, row.Team,
                          getattr(row, "Fpts", None), stats=row._asdict())

API: list teams (example SQL)
    SELECT r.roster_id, u.user_id, u.display_name, u.team_name
    FROM rosters r
    JOIN league_users u ON r.owner_id = u.user_id
    WHERE r.league_id = :lid
    ORDER BY r.roster_id;

---

## ✅ Definition of Done (this milestone)
- `manage.py ingest_sleeper` loads league/users/rosters/players for **1226433368405585920**.
- `manage.py ingest_projections --season 2025 --week 8` loads at least one free source (+ Sleeper undoc).
- `manage.py ingest_actuals --season 2025 --weeks 1..8` loads at least one free source.
- `/teams` and `/teams/{id}/roster` return correct data.
- All tables created; indices in place.

---

## 📝 Notes
- Undocumented endpoints (Sleeper projections, ESPN JSON) are unstable—expect schema shifts.
- Store a weekly `schema_snapshot.json` per source; alert on column/name changes.
- Make all upserts idempotent so reruns don’t duplicate rows.
