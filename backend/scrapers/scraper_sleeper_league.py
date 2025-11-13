import time
import sys
import os
import requests
from database_league import LeagueDB
from typing import List, Dict, Optional
import logging
import json

# Fix encoding issues on Windows
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class SleeperLeagueScraper:
    """Scraper for Sleeper fantasy league data using their official API."""
    
    def __init__(self, db_path: str = "league.db"):
        """Initialize the scraper."""
        self.base_url = "https://api.sleeper.app"
        self.db_path = db_path  # Store database path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    # ==================== User Methods ====================
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user information by username.
        
        Args:
            username: Sleeper username
        
        Returns:
            User dictionary or None
        """
        url = f"{self.base_url}/v1/user/{username}"
        
        try:
            print(f"Fetching user: {username}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            user = response.json()
            print(f"  ✓ Found user: {user.get('display_name', username)} (ID: {user.get('user_id')})")
            return user
        except Exception as e:
            log.error(f"Failed to fetch user {username}: {e}")
            return None
    
    def get_user_leagues(self, user_id: str, season: str = "2024") -> List[Dict]:
        """
        Get all leagues for a user in a specific season.
        
        Args:
            user_id: Sleeper user ID
            season: Season year (e.g., "2024")
        
        Returns:
            List of league dictionaries
        """
        url = f"{self.base_url}/v1/user/{user_id}/leagues/nfl/{season}"
        
        try:
            print(f"Fetching leagues for user {user_id} in {season}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            leagues = response.json()
            print(f"  ✓ Found {len(leagues)} leagues")
            return leagues
        except Exception as e:
            log.error(f"Failed to fetch leagues: {e}")
            return []
    
    # ==================== League Methods ====================
    
    def get_league(self, league_id: str) -> Optional[Dict]:
        """
        Get detailed league information.
        
        Args:
            league_id: Sleeper league ID
        
        Returns:
            League dictionary or None
        """
        url = f"{self.base_url}/v1/league/{league_id}"
        
        try:
            print(f"Fetching league details: {league_id}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            league = response.json()
            print(f"  ✓ League: {league.get('name')} ({league.get('season')})")
            return league
        except Exception as e:
            log.error(f"Failed to fetch league {league_id}: {e}")
            return None
    
    def get_league_rosters(self, league_id: str) -> List[Dict]:
        """
        Get all rosters/teams in a league.
        
        Args:
            league_id: Sleeper league ID
        
        Returns:
            List of roster dictionaries
        """
        url = f"{self.base_url}/v1/league/{league_id}/rosters"
        
        try:
            print(f"Fetching rosters for league {league_id}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            rosters = response.json()
            print(f"  ✓ Found {len(rosters)} rosters/teams")
            return rosters
        except Exception as e:
            log.error(f"Failed to fetch rosters: {e}")
            return []
    
    def get_league_users(self, league_id: str) -> List[Dict]:
        """
        Get all users/owners in a league.
        
        Args:
            league_id: Sleeper league ID
        
        Returns:
            List of user dictionaries
        """
        url = f"{self.base_url}/v1/league/{league_id}/users"
        
        try:
            print(f"Fetching users for league {league_id}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            users = response.json()
            print(f"  ✓ Found {len(users)} users/owners")
            return users
        except Exception as e:
            log.error(f"Failed to fetch users: {e}")
            return []
    
    def get_league_matchups(self, league_id: str, week: int) -> List[Dict]:
        """
        Get matchups for a specific week.
        
        Args:
            league_id: Sleeper league ID
            week: Week number (1-18)
        
        Returns:
            List of matchup dictionaries
        """
        url = f"{self.base_url}/v1/league/{league_id}/matchups/{week}"
        
        try:
            print(f"Fetching matchups for week {week}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            matchups = response.json()
            
            # Group by matchup_id to show pairs
            matchup_groups = {}
            for m in matchups:
                mid = m.get('matchup_id')
                if mid not in matchup_groups:
                    matchup_groups[mid] = []
                matchup_groups[mid].append(m)
            
            print(f"  ✓ Found {len(matchups)} team matchups ({len(matchup_groups)} games)")
            return matchups
        except Exception as e:
            log.error(f"Failed to fetch matchups for week {week}: {e}")
            return []
    
    def get_league_transactions(self, league_id: str, week: int) -> List[Dict]:
        """
        Get transactions for a specific week.
        
        Args:
            league_id: Sleeper league ID
            week: Week number (1-18)
        
        Returns:
            List of transaction dictionaries
        """
        url = f"{self.base_url}/v1/league/{league_id}/transactions/{week}"
        
        try:
            print(f"Fetching transactions for week {week}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            transactions = response.json()
            print(f"  ✓ Found {len(transactions)} transactions")
            return transactions
        except Exception as e:
            log.error(f"Failed to fetch transactions for week {week}: {e}")
            return []
    
    # ==================== NFL Data Methods ====================
    
    def get_all_nfl_players(self) -> Dict:
        """
        Get all NFL players with comprehensive metadata.
        
        Returns:
            Dictionary mapping player_id to player info
        """
        url = f"{self.base_url}/v1/players/nfl"
        
        try:
            print("Fetching all NFL players (this may take a moment)...")
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            players = response.json()
            print(f"  ✓ Loaded {len(players)} NFL players")
            return players
        except Exception as e:
            log.error(f"Failed to fetch NFL players: {e}")
            return {}
    
    def get_nfl_state(self) -> Optional[Dict]:
        """
        Get current NFL state (current week, season info).
        
        Returns:
            State dictionary or None
        """
        url = f"{self.base_url}/v1/state/nfl"
        
        try:
            print("Fetching NFL state...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            state = response.json()
            print(f"  ✓ Season: {state.get('season')}, Week: {state.get('week')}, Season Type: {state.get('season_type')}")
            return state
        except Exception as e:
            log.error(f"Failed to fetch NFL state: {e}")
            return None
    
    def get_player_stats(self, season: str, week: int) -> Dict:
        """
        Get player stats for a specific week.
        
        Args:
            season: Season year (e.g., "2024")
            week: Week number (1-18)
        
        Returns:
            Dictionary mapping player_id to stats
        """
        url = f"{self.base_url}/v1/stats/nfl/regular/{season}/{week}"
        
        try:
            print(f"Fetching player stats for {season} Week {week}...")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                stats = response.json()
                print(f"  ✓ Loaded stats for {len(stats)} players")
                return stats
            else:
                print(f"  ⚠ No stats available yet (Status: {response.status_code})")
                return {}
        except Exception as e:
            log.error(f"Failed to fetch stats: {e}")
            return {}
    
    # ==================== High-Level Data Fetching ====================
    
    def fetch_all_league_data(self, league_id: str, weeks: Optional[List[int]] = None,
                              include_transactions: bool = False) -> Dict:
        """
        Fetch all data for a league.
        
        Args:
            league_id: Sleeper league ID
            weeks: List of weeks to fetch (default: all played weeks)
            include_transactions: Whether to include transaction history
        
        Returns:
            Dictionary containing all league data
        """
        print(f"\n{'='*70}")
        print(f"FETCHING COMPLETE LEAGUE DATA")
        print(f"{'='*70}\n")
        
        # Get league info
        league = self.get_league(league_id)
        if not league:
            print("❌ Failed to fetch league information")
            return {}
        
        # Get users
        users = self.get_league_users(league_id)
        
        # Get rosters
        rosters = self.get_league_rosters(league_id)
        
        # Determine weeks to fetch
        if weeks is None:
            # Get current NFL state to determine how many weeks have been played
            nfl_state = self.get_nfl_state()
            if nfl_state and nfl_state.get('season_type') == 'regular':
                current_week = nfl_state.get('week', 1)
                # Fetch all weeks up to current week
                weeks = list(range(1, current_week + 1))
            else:
                # Default to first 9 weeks if we can't determine
                weeks = list(range(1, 10))
        
        print(f"\nFetching matchups for weeks: {weeks}")
        
        # Get matchups for all weeks
        all_matchups = {}
        for week in weeks:
            matchups = self.get_league_matchups(league_id, week)
            if matchups:
                all_matchups[week] = matchups
            time.sleep(0.5)  # Be nice to the API
        
        # Get transactions if requested
        all_transactions = {}
        if include_transactions:
            print(f"\nFetching transactions for weeks: {weeks}")
            for week in weeks:
                transactions = self.get_league_transactions(league_id, week)
                if transactions:
                    all_transactions[week] = transactions
                time.sleep(0.5)
        
        print(f"\n{'='*70}")
        print(f"DATA FETCH COMPLETE")
        print(f"{'='*70}")
        print(f"League: {league.get('name')}")
        print(f"Users: {len(users)}")
        print(f"Rosters: {len(rosters)}")
        print(f"Matchups: {sum(len(m) for m in all_matchups.values())} across {len(all_matchups)} weeks")
        if include_transactions:
            print(f"Transactions: {sum(len(t) for t in all_transactions.values())}")
        print(f"{'='*70}\n")
        
        return {
            'league': league,
            'users': users,
            'rosters': rosters,
            'matchups': all_matchups,
            'transactions': all_transactions
        }
    
    def fetch_nfl_players_data(self) -> Dict:
        """
        Fetch comprehensive NFL player data.
        
        Returns:
            Dictionary of player data
        """
        print(f"\n{'='*70}")
        print(f"FETCHING NFL PLAYERS DATA")
        print(f"{'='*70}\n")
        
        players = self.get_all_nfl_players()
        
        print(f"\n{'='*70}")
        print(f"NFL PLAYERS DATA COMPLETE")
        print(f"{'='*70}")
        print(f"Total players: {len(players)}")
        print(f"{'='*70}\n")
        
        return players
    
    def fetch_player_stats_range(self, season: str, start_week: int, end_week: int) -> Dict:
        """
        Fetch player stats for a range of weeks.
        
        Args:
            season: Season year (e.g., "2024")
            start_week: Starting week number
            end_week: Ending week number
        
        Returns:
            Dictionary mapping week to player stats
        """
        print(f"\n{'='*70}")
        print(f"FETCHING PLAYER STATS")
        print(f"{'='*70}\n")
        
        all_stats = {}
        for week in range(start_week, end_week + 1):
            stats = self.get_player_stats(season, week)
            if stats:
                all_stats[week] = stats
            time.sleep(0.5)
        
        print(f"\n{'='*70}")
        print(f"PLAYER STATS COMPLETE")
        print(f"{'='*70}")
        print(f"Weeks fetched: {len(all_stats)}")
        total_stats = sum(len(s) for s in all_stats.values())
        print(f"Total player-week stats: {total_stats}")
        print(f"{'='*70}\n")
        
        return all_stats
    
    # ==================== Database Save Methods ====================
    
    def save_league_data(self, league_id: str, weeks: Optional[List[int]] = None,
                        include_transactions: bool = False):
        """
        Fetch and save complete league data to database.
        
        Args:
            league_id: Sleeper league ID
            weeks: List of weeks to fetch (default: all played weeks)
            include_transactions: Whether to include transaction history
        """
        # Fetch data
        data = self.fetch_all_league_data(league_id, weeks, include_transactions)
        
        if not data or not data.get('league'):
            print("❌ No data to save")
            return
        
        # Save to database
        print("\n💾 Saving to database...")
        
        with LeagueDB(self.db_path) as db:
            # Save league
            league_data = {
                'league_id': data['league']['league_id'],
                'name': data['league']['name'],
                'season': data['league']['season'],
                'season_type': data['league'].get('season_type'),
                'sport': data['league'].get('sport'),
                'status': data['league'].get('status'),
                'total_rosters': data['league'].get('total_rosters'),
                'roster_positions': data['league'].get('roster_positions'),
                'scoring_settings': data['league'].get('scoring_settings'),
                'settings': data['league'].get('settings'),
                'previous_league_id': data['league'].get('previous_league_id'),
                'bracket_id': data['league'].get('bracket_id'),
                'draft_id': data['league'].get('draft_id'),
                'avatar': data['league'].get('avatar')
            }
            db.insert_league(league_data)
            print(f"  ✓ Saved league: {data['league']['name']}")
            
            # Save users
            if data.get('users'):
                db.insert_users_batch(data['users'])
                print(f"  ✓ Saved {len(data['users'])} users")
            
            # Save rosters
            if data.get('rosters'):
                db.insert_rosters_batch(data['rosters'], league_id)
                print(f"  ✓ Saved {len(data['rosters'])} rosters")
            
            # Save matchups
            if data.get('matchups'):
                for week, matchups in data['matchups'].items():
                    db.insert_matchups_batch(matchups, league_id, week)
                total_matchups = sum(len(m) for m in data['matchups'].values())
                print(f"  ✓ Saved {total_matchups} matchups across {len(data['matchups'])} weeks")
            
            # Save transactions
            if include_transactions and data.get('transactions'):
                for week, transactions in data['transactions'].items():
                    db.insert_transactions_batch(transactions, league_id)
                total_trans = sum(len(t) for t in data['transactions'].values())
                print(f"  ✓ Saved {total_trans} transactions")
        
        print("\n✅ League data saved successfully!\n")
    
    def save_nfl_players(self):
        """Fetch and save NFL player data to database."""
        players_dict = self.fetch_nfl_players_data()
        
        if not players_dict:
            print("❌ No player data to save")
            return
        
        print("\n💾 Saving to database...")
        
        # Convert to list format
        players_list = []
        for player_id, player_data in players_dict.items():
            player_data['player_id'] = player_id
            
            # Fix DEF player names (Sleeper doesn't provide them)
            if player_data.get('position') == 'DEF':
                team = player_data.get('team')
                if team and not player_data.get('full_name'):
                    player_data['full_name'] = f"{team} Defense"
                    player_data['first_name'] = team
                    player_data['last_name'] = "Defense"
            
            players_list.append(player_data)
        
        # Filter out IDP positions for fantasy relevance
        # Note: Sleeper uses 'DEF' for team defenses
        fantasy_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF', 'DST']
        fantasy_players = [p for p in players_list if p.get('position') in fantasy_positions]
        
        # Log defense count for debugging
        def_count = sum(1 for p in fantasy_players if p.get('position') in ['DEF', 'DST'])
        if def_count > 0:
            print(f"  ✓ Included {def_count} team defenses")
        
        with LeagueDB(self.db_path) as db:
            db.insert_nfl_players_batch(fantasy_players)
            print(f"  ✓ Saved {len(fantasy_players)} fantasy-relevant players")
        
        print("\n✅ NFL players saved successfully!\n")
    
    def save_player_stats(self, season: str, start_week: int, end_week: int):
        """
        Fetch and save player stats for a range of weeks.
        
        Args:
            season: Season year (e.g., "2024")
            start_week: Starting week number
            end_week: Ending week number
        """
        stats_by_week = self.fetch_player_stats_range(season, start_week, end_week)
        
        if not stats_by_week:
            print("❌ No stats data to save")
            return
        
        print("\n💾 Saving to database...")
        
        all_stats = []
        for week, players_stats in stats_by_week.items():
            for player_id, stats in players_stats.items():
                stat_record = {
                    'player_id': player_id,
                    'season': season,
                    'week': week,
                    **stats  # Include all stat fields
                }
                all_stats.append(stat_record)
        
        with LeagueDB(self.db_path) as db:
            db.insert_player_stats_batch(all_stats)
            print(f"  ✓ Saved {len(all_stats)} player stat records")
        
        print("\n✅ Player stats saved successfully!\n")
    
    def save_nfl_schedule(self, season: str):
        """
        Create NFL schedule with official 2025 bye weeks.
        
        Args:
            season: Season year (e.g., "2025")
        """
        print(f"\n{'='*70}")
        print(f"FETCHING NFL SCHEDULE FOR {season}")
        print(f"{'='*70}\n")
        
        # Official 2025 NFL bye weeks (source: NFL.com, ESPN)
        bye_weeks_2025 = {
            'ATL': 5, 'CHI': 5, 'GB': 5, 'PIT': 5,
            'HOU': 6, 'MIN': 6,
            'BAL': 7, 'BUF': 7,
            'ARI': 8, 'DET': 8, 'JAX': 8, 'LV': 8, 'LAR': 8, 'SEA': 8,
            'CLE': 9, 'NYJ': 9, 'PHI': 9, 'TB': 9,
            'CIN': 10, 'DAL': 10, 'KC': 10, 'TEN': 10,
            'IND': 11, 'NO': 11,
            'DEN': 12, 'LAC': 12, 'MIA': 12, 'WAS': 12,
            'CAR': 14, 'NE': 14, 'NYG': 14, 'SF': 14
        }
        
        print(f"Using official 2025 NFL bye week schedule")
        bye_weeks_found = bye_weeks_2025
        
        # Create schedule records
        schedules = []
        all_teams = list(bye_weeks_2025.keys())
        
        for team in all_teams:
            bye_week = bye_weeks_found.get(team)
            
            for week in range(1, 19):
                is_bye = (week == bye_week)
                
                schedule = {
                    'season': season,
                    'week': week,
                    'team': team,
                    'opponent': None,
                    'is_home': None,
                    'is_bye': is_bye,
                    'game_date': None,
                    'game_time': None,
                    'metadata': None
                }
                schedules.append(schedule)
        
        # Save to database
        print("\n💾 Saving schedule to database...")
        with LeagueDB(self.db_path) as db:
            db.insert_schedules_batch(schedules)
            print(f"  ✓ Saved {len(schedules)} schedule records")
        
        print(f"\n✅ NFL schedule saved successfully!")
        print(f"Bye weeks detected for {len(bye_weeks_found)} teams:\n")
        
        # Group by week for display
        weeks_dict = {}
        for team, week in bye_weeks_found.items():
            if week not in weeks_dict:
                weeks_dict[week] = []
            weeks_dict[week].append(team)
        
        for week in sorted(weeks_dict.keys()):
            teams = sorted(weeks_dict[week])
            print(f"  Week {week:2}: {', '.join(teams)}")
        
        # Verify specific teams mentioned by user
        if 'DET' in bye_weeks_found:
            print(f"\n✓ Lions bye week: Week {bye_weeks_found['DET']}")
        if 'MIA' in bye_weeks_found:
            print(f"✓ Dolphins bye week: Week {bye_weeks_found['MIA']}")
        
        print(f"\n{'='*70}\n")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()


if __name__ == "__main__":
    # Example usage
    with SleeperLeagueScraper() as scraper:
        # Get user and their leagues
        username = input("Enter your Sleeper username: ")
        user = scraper.get_user(username)
        
        if user:
            user_id = user['user_id']
            leagues = scraper.get_user_leagues(user_id, "2024")
            
            if leagues:
                print("\nYour leagues:")
                for i, league in enumerate(leagues, 1):
                    print(f"{i}. {league['name']} (ID: {league['league_id']})")
                
                # Let user select a league
                choice = int(input("\nSelect a league number: ")) - 1
                selected_league = leagues[choice]
                
                # Fetch and save league data
                scraper.save_league_data(
                    league_id=selected_league['league_id'],
                    weeks=None,  # Auto-detect played weeks
                    include_transactions=True
                )
                
                # Save NFL players
                scraper.save_nfl_players()
                
                # Save player stats (weeks 1-9)
                scraper.save_player_stats("2024", 1, 9)
                
                # Save NFL schedule
                scraper.save_nfl_schedule("2024")

