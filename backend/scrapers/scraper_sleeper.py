import time
import re
import sys
import os
import requests
from database import ProjectionsDB
from typing import List, Dict, Optional
import logging

# Fix encoding issues on Windows
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # In Jupyter or other environments where reconfigure is not available
        pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class SleeperScraper:
    """Scraper for Sleeper fantasy projections using their undocumented API."""
    
    def __init__(self, db_path: str = None):
        """Initialize the scraper."""
        self.source = "sleeper.com"
        self.base_url = "https://api.sleeper.app"
        self.db_path = db_path or "projections.db"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _parse_player_name(self, full_name: str) -> tuple[str, str]:
        """
        Parse full name into first and last name.
        
        Args:
            full_name: Full player name (e.g., "Patrick Mahomes")
        
        Returns:
            Tuple of (first_name, last_name)
        """
        if not full_name:
            return "", ""
        
        # Clean any extra whitespace
        full_name = full_name.strip()
        
        name_parts = full_name.split()
        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name
    
    def _get_all_players(self) -> Dict:
        """
        Get all NFL players from Sleeper API.
        This provides player metadata including names and positions.
        
        Returns:
            Dictionary mapping player_id to player info
        """
        print("Fetching all players from Sleeper API...")
        url = f"{self.base_url}/v1/players/nfl"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            players = response.json()
            print(f"  ✓ Loaded {len(players)} players")
            return players
        except Exception as e:
            log.error(f"Failed to fetch players: {e}")
            return {}
    
    def _get_projections(self, season: str, week: str) -> Optional[Dict]:
        """
        Get projections from Sleeper's undocumented API.
        
        Args:
            season: Season year (e.g., "2024")
            week: Week number (e.g., "8")
        
        Returns:
            Dictionary of projections by player_id
        """
        # The working endpoint format includes "regular" season type
        url = f"{self.base_url}/v1/projections/nfl/regular/{season}/{week}"
        
        try:
            print(f"Fetching from: {url}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    print(f"  ✓ Successfully fetched {len(data)} player projections")
                    return data
            else:
                print(f"  ✗ Status {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        log.error("Could not fetch projections")
        return None
    
    def scrape_week_projections(self, week: str = "Week 8", season: str = "2025") -> List[Dict]:
        """
        Scrape projections for a specific week.
        
        Args:
            week: Week string (e.g., "Week 8")
            season: Season year (e.g., "2025")
        
        Returns:
            List of projection dictionaries
        """
        # Extract week number from string like "Week 8"
        week_match = re.search(r'\d+', week)
        week_num = week_match.group() if week_match else "8"
        
        print(f"\nFetching Sleeper projections for {season} Week {week_num}...")
        
        # Get all players first (for metadata)
        players_data = self._get_all_players()
        
        if not players_data:
            log.error("Could not load players data")
            return []
        
        # Get projections
        projections_data = self._get_projections(season, week_num)
        
        if not projections_data:
            log.error("Could not load projections data")
            return []
        
        all_projections = []
        
        print(f"\nParsing {len(projections_data)} projections...")
        
        # Count how many have actual data
        non_empty_count = 0
        
        for player_id, proj_stats in projections_data.items():
            try:
                # Check if projection has any data
                if not proj_stats or len(proj_stats) == 0:
                    continue
                
                non_empty_count += 1
                
                # Get player info
                player_info = players_data.get(player_id)
                
                if not player_info:
                    continue
                
                # Get player details
                full_name = player_info.get('full_name', '')
                position = player_info.get('position', '')
                team = player_info.get('team', '')
                status = player_info.get('status', '')
                active = player_info.get('active', False)
                
                if not full_name or not position:
                    continue
                
                # Skip IDP positions (not used in standard fantasy)
                if position in ['CB', 'DB', 'DE', 'DT', 'LB', 'S', 'SS', 'FS']:
                    continue
                
                # Set team to "FA" for free agents (active players without team)
                if not team and active and status == 'Active':
                    team = 'FA'
                
                # Sleeper provides pts_ppr directly! Use that if available
                projected_points = proj_stats.get('pts_ppr')
                
                # If not available, calculate from component stats
                if projected_points is None:
                    projected_points = self._calculate_fantasy_points(proj_stats, position)
                else:
                    projected_points = float(projected_points)
                
                # Skip players with 0 or very low projections
                if projected_points < 0.1:
                    continue
                
                # Parse name
                first_name, last_name = self._parse_player_name(full_name)
                
                # Remove any numbers from position (just in case)
                position = re.sub(r'\d+', '', position).strip()
                
                projection = {
                    'source': self.source,
                    'week': week,
                    'first_name': first_name,
                    'last_name': last_name,
                    'position': position,
                    'team': team.upper() if team else None,
                    'projected_points': round(projected_points, 1)
                }
                
                all_projections.append(projection)
                
                if projected_points >= 10:  # Only print notable projections
                    print(f"  {first_name} {last_name} ({position}): {projected_points:.1f} pts")
                
            except Exception as e:
                log.warning(f"Error parsing projection for player {player_id}: {e}")
                continue
        
        # Sort by projected points
        all_projections.sort(key=lambda x: x['projected_points'], reverse=True)
        
        print(f"\n✓ Projections with data: {non_empty_count} out of {len(projections_data)}")
        print(f"✓ Total players with valid projections: {len(all_projections)}")
        
        return all_projections
    
    def _calculate_fantasy_points(self, stats: Dict, position: str) -> float:
        """
        Calculate PPR fantasy points from raw stats.
        
        Args:
            stats: Dictionary of player stats
            position: Player position
        
        Returns:
            Calculated fantasy points
        """
        if not stats:
            return 0.0
        
        points = 0.0
        
        try:
            # Passing stats (QB)
            pass_yds = float(stats.get('pass_yd', 0))
            pass_tds = float(stats.get('pass_td', 0))
            interceptions = float(stats.get('pass_int', 0))
            pass_2pt = float(stats.get('pass_2pt', 0))
            
            points += pass_yds * 0.04  # 1 point per 25 yards
            points += pass_tds * 4
            points += interceptions * -2
            points += pass_2pt * 2
            
            # Rushing stats
            rush_yds = float(stats.get('rush_yd', 0))
            rush_tds = float(stats.get('rush_td', 0))
            rush_2pt = float(stats.get('rush_2pt', 0))
            
            points += rush_yds * 0.1  # 1 point per 10 yards
            points += rush_tds * 6
            points += rush_2pt * 2
            
            # Receiving stats (PPR)
            receptions = float(stats.get('rec', 0))
            rec_yds = float(stats.get('rec_yd', 0))
            rec_tds = float(stats.get('rec_td', 0))
            rec_2pt = float(stats.get('rec_2pt', 0))
            
            points += receptions * 1.0  # PPR: 1 point per reception
            points += rec_yds * 0.1  # 1 point per 10 yards
            points += rec_tds * 6
            points += rec_2pt * 2
            
            # Fumbles
            fumbles_lost = float(stats.get('fum_lost', 0))
            points += fumbles_lost * -2
            
        except (ValueError, TypeError) as e:
            log.warning(f"Error calculating points: {e}")
            return 0.0
        
        return points
    
    def scrape_and_save(self, week: str = "Week 8", season: str = "2024"):
        """Scrape projections and save to database."""
        projections = self.scrape_week_projections(week, season)
        
        if projections:
            print(f"\nSaving {len(projections)} projections to database...")
            with ProjectionsDB(db_path=self.db_path) as db:
                db.insert_projections_batch(projections)
            print("✓ Successfully saved to database!")
        else:
            print("No projections found to save.")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()


if __name__ == "__main__":
    # Example usage
    with SleeperScraper() as scraper:
        scraper.scrape_and_save(week="Week 8", season="2024")

