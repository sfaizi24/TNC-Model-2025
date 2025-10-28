import time
import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from database import ProjectionsDB
from typing import List, Dict
import logging

# Fix encoding issues on Windows
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class ESPNScraper:
    """Scraper for ESPN fantasy projections."""
    
    def __init__(self, headless: bool = True):
        """Initialize the scraper with Chrome options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.source = "espn.com"
        self.url = "https://fantasy.espn.com/football/players/projections"
    
    def _map_team_name(self, team_name: str) -> str:
        """
        Map ESPN team names to 3-letter abbreviations.
        
        Args:
            team_name: ESPN team name (e.g., "Falcons", "Chiefs")
        
        Returns:
            3-letter team code in uppercase
        """
        team_map = {
            'Cardinals': 'ARI', 'Falcons': 'ATL', 'Ravens': 'BAL', 'Bills': 'BUF',
            'Panthers': 'CAR', 'Bears': 'CHI', 'Bengals': 'CIN', 'Browns': 'CLE',
            'Cowboys': 'DAL', 'Broncos': 'DEN', 'Lions': 'DET', 'Packers': 'GB',
            'Texans': 'HOU', 'Colts': 'IND', 'Jaguars': 'JAX', 'Chiefs': 'KC',
            'Raiders': 'LV', 'Chargers': 'LAC', 'Rams': 'LAR', 'Dolphins': 'MIA',
            'Vikings': 'MIN', 'Patriots': 'NE', 'Saints': 'NO', 'Giants': 'NYG',
            'Jets': 'NYJ', 'Eagles': 'PHI', 'Steelers': 'PIT', '49ers': 'SF',
            'Seahawks': 'SEA', 'Buccaneers': 'TB', 'Titans': 'TEN', 'Commanders': 'WAS',
        }
        
        return team_map.get(team_name, team_name[:3].upper() if team_name else None)
    
    def _parse_player_name(self, full_name: str, position: str) -> tuple[str, str]:
        """
        Parse full name into first and last name.
        
        Args:
            full_name: Full player name
            position: Player position (for special handling of D/ST)
        
        Returns:
            Tuple of (first_name, last_name)
        """
        if not full_name:
            return "", ""
        
        # D/ST names are team names
        if position in ['D/ST', 'DST']:
            return full_name, "Defense"
        
        # Clean team abbreviations and whitespace
        full_name = re.sub(r'[A-Z]{2,3}$', '', full_name).strip()
        
        name_parts = full_name.split()
        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name
    
    def _scrape_position(self, position_filter: str, week: str) -> List[Dict]:
        """
        Scrape projections for a specific position.
        
        Args:
            position_filter: Position to filter (QB, RB, WR, TE, K, D/ST)
            week: Week string
        
        Returns:
            List of projections for this position
        """
        projections = []
        
        try:
            # Click the position filter (they're <label> elements)
            print(f"\n  Filtering to {position_filter}...")
            position_labels = self.driver.find_elements(By.XPATH, 
                f"//label[@class='control control--radio picker-option' and text()='{position_filter}']")
            
            if position_labels:
                # Use JavaScript click to avoid click interception
                self.driver.execute_script("arguments[0].click();", position_labels[0])
                time.sleep(3)  # Wait for table to reload
                print(f"    ✓ Filtered to {position_filter}")
            else:
                print(f"    ⚠ Could not find {position_filter} filter")
            
            # Wait for table to fully load
            time.sleep(2)
            
            # ESPN has 3 tables: Players (table 0), Stats (table 1), FPTS (table 2)
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            if len(tables) < 3:
                print(f"    Expected 3 tables, found {len(tables)}")
                return projections
            
            players_table = tables[0]
            fpts_table = tables[2]  # This has the FPTS column!
            
            player_rows = players_table.find_elements(By.CSS_SELECTOR, "tbody tr")
            fpts_rows = fpts_table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            print(f"    Found {len(player_rows)} players")
            
            # Parse both tables simultaneously (same row index = same player)
            for idx in range(min(len(player_rows), len(fpts_rows))):
                try:
                    # Get player info from table 0
                    player_row = player_rows[idx]
                    player_cells = player_row.find_elements(By.TAG_NAME, "td")
                    
                    if len(player_cells) < 2:
                        continue
                    
                    player_cell_text = player_cells[1].text.strip()
                    
                    if not player_cell_text:
                        continue
                    
                    # Parse player info - format: "PlayerName\nTeam\nPosition"
                    player_lines = player_cell_text.split('\n')
                    player_name = player_lines[0].strip() if len(player_lines) > 0 else ""
                    team_abbr = player_lines[1].strip().upper() if len(player_lines) > 1 else None
                    position = player_lines[2].strip() if len(player_lines) > 2 else position_filter
                    
                    if not player_name:
                        continue
                    
                    # Get projected points from table 2 (FPTS table), same row index
                    fpts_row = fpts_rows[idx]
                    fpts_cells = fpts_row.find_elements(By.TAG_NAME, "td")
                    
                    if len(fpts_cells) < 1:
                        continue
                    
                    # FPTS is in the only cell of table 2
                    proj_text = fpts_cells[0].text.strip()
                    
                    # Handle missing values (--, -, N/A, etc.) as 0.0
                    if not proj_text or proj_text in ['-', '--', 'N/A', '']:
                        proj_text = "0.0"
                    
                    try:
                        projected_points = float(proj_text)
                        
                        if projected_points >= 0.1:
                            # Parse name
                            first_name, last_name = self._parse_player_name(player_name, position)
                            
                            if first_name or last_name:
                                projection = {
                                    'source': self.source,
                                    'week': week,
                                    'first_name': first_name,
                                    'last_name': last_name,
                                    'position': position,
                                    'team': team_abbr,
                                    'projected_points': round(projected_points, 1)
                                }
                                
                                projections.append(projection)
                                
                                if projected_points >= 10:
                                    team_str = f" ({team_abbr})" if team_abbr else ""
                                    print(f"      {first_name} {last_name}{team_str}: {projected_points:.1f} pts")
                    
                    except ValueError:
                        # If can't convert to float, skip
                        pass
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"    ✗ Error scraping {position_filter}: {e}")
        
        return projections
    
    def scrape_week_projections(self, week: str = "Week 8", season: str = "2024") -> List[Dict]:
        """
        Scrape projections for a specific week.
        
        Args:
            week: Week string (e.g., "Week 8")
            season: Season year (e.g., "2024")
        
        Returns:
            List of projection dictionaries
        """
        print(f"\nFetching ESPN projections for {week}...")
        print(f"Navigating to {self.url}...")
        
        self.driver.get(self.url)
        time.sleep(5)
        
        # Click "Sortable Projections" button
        try:
            print("Clicking 'Sortable Projections' view...")
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            for button in all_buttons:
                if button.text.strip() == "Sortable Projections":
                    button.click()
                    time.sleep(4)  # Give it time to load
                    print("  ✓ Switched to Sortable Projections view")
                    break
        except Exception as e:
            print(f"  Could not switch to Sortable view: {e}")
        
        # Set scoring to PPR
        try:
            print("Setting scoring to Points PPR...")
            time.sleep(2)  # Wait for dropdowns to be ready
            dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
            
            # Find the scoring dropdown
            for dropdown in dropdowns:
                options = dropdown.find_elements(By.TAG_NAME, "option")
                for option in options:
                    if "PPR" in option.text:
                        select = Select(dropdown)
                        select.select_by_visible_text(option.text)
                        print(f"  ✓ Set to {option.text}")
                        time.sleep(3)  # Wait for table to reload
                        break
        except Exception as e:
            print(f"  Could not set PPR: {e}")
        
        # Set to "This Week" view
        try:
            print("Setting to This Week projections...")
            dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
            
            for dropdown in dropdowns:
                options = dropdown.find_elements(By.TAG_NAME, "option")
                for option in options:
                    if "This Week" in option.text:
                        select = Select(dropdown)
                        select.select_by_visible_text(option.text)
                        print(f"  ✓ Set to {option.text}")
                        time.sleep(3)  # Wait for table to reload
                        break
        except Exception as e:
            print(f"  Could not set week view: {e}")
        
        # Scrape each position separately to get 50 per position
        all_projections = []
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']
        
        print(f"\nScraping {len(positions)} positions (up to 50 players each)...")
        
        for position_filter in positions:
            position_projs = self._scrape_position(position_filter, week)
            all_projections.extend(position_projs)
            print(f"    ✓ Scraped {len(position_projs)} {position_filter} projections")
        
        print(f"\n✓ Total players with valid projections: {len(all_projections)}")
        
        return all_projections
    
    def scrape_and_save(self, week: str = "Week 8", season: str = "2024"):
        """Scrape projections and save to database."""
        projections = self.scrape_week_projections(week, season)
        
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
    with ESPNScraper(headless=False) as scraper:
        scraper.scrape_and_save(week="Week 8", season="2024")

