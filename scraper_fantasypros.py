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
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # In Jupyter or other environments where reconfigure is not available
        pass


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
        
        # Clean injury designations and team info in parentheses
        full_name = re.sub(r'\s*\([^)]*\)\s*', '', full_name).strip()
        
        # Remove injury designations stuck to end of names (Q, IR, O, etc.)
        full_name = re.sub(r'(Q|O|D|IR|PUP|SSPD|COV|IA)$', '', full_name).strip()
        
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
        teams_found = 0
        
        try:
            # Wait for table to load
            table = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table, table#rank-data, table.rankings-table, table"))
            )
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"  Found {len(rows)} rows")
            
            # Check header to find team column
            header_row = rows[0] if rows else None
            team_col_idx = None
            if header_row:
                header_cells = header_row.find_elements(By.TAG_NAME, "th")
                for idx, cell in enumerate(header_cells):
                    if 'TEAM' in cell.text.upper() or cell.text.strip().upper() == 'OPP':
                        team_col_idx = idx
                        print(f"  Found team column at index {idx}")
                        break
            
            for row_idx, row in enumerate(rows[1:], 1):  # Skip header
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue
                    
                    # FantasyPros structure:
                    # Cell 0: Rank
                    # Cell 2: Player Name (with team)
                    # Cell 3: Sometimes team column
                    # Cell 8 or later: PROJ. FPTS
                    
                    rank_text = cells[0].text.strip()
                    if not rank_text or not rank_text[0].isdigit():
                        continue
                    
                    # Extract player name from cell 2
                    player_name_raw = cells[2].text.strip() if len(cells) > 2 else ""
                    if not player_name_raw:
                        continue
                    
                    # Clean injury designations and status tags stuck to names
                    # Examples: "Breece HallQ", "Carson WentzIR", "Alvin KamaraO"
                    player_name = player_name_raw
                    player_name = re.sub(r'(Q|O|D|IR|PUP|SSPD|COV)$', '', player_name).strip()
                    
                    # Debug: Print only if raw name differs from cleaned (injury designation removed)
                    if player_name_raw != player_name:
                        print(f"\n  DEBUG: Cleaned '{player_name_raw}' → '{player_name}'")
                    
                    # Strategy 1: Extract team from player name (format: "Name (TEAM)")
                    team = None
                    team_match = re.search(r'\(([A-Z]{2,3})\)', player_name)
                    if team_match:
                        team = team_match.group(1)
                        # Remove team from player name
                        player_name = re.sub(r'\s*\([A-Z]{2,3}\)', '', player_name).strip()
                    
                    # Strategy 2: Check for dedicated team column
                    if not team and team_col_idx is not None and len(cells) > team_col_idx:
                        team_text = cells[team_col_idx].text.strip()
                        # Extract just the team code (might be "KC" or "KC vs DEN" format)
                        team_match = re.search(r'\b([A-Z]{2,3})\b', team_text)
                        if team_match:
                            team = team_match.group(1)
                    
                    # Strategy 3: Check cell 3 for team (common layout)
                    if not team and len(cells) > 3:
                        cell3_text = cells[3].text.strip()
                        # Look for 2-3 uppercase letters
                        if re.match(r'^[A-Z]{2,3}$', cell3_text):
                            team = cell3_text
                        # Or matchup format like "KC vs DEN" or "@KC"
                        elif re.search(r'\b([A-Z]{2,3})\b', cell3_text):
                            team_match = re.search(r'\b([A-Z]{2,3})\b', cell3_text)
                            if team_match:
                                team = team_match.group(1)
                    
                    # Strategy 4: Look in the player cell for more formats
                    if not team:
                        # Try to find team anywhere in player cell (e.g., "Name - TEAM")
                        full_cell_text = cells[2].text
                        team_patterns = [
                            r'\s+-\s+([A-Z]{2,3})\b',  # "Name - KC"
                            r'\s+([A-Z]{2,3})\s+\w{2}$',  # "Name KC RB"
                            r'^([A-Z]{2,3})\s+-',  # "KC - Name"
                        ]
                        for pattern in team_patterns:
                            match = re.search(pattern, full_cell_text)
                            if match:
                                team = match.group(1)
                                break
                    
                    if team:
                        teams_found += 1
                    
                    # Extract projected points from cell 8 or search for it
                    projected_points = None
                    for i in range(8, len(cells)):
                        proj_text = cells[i].text.strip()
                        try:
                            projected_points = float(proj_text)
                            break
                        except ValueError:
                            continue
                    
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
                            team_str = f" ({team})" if team else ""
                            print(f"  {first_name} {last_name}{team_str}: {projected_points:.1f} pts")
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"  ✗ Error scraping {position}: {e}")
        
        team_percentage = (teams_found / len(projections) * 100) if projections else 0
        print(f"  ✓ Scraped {len(projections)} {position} projections")
        print(f"  ✓ Team data found: {teams_found}/{len(projections)} ({team_percentage:.1f}%)")
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

