import time
import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from .database import ProjectionsDB
from typing import List, Dict
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


class ESPNScraper:
    """Scraper for ESPN fantasy projections."""
    
    def __init__(self, headless: bool = True, db_path: str = None):
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
        self.db_path = db_path or "backend/data/databases/projections.db"
    
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
        
        ESPN uses THREE separate tables:
        - Table 0 (fixed-left): Player names with team/position
        - Table 1 (scrollable): Stats (passing, rushing, receiving)
        - Table 2 (fixed-right): FPTS column only
        
        Args:
            position_filter: Position to filter (QB, RB, WR, TE, K, D/ST)
            week: Week string
        
        Returns:
            List of projections for this position
        """
        projections = []
        
        try:
            # ESPN's position filters are VERY flaky
            # APPROACH: Reload page fresh, go to Sortable, try filter multiple ways
            print(f"\n  [{position_filter}] Loading fresh page and applying filter...", flush=True)
            
            # Step 1: Reload page to get a fresh state
            self.driver.get(self.url)
            time.sleep(3)
            
            # Step 2: Click Sortable Projections first
            try:
                sortable_btn = self.driver.find_element(By.XPATH, 
                    "//button[contains(.,'Sortable Projections')]")
                self.driver.execute_script("arguments[0].click();", sortable_btn)
                print(f"    → Switched to Sortable Projections", flush=True)
                time.sleep(2)
            except:
                pass
            
            # Step 3: Click the position filter with multiple attempts and verification
            filter_worked = False
            expected_pos = position_filter if position_filter != 'D/ST' else 'DST'
            
            click_script = f"""
                const elements = document.querySelectorAll('*');
                for (const el of elements) {{
                    if (el.innerText?.trim() === '{position_filter}' && 
                        el.children.length === 0 && 
                        !el.closest('table') &&
                        el.offsetParent !== null) {{
                        const rect = el.getBoundingClientRect();
                        if (rect.top < 600 && rect.top > 50) {{
                            el.click();
                            return true;
                        }}
                    }}
                }}
                return false;
            """
            
            verify_script = f"""
                const leftTable = document.querySelector('table.Table--fixed-left');
                if (!leftTable) return null;
                const rows = leftTable.querySelectorAll('tbody tr');
                const positions = [];
                for (let i = 0; i < Math.min(5, rows.length); i++) {{
                    const cell = rows[i].querySelector('td');
                    if (cell) {{
                        const text = cell.innerText.replace(/\\n/g, ' ').toUpperCase();
                        const posMatch = text.match(/\\b(QB|RB|WR|TE|K|DST|D\\/ST|DEF)\\b/);
                        if (posMatch) positions.push(posMatch[1]);
                    }}
                }}
                return positions;
            """
            
            # Try up to 5 attempts to get the filter working
            for attempt in range(5):
                print(f"    → Filter attempt {attempt + 1}/5...", flush=True)
                
                # Try clicking the filter
                try:
                    self.driver.execute_script(click_script)
                except:
                    pass
                
                # Also try XPath
                try:
                    xpath = f"//*[normalize-space(text())='{position_filter}' and not(ancestor::table)]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        try:
                            rect = self.driver.execute_script(
                                "var r = arguments[0].getBoundingClientRect(); return {top: r.top};", elem)
                            if rect and rect.get('top', 1000) < 600:
                                self.driver.execute_script("arguments[0].click();", elem)
                                break
                        except:
                            continue
                except:
                    pass
                
                time.sleep(2)
                
                # Verify the filter worked
                try:
                    detected = self.driver.execute_script(verify_script)
                    if detected:
                        expected_variants = [expected_pos]
                        if expected_pos == 'DST':
                            expected_variants = ['DST', 'D/ST', 'DEF']
                        
                        matches = sum(1 for p in detected if p in expected_variants)
                        if matches >= 2 or (matches >= 1 and len(detected) <= 2):
                            print(f"    ✓ Filter verified: {detected[:3]}", flush=True)
                            filter_worked = True
                            break
                        else:
                            print(f"    ✗ Wrong positions: {detected[:3]}", flush=True)
                except:
                    pass
                
                # If filter didn't work, try the Full -> Sortable dance
                if attempt == 2:
                    print(f"    → Trying Full Projections workaround...", flush=True)
                    try:
                        full_btn = self.driver.find_element(By.XPATH, "//button[contains(.,'Full Projections')]")
                        self.driver.execute_script("arguments[0].click();", full_btn)
                        time.sleep(1.5)
                        self.driver.execute_script(click_script)
                        time.sleep(1)
                        sortable_btn = self.driver.find_element(By.XPATH, "//button[contains(.,'Sortable Projections')]")
                        self.driver.execute_script("arguments[0].click();", sortable_btn)
                        time.sleep(2)
                    except:
                        pass
            
            if not filter_worked:
                print(f"    ⚠ Could not filter to {position_filter} after 5 attempts - SKIPPING", flush=True)
                return []
            
            # ESPN uses 3 tables: left-fixed (player), middle (stats), right-fixed (FPTS)
            # Find tables by their class names
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            if len(tables) < 2:
                print(f"    No tables found", flush=True)
                return projections
            
            print(f"    Found {len(tables)} tables", flush=True)
            
            # Identify tables by class
            left_table = None   # Player names
            right_table = None  # FPTS values
            
            for table in tables:
                table_class = table.get_attribute('class') or ''
                if 'fixed-left' in table_class:
                    left_table = table
                elif 'fixed-right' in table_class:
                    right_table = table
            
            # Fallback: first table is players, last table might have FPTS
            if not left_table:
                left_table = tables[0]
            if not right_table and len(tables) >= 3:
                right_table = tables[-1]
            
            if not left_table:
                print(f"    Could not find player table", flush=True)
                return projections
            
            # Get player rows from left table
            player_rows = left_table.find_elements(By.CSS_SELECTOR, "tbody tr")
            print(f"    Found {len(player_rows)} player rows", flush=True)
            
            # Get FPTS rows from right table (if exists)
            fpts_rows = []
            if right_table:
                fpts_rows = right_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                print(f"    Found {len(fpts_rows)} FPTS rows", flush=True)
            
            # Scrape each player
            for idx, player_row in enumerate(player_rows):
                try:
                    # Get player info from left table
                    player_cell = player_row.find_element(By.CSS_SELECTOR, "td")
                    cell_text = player_cell.text.strip()
                    
                    if not cell_text:
                        continue
                    
                    # Parse: "Josh Allen\nBuf QB" or "Josh Allen Buf QB"
                    lines = cell_text.replace('\n', ' ').split()
                    
                    # Find player name (words before team abbreviation)
                    player_name_parts = []
                    team_abbr = None
                    detected_position = None
                    
                    for word in lines:
                        word_upper = word.upper().strip()
                        # Check if this is a team abbreviation (2-4 letters, specific known teams)
                        if word_upper in ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 
                                         'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 
                                         'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 
                                         'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS', 'WSH', 'FA']:
                            team_abbr = word_upper
                            if team_abbr == 'WSH':
                                team_abbr = 'WAS'
                        # Check if this is a position
                        elif word_upper in ['QB', 'RB', 'WR', 'TE', 'K', 'DST', 'D/ST', 'DEF']:
                            detected_position = word_upper
                        # Otherwise it's part of the player name
                        elif len(word) > 1:  # Skip single characters
                            player_name_parts.append(word)
                    
                    player_name = ' '.join(player_name_parts)
                    
                    if not player_name:
                        continue
                    
                    # Get FPTS from right table
                    projected_points = None
                    
                    if fpts_rows and idx < len(fpts_rows):
                        try:
                            fpts_cells = fpts_rows[idx].find_elements(By.TAG_NAME, "td")
                            # The right-fixed table typically has just 1 cell with FPTS
                            # or FPTS is the last cell
                            if fpts_cells:
                                fpts_text = fpts_cells[-1].text.strip()
                                if fpts_text and fpts_text not in ['-', '--', 'N/A', '']:
                                    projected_points = float(fpts_text)
                        except (ValueError, IndexError) as e:
                            pass
                    
                    # Skip if no valid FPTS
                    if projected_points is None:
                        continue
                    
                    # Validate reasonable range (0-60 for weekly projections)
                    if not (0 <= projected_points <= 60):
                        continue
                    
                    # IMPORTANT: Verify the player's actual position matches what we're scraping
                    # This prevents saving wrong data if the filter click didn't work
                    expected_pos = 'DST' if position_filter == 'D/ST' else position_filter
                    if detected_position:
                        actual_pos = 'DST' if detected_position in ['D/ST', 'DST', 'DEF'] else detected_position
                        if actual_pos != expected_pos:
                            # Position mismatch - skip this player
                            continue
                    
                    # Parse name
                    first_name, last_name = self._parse_player_name(player_name, position_filter)
                    
                    if first_name or last_name:
                        projection = {
                            'source': self.source,
                            'week': week,
                            'first_name': first_name,
                            'last_name': last_name,
                            'position': expected_pos,
                            'team': team_abbr,
                            'projected_points': round(projected_points, 1)
                        }
                        projections.append(projection)
                        
                        team_str = f" ({team_abbr})" if team_abbr else ""
                        print(f"      {len(projections):3}. {first_name} {last_name}{team_str}: {projected_points:.1f} pts", flush=True)
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"    ✗ Error scraping {position_filter}: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        print(f"    ✓ Total {len(projections)} {position_filter} projections", flush=True)
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
            with ProjectionsDB(db_path=self.db_path) as db:
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

