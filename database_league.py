import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import os

class LeagueDB:
    """SQLite database for Sleeper fantasy league data."""
    
    def __init__(self, db_path: str = "league.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.create_tables()
    
    def create_tables(self):
        """Create all league-related tables."""
        cursor = self.conn.cursor()
        
        # League information table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                league_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                season TEXT NOT NULL,
                season_type TEXT,
                sport TEXT,
                status TEXT,
                total_rosters INTEGER,
                roster_positions TEXT,
                scoring_settings TEXT,
                settings TEXT,
                previous_league_id TEXT,
                bracket_id TEXT,
                draft_id TEXT,
                avatar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Users/Owners table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                avatar TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Rosters/Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rosters (
                roster_id INTEGER,
                league_id TEXT NOT NULL,
                owner_id TEXT,
                co_owners TEXT,
                team_name TEXT,
                starters TEXT,
                players TEXT,
                reserve TEXT,
                taxi TEXT,
                settings TEXT,
                metadata TEXT,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                fpts REAL DEFAULT 0,
                fpts_against REAL DEFAULT 0,
                fpts_decimal REAL DEFAULT 0,
                fpts_against_decimal REAL DEFAULT 0,
                total_moves INTEGER DEFAULT 0,
                waiver_position INTEGER,
                waiver_budget_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (roster_id, league_id),
                FOREIGN KEY (league_id) REFERENCES leagues(league_id),
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        """)
        
        # Matchups table (for weekly games)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matchups (
                matchup_id TEXT PRIMARY KEY,
                league_id TEXT NOT NULL,
                week INTEGER NOT NULL,
                roster_id INTEGER NOT NULL,
                matchup_id_number INTEGER,
                starters TEXT,
                players TEXT,
                points REAL DEFAULT 0,
                custom_points REAL,
                players_points TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(league_id),
                FOREIGN KEY (roster_id, league_id) REFERENCES rosters(roster_id, league_id)
            )
        """)
        
        # NFL Players metadata table (comprehensive player information)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nfl_players (
                player_id TEXT PRIMARY KEY,
                full_name TEXT,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                team TEXT,
                number INTEGER,
                age INTEGER,
                height TEXT,
                weight TEXT,
                college TEXT,
                years_exp INTEGER,
                birth_date TEXT,
                birth_city TEXT,
                birth_state TEXT,
                birth_country TEXT,
                high_school TEXT,
                status TEXT,
                active BOOLEAN,
                injury_status TEXT,
                injury_body_part TEXT,
                injury_notes TEXT,
                injury_start_date TEXT,
                practice_participation TEXT,
                depth_chart_position TEXT,
                depth_chart_order INTEGER,
                search_rank INTEGER,
                fantasy_positions TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NFL Team schedules table (for bye weeks and opponent schedules)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nfl_schedules (
                schedule_id TEXT PRIMARY KEY,
                season TEXT NOT NULL,
                week INTEGER NOT NULL,
                team TEXT NOT NULL,
                opponent TEXT,
                is_home BOOLEAN,
                is_bye BOOLEAN DEFAULT FALSE,
                game_date TEXT,
                game_time TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season, week, team)
            )
        """)
        
        # Player stats table (past performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                stat_id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                season TEXT NOT NULL,
                week INTEGER NOT NULL,
                team TEXT,
                opponent TEXT,
                
                -- Passing stats
                pass_att INTEGER DEFAULT 0,
                pass_cmp INTEGER DEFAULT 0,
                pass_yd REAL DEFAULT 0,
                pass_td INTEGER DEFAULT 0,
                pass_int INTEGER DEFAULT 0,
                pass_2pt INTEGER DEFAULT 0,
                pass_int_td INTEGER DEFAULT 0,
                pass_fd INTEGER DEFAULT 0,
                pass_sack INTEGER DEFAULT 0,
                pass_sack_yd REAL DEFAULT 0,
                
                -- Rushing stats
                rush_att INTEGER DEFAULT 0,
                rush_yd REAL DEFAULT 0,
                rush_td INTEGER DEFAULT 0,
                rush_2pt INTEGER DEFAULT 0,
                rush_fd INTEGER DEFAULT 0,
                rush_fumble INTEGER DEFAULT 0,
                rush_fumble_lost INTEGER DEFAULT 0,
                
                -- Receiving stats
                rec_tgt INTEGER DEFAULT 0,
                rec INTEGER DEFAULT 0,
                rec_yd REAL DEFAULT 0,
                rec_td INTEGER DEFAULT 0,
                rec_2pt INTEGER DEFAULT 0,
                rec_fd INTEGER DEFAULT 0,
                rec_fumble INTEGER DEFAULT 0,
                rec_fumble_lost INTEGER DEFAULT 0,
                
                -- Fantasy points
                pts_std REAL DEFAULT 0,
                pts_half_ppr REAL DEFAULT 0,
                pts_ppr REAL DEFAULT 0,
                
                -- Special teams
                st_td INTEGER DEFAULT 0,
                st_ff INTEGER DEFAULT 0,
                st_fum_rec INTEGER DEFAULT 0,
                
                -- Kicking
                fgm_0_19 INTEGER DEFAULT 0,
                fgm_20_29 INTEGER DEFAULT 0,
                fgm_30_39 INTEGER DEFAULT 0,
                fgm_40_49 INTEGER DEFAULT 0,
                fgm_50p INTEGER DEFAULT 0,
                fgm INTEGER DEFAULT 0,
                fga INTEGER DEFAULT 0,
                xpm INTEGER DEFAULT 0,
                xpa INTEGER DEFAULT 0,
                
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES nfl_players(player_id),
                UNIQUE(player_id, season, week)
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                league_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT,
                roster_ids TEXT,
                settings TEXT,
                metadata TEXT,
                adds TEXT,
                drops TEXT,
                draft_picks TEXT,
                waiver_budget TEXT,
                creator TEXT,
                created BIGINT,
                consenter_ids TEXT,
                status_updated BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(league_id)
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rosters_league ON rosters(league_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rosters_owner ON rosters(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matchups_league_week ON matchups(league_id, week)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matchups_roster ON matchups(roster_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_team ON nfl_players(team)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_position ON nfl_players(position)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_status ON nfl_players(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_team_week ON nfl_schedules(team, week)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_bye ON nfl_schedules(is_bye)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_player_week ON player_stats(player_id, week)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_season_week ON player_stats(season, week)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_league ON transactions(league_id)")
        
        self.conn.commit()
    
    # ==================== League Methods ====================
    
    def insert_league(self, league_data: Dict):
        """Insert or update league information."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO leagues 
            (league_id, name, season, season_type, sport, status, total_rosters,
             roster_positions, scoring_settings, settings, previous_league_id,
             bracket_id, draft_id, avatar, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(league_id) DO UPDATE SET
                name = excluded.name,
                status = excluded.status,
                total_rosters = excluded.total_rosters,
                roster_positions = excluded.roster_positions,
                scoring_settings = excluded.scoring_settings,
                settings = excluded.settings,
                updated_at = CURRENT_TIMESTAMP
        """, (
            league_data['league_id'],
            league_data['name'],
            league_data['season'],
            league_data.get('season_type'),
            league_data.get('sport'),
            league_data.get('status'),
            league_data.get('total_rosters'),
            str(league_data.get('roster_positions')),
            str(league_data.get('scoring_settings')),
            str(league_data.get('settings')),
            league_data.get('previous_league_id'),
            league_data.get('bracket_id'),
            league_data.get('draft_id'),
            league_data.get('avatar')
        ))
        
        self.conn.commit()
    
    def get_league(self, league_id: str) -> Optional[Dict]:
        """Get league information."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM leagues WHERE league_id = ?", (league_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_leagues(self) -> List[Dict]:
        """Get all leagues."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM leagues ORDER BY season DESC, name")
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== User Methods ====================
    
    def insert_user(self, user_data: Dict):
        """Insert or update user information."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO users 
            (user_id, username, display_name, avatar, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name,
                avatar = excluded.avatar,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_data['user_id'],
            user_data.get('username'),
            user_data.get('display_name'),
            user_data.get('avatar'),
            str(user_data.get('metadata'))
        ))
        
        self.conn.commit()
    
    def insert_users_batch(self, users: List[Dict]):
        """Insert multiple users efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (u['user_id'], u.get('username'), u.get('display_name'), 
             u.get('avatar'), str(u.get('metadata')))
            for u in users
        ]
        
        cursor.executemany("""
            INSERT INTO users 
            (user_id, username, display_name, avatar, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name,
                avatar = excluded.avatar,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_users(self, league_id: Optional[str] = None) -> List[Dict]:
        """Get all users, optionally filtered by league."""
        cursor = self.conn.cursor()
        
        if league_id:
            cursor.execute("""
                SELECT DISTINCT u.* FROM users u
                JOIN rosters r ON u.user_id = r.owner_id
                WHERE r.league_id = ?
                ORDER BY u.display_name
            """, (league_id,))
        else:
            cursor.execute("SELECT * FROM users ORDER BY display_name")
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Roster Methods ====================
    
    def insert_roster(self, roster_data: Dict, league_id: str):
        """Insert or update roster information."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO rosters 
            (roster_id, league_id, owner_id, co_owners, team_name, starters, players,
             reserve, taxi, settings, metadata, wins, losses, ties, fpts, fpts_against,
             fpts_decimal, fpts_against_decimal, total_moves, waiver_position,
             waiver_budget_used, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(roster_id, league_id) DO UPDATE SET
                owner_id = excluded.owner_id,
                co_owners = excluded.co_owners,
                team_name = excluded.team_name,
                starters = excluded.starters,
                players = excluded.players,
                reserve = excluded.reserve,
                taxi = excluded.taxi,
                settings = excluded.settings,
                metadata = excluded.metadata,
                wins = excluded.wins,
                losses = excluded.losses,
                ties = excluded.ties,
                fpts = excluded.fpts,
                fpts_against = excluded.fpts_against,
                fpts_decimal = excluded.fpts_decimal,
                fpts_against_decimal = excluded.fpts_against_decimal,
                total_moves = excluded.total_moves,
                waiver_position = excluded.waiver_position,
                waiver_budget_used = excluded.waiver_budget_used,
                updated_at = CURRENT_TIMESTAMP
        """, (
            roster_data['roster_id'],
            league_id,
            roster_data.get('owner_id'),
            str(roster_data.get('co_owners')),
            roster_data.get('metadata', {}).get('team_name'),
            str(roster_data.get('starters')),
            str(roster_data.get('players')),
            str(roster_data.get('reserve')),
            str(roster_data.get('taxi')),
            str(roster_data.get('settings')),
            str(roster_data.get('metadata')),
            roster_data.get('settings', {}).get('wins', 0),
            roster_data.get('settings', {}).get('losses', 0),
            roster_data.get('settings', {}).get('ties', 0),
            roster_data.get('settings', {}).get('fpts', 0),
            roster_data.get('settings', {}).get('fpts_against', 0),
            roster_data.get('settings', {}).get('fpts_decimal', 0),
            roster_data.get('settings', {}).get('fpts_against_decimal', 0),
            roster_data.get('settings', {}).get('total_moves', 0),
            roster_data.get('settings', {}).get('waiver_position'),
            roster_data.get('settings', {}).get('waiver_budget_used', 0)
        ))
        
        self.conn.commit()
    
    def insert_rosters_batch(self, rosters: List[Dict], league_id: str):
        """Insert multiple rosters efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                r['roster_id'], league_id, r.get('owner_id'), str(r.get('co_owners')),
                r.get('metadata', {}).get('team_name'), str(r.get('starters')), str(r.get('players')),
                str(r.get('reserve')), str(r.get('taxi')), str(r.get('settings')), str(r.get('metadata')),
                r.get('settings', {}).get('wins', 0), r.get('settings', {}).get('losses', 0),
                r.get('settings', {}).get('ties', 0), r.get('settings', {}).get('fpts', 0),
                r.get('settings', {}).get('fpts_against', 0), r.get('settings', {}).get('fpts_decimal', 0),
                r.get('settings', {}).get('fpts_against_decimal', 0), r.get('settings', {}).get('total_moves', 0),
                r.get('settings', {}).get('waiver_position'), r.get('settings', {}).get('waiver_budget_used', 0)
            )
            for r in rosters
        ]
        
        cursor.executemany("""
            INSERT INTO rosters 
            (roster_id, league_id, owner_id, co_owners, team_name, starters, players,
             reserve, taxi, settings, metadata, wins, losses, ties, fpts, fpts_against,
             fpts_decimal, fpts_against_decimal, total_moves, waiver_position,
             waiver_budget_used, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(roster_id, league_id) DO UPDATE SET
                owner_id = excluded.owner_id,
                co_owners = excluded.co_owners,
                team_name = excluded.team_name,
                starters = excluded.starters,
                players = excluded.players,
                reserve = excluded.reserve,
                taxi = excluded.taxi,
                settings = excluded.settings,
                metadata = excluded.metadata,
                wins = excluded.wins,
                losses = excluded.losses,
                ties = excluded.ties,
                fpts = excluded.fpts,
                fpts_against = excluded.fpts_against,
                fpts_decimal = excluded.fpts_decimal,
                fpts_against_decimal = excluded.fpts_against_decimal,
                total_moves = excluded.total_moves,
                waiver_position = excluded.waiver_position,
                waiver_budget_used = excluded.waiver_budget_used,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_rosters(self, league_id: str) -> List[Dict]:
        """Get all rosters for a league."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.*, u.username, u.display_name 
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE r.league_id = ?
            ORDER BY r.wins DESC, r.fpts DESC
        """, (league_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_roster(self, roster_id: int, league_id: str) -> Optional[Dict]:
        """Get a specific roster."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.*, u.username, u.display_name 
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE r.roster_id = ? AND r.league_id = ?
        """, (roster_id, league_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== Matchup Methods ====================
    
    def insert_matchup(self, matchup_data: Dict, league_id: str, week: int):
        """Insert or update matchup information."""
        cursor = self.conn.cursor()
        
        matchup_id = f"{league_id}_{week}_{matchup_data['roster_id']}"
        
        cursor.execute("""
            INSERT INTO matchups 
            (matchup_id, league_id, week, roster_id, matchup_id_number, starters,
             players, points, custom_points, players_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(matchup_id) DO UPDATE SET
                matchup_id_number = excluded.matchup_id_number,
                starters = excluded.starters,
                players = excluded.players,
                points = excluded.points,
                custom_points = excluded.custom_points,
                players_points = excluded.players_points,
                updated_at = CURRENT_TIMESTAMP
        """, (
            matchup_id,
            league_id,
            week,
            matchup_data['roster_id'],
            matchup_data.get('matchup_id'),
            str(matchup_data.get('starters')),
            str(matchup_data.get('players')),
            matchup_data.get('points', 0),
            matchup_data.get('custom_points'),
            str(matchup_data.get('players_points'))
        ))
        
        self.conn.commit()
    
    def insert_matchups_batch(self, matchups: List[Dict], league_id: str, week: int):
        """Insert multiple matchups efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                f"{league_id}_{week}_{m['roster_id']}",
                league_id,
                week,
                m['roster_id'],
                m.get('matchup_id'),
                str(m.get('starters')),
                str(m.get('players')),
                m.get('points', 0),
                m.get('custom_points'),
                str(m.get('players_points'))
            )
            for m in matchups
        ]
        
        cursor.executemany("""
            INSERT INTO matchups 
            (matchup_id, league_id, week, roster_id, matchup_id_number, starters,
             players, points, custom_points, players_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(matchup_id) DO UPDATE SET
                matchup_id_number = excluded.matchup_id_number,
                starters = excluded.starters,
                players = excluded.players,
                points = excluded.points,
                custom_points = excluded.custom_points,
                players_points = excluded.players_points,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_matchups(self, league_id: str, week: Optional[int] = None) -> List[Dict]:
        """Get matchups for a league, optionally filtered by week."""
        cursor = self.conn.cursor()
        
        if week is not None:
            cursor.execute("""
                SELECT m.*, r.team_name, u.display_name 
                FROM matchups m
                LEFT JOIN rosters r ON m.roster_id = r.roster_id AND m.league_id = r.league_id
                LEFT JOIN users u ON r.owner_id = u.user_id
                WHERE m.league_id = ? AND m.week = ?
                ORDER BY m.matchup_id_number, m.points DESC
            """, (league_id, week))
        else:
            cursor.execute("""
                SELECT m.*, r.team_name, u.display_name 
                FROM matchups m
                LEFT JOIN rosters r ON m.roster_id = r.roster_id AND m.league_id = r.league_id
                LEFT JOIN users u ON r.owner_id = u.user_id
                WHERE m.league_id = ?
                ORDER BY m.week DESC, m.matchup_id_number, m.points DESC
            """, (league_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== NFL Player Methods ====================
    
    def insert_nfl_player(self, player_data: Dict):
        """Insert or update NFL player information."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO nfl_players 
            (player_id, full_name, first_name, last_name, position, team, number, age,
             height, weight, college, years_exp, birth_date, birth_city, birth_state,
             birth_country, high_school, status, active, injury_status, injury_body_part,
             injury_notes, injury_start_date, practice_participation, depth_chart_position,
             depth_chart_order, search_rank, fantasy_positions, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                full_name = excluded.full_name,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                position = excluded.position,
                team = excluded.team,
                number = excluded.number,
                age = excluded.age,
                status = excluded.status,
                active = excluded.active,
                injury_status = excluded.injury_status,
                injury_body_part = excluded.injury_body_part,
                injury_notes = excluded.injury_notes,
                injury_start_date = excluded.injury_start_date,
                practice_participation = excluded.practice_participation,
                depth_chart_position = excluded.depth_chart_position,
                depth_chart_order = excluded.depth_chart_order,
                search_rank = excluded.search_rank,
                fantasy_positions = excluded.fantasy_positions,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            player_data['player_id'],
            player_data.get('full_name'),
            player_data.get('first_name'),
            player_data.get('last_name'),
            player_data.get('position'),
            player_data.get('team'),
            player_data.get('number'),
            player_data.get('age'),
            player_data.get('height'),
            player_data.get('weight'),
            player_data.get('college'),
            player_data.get('years_exp'),
            player_data.get('birth_date'),
            player_data.get('birth_city'),
            player_data.get('birth_state'),
            player_data.get('birth_country'),
            player_data.get('high_school'),
            player_data.get('status'),
            player_data.get('active'),
            player_data.get('injury_status'),
            player_data.get('injury_body_part'),
            player_data.get('injury_notes'),
            player_data.get('injury_start_date'),
            player_data.get('practice_participation'),
            player_data.get('depth_chart_position'),
            player_data.get('depth_chart_order'),
            player_data.get('search_rank'),
            str(player_data.get('fantasy_positions')),
            str(player_data.get('metadata'))
        ))
        
        self.conn.commit()
    
    def insert_nfl_players_batch(self, players: List[Dict]):
        """Insert multiple NFL players efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                p['player_id'], p.get('full_name'), p.get('first_name'), p.get('last_name'),
                p.get('position'), p.get('team'), p.get('number'), p.get('age'),
                p.get('height'), p.get('weight'), p.get('college'), p.get('years_exp'),
                p.get('birth_date'), p.get('birth_city'), p.get('birth_state'),
                p.get('birth_country'), p.get('high_school'), p.get('status'), p.get('active'),
                p.get('injury_status'), p.get('injury_body_part'), p.get('injury_notes'),
                p.get('injury_start_date'), p.get('practice_participation'),
                p.get('depth_chart_position'), p.get('depth_chart_order'),
                p.get('search_rank'), str(p.get('fantasy_positions')), str(p.get('metadata'))
            )
            for p in players
        ]
        
        cursor.executemany("""
            INSERT INTO nfl_players 
            (player_id, full_name, first_name, last_name, position, team, number, age,
             height, weight, college, years_exp, birth_date, birth_city, birth_state,
             birth_country, high_school, status, active, injury_status, injury_body_part,
             injury_notes, injury_start_date, practice_participation, depth_chart_position,
             depth_chart_order, search_rank, fantasy_positions, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                full_name = excluded.full_name,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                position = excluded.position,
                team = excluded.team,
                number = excluded.number,
                age = excluded.age,
                status = excluded.status,
                active = excluded.active,
                injury_status = excluded.injury_status,
                injury_body_part = excluded.injury_body_part,
                injury_notes = excluded.injury_notes,
                injury_start_date = excluded.injury_start_date,
                practice_participation = excluded.practice_participation,
                depth_chart_position = excluded.depth_chart_position,
                depth_chart_order = excluded.depth_chart_order,
                search_rank = excluded.search_rank,
                fantasy_positions = excluded.fantasy_positions,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_nfl_players(self, team: Optional[str] = None, position: Optional[str] = None,
                       status: Optional[str] = None) -> List[Dict]:
        """Get NFL players with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM nfl_players WHERE 1=1"
        params = []
        
        if team:
            query += " AND team = ?"
            params.append(team)
        
        if position:
            query += " AND position = ?"
            params.append(position)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY search_rank DESC, full_name"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_nfl_player(self, player_id: str) -> Optional[Dict]:
        """Get a specific NFL player."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM nfl_players WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== Schedule Methods ====================
    
    def insert_schedule(self, schedule_data: Dict):
        """Insert or update schedule information."""
        cursor = self.conn.cursor()
        
        schedule_id = f"{schedule_data['season']}_{schedule_data['week']}_{schedule_data['team']}"
        
        cursor.execute("""
            INSERT INTO nfl_schedules 
            (schedule_id, season, week, team, opponent, is_home, is_bye, game_date,
             game_time, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(season, week, team) DO UPDATE SET
                opponent = excluded.opponent,
                is_home = excluded.is_home,
                is_bye = excluded.is_bye,
                game_date = excluded.game_date,
                game_time = excluded.game_time,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            schedule_id,
            schedule_data['season'],
            schedule_data['week'],
            schedule_data['team'],
            schedule_data.get('opponent'),
            schedule_data.get('is_home', False),
            schedule_data.get('is_bye', False),
            schedule_data.get('game_date'),
            schedule_data.get('game_time'),
            str(schedule_data.get('metadata'))
        ))
        
        self.conn.commit()
    
    def insert_schedules_batch(self, schedules: List[Dict]):
        """Insert multiple schedules efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                f"{s['season']}_{s['week']}_{s['team']}",
                s['season'], s['week'], s['team'], s.get('opponent'),
                s.get('is_home', False), s.get('is_bye', False),
                s.get('game_date'), s.get('game_time'), str(s.get('metadata'))
            )
            for s in schedules
        ]
        
        cursor.executemany("""
            INSERT INTO nfl_schedules 
            (schedule_id, season, week, team, opponent, is_home, is_bye, game_date,
             game_time, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(season, week, team) DO UPDATE SET
                opponent = excluded.opponent,
                is_home = excluded.is_home,
                is_bye = excluded.is_bye,
                game_date = excluded.game_date,
                game_time = excluded.game_time,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_schedules(self, season: Optional[str] = None, week: Optional[int] = None,
                     team: Optional[str] = None, is_bye: Optional[bool] = None) -> List[Dict]:
        """Get schedules with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM nfl_schedules WHERE 1=1"
        params = []
        
        if season:
            query += " AND season = ?"
            params.append(season)
        
        if week is not None:
            query += " AND week = ?"
            params.append(week)
        
        if team:
            query += " AND team = ?"
            params.append(team)
        
        if is_bye is not None:
            query += " AND is_bye = ?"
            params.append(is_bye)
        
        query += " ORDER BY week, team"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_bye_weeks(self, season: str) -> Dict[str, int]:
        """Get bye weeks for all teams in a season."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT team, week FROM nfl_schedules 
            WHERE season = ? AND is_bye = TRUE
            ORDER BY team
        """, (season,))
        
        return {row['team']: row['week'] for row in cursor.fetchall()}
    
    # ==================== Player Stats Methods ====================
    
    def insert_player_stat(self, stat_data: Dict):
        """Insert or update player stats."""
        cursor = self.conn.cursor()
        
        stat_id = f"{stat_data['player_id']}_{stat_data['season']}_{stat_data['week']}"
        
        cursor.execute("""
            INSERT INTO player_stats 
            (stat_id, player_id, season, week, team, opponent,
             pass_att, pass_cmp, pass_yd, pass_td, pass_int, pass_2pt, pass_int_td,
             pass_fd, pass_sack, pass_sack_yd,
             rush_att, rush_yd, rush_td, rush_2pt, rush_fd, rush_fumble, rush_fumble_lost,
             rec_tgt, rec, rec_yd, rec_td, rec_2pt, rec_fd, rec_fumble, rec_fumble_lost,
             pts_std, pts_half_ppr, pts_ppr,
             st_td, st_ff, st_fum_rec,
             fgm_0_19, fgm_20_29, fgm_30_39, fgm_40_49, fgm_50p, fgm, fga, xpm, xpa,
             metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id, season, week) DO UPDATE SET
                team = excluded.team,
                opponent = excluded.opponent,
                pass_att = excluded.pass_att,
                pass_cmp = excluded.pass_cmp,
                pass_yd = excluded.pass_yd,
                pass_td = excluded.pass_td,
                pass_int = excluded.pass_int,
                pass_2pt = excluded.pass_2pt,
                pass_int_td = excluded.pass_int_td,
                pass_fd = excluded.pass_fd,
                pass_sack = excluded.pass_sack,
                pass_sack_yd = excluded.pass_sack_yd,
                rush_att = excluded.rush_att,
                rush_yd = excluded.rush_yd,
                rush_td = excluded.rush_td,
                rush_2pt = excluded.rush_2pt,
                rush_fd = excluded.rush_fd,
                rush_fumble = excluded.rush_fumble,
                rush_fumble_lost = excluded.rush_fumble_lost,
                rec_tgt = excluded.rec_tgt,
                rec = excluded.rec,
                rec_yd = excluded.rec_yd,
                rec_td = excluded.rec_td,
                rec_2pt = excluded.rec_2pt,
                rec_fd = excluded.rec_fd,
                rec_fumble = excluded.rec_fumble,
                rec_fumble_lost = excluded.rec_fumble_lost,
                pts_std = excluded.pts_std,
                pts_half_ppr = excluded.pts_half_ppr,
                pts_ppr = excluded.pts_ppr,
                st_td = excluded.st_td,
                st_ff = excluded.st_ff,
                st_fum_rec = excluded.st_fum_rec,
                fgm_0_19 = excluded.fgm_0_19,
                fgm_20_29 = excluded.fgm_20_29,
                fgm_30_39 = excluded.fgm_30_39,
                fgm_40_49 = excluded.fgm_40_49,
                fgm_50p = excluded.fgm_50p,
                fgm = excluded.fgm,
                fga = excluded.fga,
                xpm = excluded.xpm,
                xpa = excluded.xpa,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            stat_id,
            stat_data['player_id'],
            stat_data['season'],
            stat_data['week'],
            stat_data.get('team'),
            stat_data.get('opponent'),
            stat_data.get('pass_att', 0), stat_data.get('pass_cmp', 0), stat_data.get('pass_yd', 0),
            stat_data.get('pass_td', 0), stat_data.get('pass_int', 0), stat_data.get('pass_2pt', 0),
            stat_data.get('pass_int_td', 0), stat_data.get('pass_fd', 0), stat_data.get('pass_sack', 0),
            stat_data.get('pass_sack_yd', 0),
            stat_data.get('rush_att', 0), stat_data.get('rush_yd', 0), stat_data.get('rush_td', 0),
            stat_data.get('rush_2pt', 0), stat_data.get('rush_fd', 0), stat_data.get('rush_fumble', 0),
            stat_data.get('rush_fumble_lost', 0),
            stat_data.get('rec_tgt', 0), stat_data.get('rec', 0), stat_data.get('rec_yd', 0),
            stat_data.get('rec_td', 0), stat_data.get('rec_2pt', 0), stat_data.get('rec_fd', 0),
            stat_data.get('rec_fumble', 0), stat_data.get('rec_fumble_lost', 0),
            stat_data.get('pts_std', 0), stat_data.get('pts_half_ppr', 0), stat_data.get('pts_ppr', 0),
            stat_data.get('st_td', 0), stat_data.get('st_ff', 0), stat_data.get('st_fum_rec', 0),
            stat_data.get('fgm_0_19', 0), stat_data.get('fgm_20_29', 0), stat_data.get('fgm_30_39', 0),
            stat_data.get('fgm_40_49', 0), stat_data.get('fgm_50p', 0), stat_data.get('fgm', 0),
            stat_data.get('fga', 0), stat_data.get('xpm', 0), stat_data.get('xpa', 0),
            str(stat_data.get('metadata'))
        ))
        
        self.conn.commit()
    
    def insert_player_stats_batch(self, stats: List[Dict]):
        """Insert multiple player stats efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                f"{s['player_id']}_{s['season']}_{s['week']}",
                s['player_id'], s['season'], s['week'], s.get('team'), s.get('opponent'),
                s.get('pass_att', 0), s.get('pass_cmp', 0), s.get('pass_yd', 0),
                s.get('pass_td', 0), s.get('pass_int', 0), s.get('pass_2pt', 0),
                s.get('pass_int_td', 0), s.get('pass_fd', 0), s.get('pass_sack', 0),
                s.get('pass_sack_yd', 0),
                s.get('rush_att', 0), s.get('rush_yd', 0), s.get('rush_td', 0),
                s.get('rush_2pt', 0), s.get('rush_fd', 0), s.get('rush_fumble', 0),
                s.get('rush_fumble_lost', 0),
                s.get('rec_tgt', 0), s.get('rec', 0), s.get('rec_yd', 0),
                s.get('rec_td', 0), s.get('rec_2pt', 0), s.get('rec_fd', 0),
                s.get('rec_fumble', 0), s.get('rec_fumble_lost', 0),
                s.get('pts_std', 0), s.get('pts_half_ppr', 0), s.get('pts_ppr', 0),
                s.get('st_td', 0), s.get('st_ff', 0), s.get('st_fum_rec', 0),
                s.get('fgm_0_19', 0), s.get('fgm_20_29', 0), s.get('fgm_30_39', 0),
                s.get('fgm_40_49', 0), s.get('fgm_50p', 0), s.get('fgm', 0),
                s.get('fga', 0), s.get('xpm', 0), s.get('xpa', 0),
                str(s.get('metadata'))
            )
            for s in stats
        ]
        
        cursor.executemany("""
            INSERT INTO player_stats 
            (stat_id, player_id, season, week, team, opponent,
             pass_att, pass_cmp, pass_yd, pass_td, pass_int, pass_2pt, pass_int_td,
             pass_fd, pass_sack, pass_sack_yd,
             rush_att, rush_yd, rush_td, rush_2pt, rush_fd, rush_fumble, rush_fumble_lost,
             rec_tgt, rec, rec_yd, rec_td, rec_2pt, rec_fd, rec_fumble, rec_fumble_lost,
             pts_std, pts_half_ppr, pts_ppr,
             st_td, st_ff, st_fum_rec,
             fgm_0_19, fgm_20_29, fgm_30_39, fgm_40_49, fgm_50p, fgm, fga, xpm, xpa,
             metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id, season, week) DO UPDATE SET
                team = excluded.team,
                opponent = excluded.opponent,
                pass_att = excluded.pass_att,
                pass_cmp = excluded.pass_cmp,
                pass_yd = excluded.pass_yd,
                pass_td = excluded.pass_td,
                pass_int = excluded.pass_int,
                pass_2pt = excluded.pass_2pt,
                pass_int_td = excluded.pass_int_td,
                pass_fd = excluded.pass_fd,
                pass_sack = excluded.pass_sack,
                pass_sack_yd = excluded.pass_sack_yd,
                rush_att = excluded.rush_att,
                rush_yd = excluded.rush_yd,
                rush_td = excluded.rush_td,
                rush_2pt = excluded.rush_2pt,
                rush_fd = excluded.rush_fd,
                rush_fumble = excluded.rush_fumble,
                rush_fumble_lost = excluded.rush_fumble_lost,
                rec_tgt = excluded.rec_tgt,
                rec = excluded.rec,
                rec_yd = excluded.rec_yd,
                rec_td = excluded.rec_td,
                rec_2pt = excluded.rec_2pt,
                rec_fd = excluded.rec_fd,
                rec_fumble = excluded.rec_fumble,
                rec_fumble_lost = excluded.rec_fumble_lost,
                pts_std = excluded.pts_std,
                pts_half_ppr = excluded.pts_half_ppr,
                pts_ppr = excluded.pts_ppr,
                st_td = excluded.st_td,
                st_ff = excluded.st_ff,
                st_fum_rec = excluded.st_fum_rec,
                fgm_0_19 = excluded.fgm_0_19,
                fgm_20_29 = excluded.fgm_20_29,
                fgm_30_39 = excluded.fgm_30_39,
                fgm_40_49 = excluded.fgm_40_49,
                fgm_50p = excluded.fgm_50p,
                fgm = excluded.fgm,
                fga = excluded.fga,
                xpm = excluded.xpm,
                xpa = excluded.xpa,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_player_stats(self, player_id: Optional[str] = None, season: Optional[str] = None,
                        week: Optional[int] = None) -> List[Dict]:
        """Get player stats with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM player_stats WHERE 1=1"
        params = []
        
        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        
        if season:
            query += " AND season = ?"
            params.append(season)
        
        if week is not None:
            query += " AND week = ?"
            params.append(week)
        
        query += " ORDER BY season DESC, week DESC, pts_ppr DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Transaction Methods ====================
    
    def insert_transaction(self, transaction_data: Dict, league_id: str):
        """Insert or update transaction information."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions 
            (transaction_id, league_id, type, status, roster_ids, settings, metadata,
             adds, drops, draft_picks, waiver_budget, creator, created, consenter_ids,
             status_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id) DO UPDATE SET
                status = excluded.status,
                consenter_ids = excluded.consenter_ids,
                status_updated = excluded.status_updated
        """, (
            transaction_data['transaction_id'],
            league_id,
            transaction_data.get('type'),
            transaction_data.get('status'),
            str(transaction_data.get('roster_ids')),
            str(transaction_data.get('settings')),
            str(transaction_data.get('metadata')),
            str(transaction_data.get('adds')),
            str(transaction_data.get('drops')),
            str(transaction_data.get('draft_picks')),
            str(transaction_data.get('waiver_budget')),
            transaction_data.get('creator'),
            transaction_data.get('created'),
            str(transaction_data.get('consenter_ids')),
            transaction_data.get('status_updated')
        ))
        
        self.conn.commit()
    
    def insert_transactions_batch(self, transactions: List[Dict], league_id: str):
        """Insert multiple transactions efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (
                t['transaction_id'], league_id, t.get('type'), t.get('status'),
                str(t.get('roster_ids')), str(t.get('settings')), str(t.get('metadata')),
                str(t.get('adds')), str(t.get('drops')), str(t.get('draft_picks')),
                str(t.get('waiver_budget')), t.get('creator'), t.get('created'),
                str(t.get('consenter_ids')), t.get('status_updated')
            )
            for t in transactions
        ]
        
        cursor.executemany("""
            INSERT INTO transactions 
            (transaction_id, league_id, type, status, roster_ids, settings, metadata,
             adds, drops, draft_picks, waiver_budget, creator, created, consenter_ids,
             status_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id) DO UPDATE SET
                status = excluded.status,
                consenter_ids = excluded.consenter_ids,
                status_updated = excluded.status_updated
        """, data)
        
        self.conn.commit()
    
    def get_transactions(self, league_id: str, transaction_type: Optional[str] = None) -> List[Dict]:
        """Get transactions for a league, optionally filtered by type."""
        cursor = self.conn.cursor()
        
        if transaction_type:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE league_id = ? AND type = ?
                ORDER BY created DESC
            """, (league_id, transaction_type))
        else:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE league_id = ?
                ORDER BY created DESC
            """, (league_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Utility Methods ====================
    
    def clear_league_data(self, league_id: str):
        """Clear all data for a specific league."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM matchups WHERE league_id = ?", (league_id,))
        cursor.execute("DELETE FROM rosters WHERE league_id = ?", (league_id,))
        cursor.execute("DELETE FROM transactions WHERE league_id = ?", (league_id,))
        cursor.execute("DELETE FROM leagues WHERE league_id = ?", (league_id,))
        self.conn.commit()
    
    def clear_all_data(self):
        """Clear all data from all tables."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM matchups")
        cursor.execute("DELETE FROM rosters")
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM leagues")
        cursor.execute("DELETE FROM nfl_players")
        cursor.execute("DELETE FROM nfl_schedules")
        cursor.execute("DELETE FROM player_stats")
        cursor.execute("DELETE FROM transactions")
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    with LeagueDB() as db:
        print("League database initialized successfully!")
        print(f"Database location: {db.db_path}")

