import time
import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from database import ProjectionsDB
from typing import List, Dict

# Fix encoding issues on Windows
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class FantasyProsScraper:
    """Scraper for FantasyPros consensus rankings."""
    
    def __init__(self, headless: bool = True):
        """Initialize the scraper with Chrome options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.source = "fantasypros.com"
        
        # Position pages (PPR for skill positions, standard for others)
        self.position_urls = {
            'QB': 'https://www.fantasypros.com/nfl/rankings/qb.php',
            'RB': 'https://www.fantasypros.com/nfl/rankings/ppr-rb.php',
            'WR': 'https://www.fantasypros.com/nfl/rankings/ppr-wr.php',
            'TE': 'https://www.fantasypros.com/nfl/rankings/ppr-te.php',
            'K': 'https://www.fantasypros.com/nfl/rankings/k.php',
            'DST': 'https://www.fantasypros.com/nfl/rankings/dst.php',
        }
    
    def _parse_player_name(self, full_name: str, position: str) -> tuple[str, str]:
        """
        Parse player name into first and last name.
        
        Args:
            full_name: Full player name (e.g., "Patrick Mahomes II")
            position: Player position (for special handling of DST)
        
        Returns:
            Tuple of (first_name, last_name)
        """
        if not full_name:
            return "", ""
        
        # Clean injury designations and team info
        full_name = re.sub(r'\s*\([^)]*\)\s*', '', full_name).strip()
        
        # DST names are team names
        if position == 'DST':
            return full_name, "Defense"
        
        name_parts = full_name.split()
        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name
    
    def _scrape_position(self, position: str, url: str) -> List[Dict]:
        """
        Scrape rankings for a specific position.
        
        Args:
            position: Position abbreviation (QB, RB, WR, TE, K, DST)
            url: URL to scrape
        
        Returns:
            List of player projections
        """
        print(f"\nScraping {position} from {url}...")
        self.driver.get(url)
        time.sleep(3)
        
        projections = []
        
        try:
            # Wait for table to load
            table = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table, table#rank-data, table.rankings-table, table"))
            )
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"  Found {len(rows)} rows")
            
            for row in rows[1:]:  # Skip header
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue
                    
                    # FantasyPros structure:
                    # Cell 0: Rank
                    # Cell 2: Player Name (with team)
                    # Cell 8: PROJ. FPTS
                    
                    rank_text = cells[0].text.strip()
                    if not rank_text or not rank_text[0].isdigit():
                        continue
                    
                    # Extract player name from cell 2
                    player_name = cells[2].text.strip() if len(cells) > 2 else ""
                    if not player_name:
                        continue
                    
                    # Extract team from player name (format: "Name (TEAM)" or "Name TEAM")
                    team = None
                    team_match = re.search(r'\(([A-Z]{2,3})\)', player_name)
                    if team_match:
                        team = team_match.group(1)
                        # Remove team from player name
                        player_name = re.sub(r'\s*\([A-Z]{2,3}\)', '', player_name).strip()
                    
                    # Extract projected points from cell 8
                    projected_points = None
                    if len(cells) > 8:
                        proj_text = cells[8].text.strip()
                        try:
                            projected_points = float(proj_text)
                        except ValueError:
                            pass
                    
                    # If no projected points found, estimate from rank
                    if projected_points is None:
                        rank = int(rank_text)
                        projected_points = self._estimate_points_from_rank(rank, position)
                    
                    # Parse name
                    first_name, last_name = self._parse_player_name(player_name, position)
                    
                    if first_name or last_name:
                        projection = {
                            'source': self.source,
                            'week': 'Week 8',  # FantasyPros shows current week
                            'first_name': first_name,
                            'last_name': last_name,
                            'position': position,
                            'team': team,
                            'projected_points': round(projected_points, 1)
                        }
                        
                        projections.append(projection)
                        
                        if projected_points >= 10:  # Only print notable projections
                            print(f"  {first_name} {last_name} ({position}): {projected_points:.1f} pts")
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"  ✗ Error scraping {position}: {e}")
        
        print(f"  ✓ Scraped {len(projections)} {position} projections")
        return projections
    
    def _estimate_points_from_rank(self, rank: int, position: str) -> float:
        """
        Estimate projected points based on rank and position.
        This is a fallback when actual projections aren't available.
        """
        # Base points by position (for rank 1)
        base_points = {
            'QB': 25.0,
            'RB': 20.0,
            'WR': 18.0,
            'TE': 14.0,
            'K': 10.0,
            'DST': 10.0,
        }
        
        # Decay factor (how much points drop per rank)
        decay = {
            'QB': 0.5,
            'RB': 0.4,
            'WR': 0.35,
            'TE': 0.3,
            'K': 0.2,
            'DST': 0.25,
        }
        
        base = base_points.get(position, 15.0)
        decay_rate = decay.get(position, 0.3)
        
        # Calculate estimated points with diminishing returns
        estimated = base - (decay_rate * (rank - 1))
        
        # Set minimum at 1.0 point
        return max(1.0, estimated)
    
    def scrape_week_projections(self, week: str = "Week 8") -> List[Dict]:
        """
        Scrape projections for all positions.
        
        Args:
            week: Week string (e.g., "Week 8") - FantasyPros always shows current week
        
        Returns:
            List of projection dictionaries
        """
        print(f"\nFetching FantasyPros consensus rankings for {week}...")
        
        all_projections = []
        
        for position, url in self.position_urls.items():
            position_projs = self._scrape_position(position, url)
            all_projections.extend(position_projs)
            time.sleep(2)  # Be respectful with rate limiting
        
        print(f"\n✓ Total players scraped: {len(all_projections)}")
        return all_projections
    
    def scrape_and_save(self, week: str = "Week 8"):
        """Scrape projections and save to database."""
        projections = self.scrape_week_projections(week)
        
        if projections:
            print(f"\nSaving {len(projections)} projections to database...")
            with ProjectionsDB() as db:
                db.insert_projections_batch(projections)
            print("✓ Successfully saved to database!")
        else:
            print("No projections found to save.")
    
    def close(self):
        """Close the browser."""
        self.driver.quit()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    with FantasyProsScraper(headless=False) as scraper:
        scraper.scrape_and_save(week="Week 8")

