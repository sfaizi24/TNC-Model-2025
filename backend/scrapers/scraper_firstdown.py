import time
import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .database import ProjectionsDB
from typing import List, Dict

# Fix encoding issues on Windows
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # In Jupyter or other environments where reconfigure is not available
        pass

class FirstDownStudioScraper:
    """Scraper for First Down Studio fantasy projections."""
    
    def __init__(self, headless: bool = True, db_path: str = None):
        """Initialize the scraper with Chrome options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.source = "firstdown.studio"
        self.db_path = db_path or "backend/data/databases/projections.db"
    
    def scrape_week_projections(self, week: str = "Week 8", scoring: str = "PPR") -> List[Dict]:
        """
        Scrape projections for a specific week.
        
        The site now uses separate URL paths for each position:
        - /rankings/qb, /rankings/rb, /rankings/wr, /rankings/te, /rankings/flex, /rankings/k
        
        Args:
            week: Week to scrape (e.g., "Week 8")
            scoring: Scoring format - "PPR", "Half PPR", or "Standard"
        
        Returns:
            List of projection dictionaries
        """
        base_url = "https://www.firstdown.studio/rankings"
        
        all_projections = []
        
        # Position pages to scrape - each has its own URL
        # QB, RB, WR, TE all have "Proj. Pts" column we can use directly
        positions = ["qb", "rb", "wr", "te", "k"]
        
        for position in positions:
            url = f"{base_url}/{position}"
            print(f"\nScraping {position.upper()} from {url}...")
            
            try:
                self.driver.get(url)
                time.sleep(3)
                
                # Wait for table to load
                table = self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                # Get header row to find column indices
                # Headers are in thead > tr > cell elements
                try:
                    header_cells = table.find_elements(By.CSS_SELECTOR, "thead tr th, thead tr td")
                    if not header_cells:
                        header_cells = table.find_element(By.TAG_NAME, "tr").find_elements(By.TAG_NAME, "th")
                    headers = [cell.text.strip() for cell in header_cells]
                except:
                    # Fallback: get first row
                    first_row = table.find_element(By.TAG_NAME, "tr")
                    headers = [cell.text.strip() for cell in first_row.find_elements(By.TAG_NAME, "th")]
                
                print(f"  Headers: {headers}")
                
                # Find points column index
                # Most positions use "Proj. Pts", but kickers use "Kicking Pts"
                proj_pts_idx = None
                for idx, header in enumerate(headers):
                    header_lower = header.lower()
                    if ("proj" in header_lower and "pts" in header_lower) or \
                       ("kicking" in header_lower and "pts" in header_lower):
                        proj_pts_idx = idx
                        break
                
                if proj_pts_idx is None:
                    print(f"  ⚠ Could not find points column, skipping {position.upper()}")
                    continue
                
                print(f"  Found points column at index {proj_pts_idx}")
                
                # Get all data rows from tbody
                try:
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                except:
                    rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
                
                print(f"  Found {len(rows)} player rows")
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 3:
                            continue
                        
                        # Cell structure:
                        # Cell 0: Rank (e.g., "1" or "3(+3)")
                        # Cell 1: Player name and matchup (nested elements)
                        # Cell 2: Proj. Pts
                        # ...remaining stat columns
                        
                        # Extract player name from cell 1
                        # The new structure has player name in nested divs
                        player_cell = cells[1]
                        player_text = player_cell.text.strip()
                        
                        # Parse player name and team
                        # Format: "Josh Allen\n(BUF @ NE)" or "Josh Allen (BUF @ NE)"
                        lines = player_text.replace('\n', ' ').strip()
                        
                        # Extract team from matchup info (TEAM vs/@ OPP)
                        team = None
                        team_match = re.search(r'\(([A-Z]{2,3})\s+(?:vs|@|VS|AT)', lines)
                        if team_match:
                            team = team_match.group(1)
                        
                        # Extract player name (everything before the parenthesis)
                        name_match = re.match(r"(.+?)\s*\(", lines)
                        if name_match:
                            full_name = name_match.group(1).strip()
                        else:
                            full_name = lines.split('(')[0].strip()
                        
                        name_parts = full_name.split()
                        first_name = name_parts[0] if name_parts else ""
                        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        
                        if not first_name:
                            continue
                        
                        # Get projected points
                        try:
                            proj_pts_text = cells[proj_pts_idx].text.strip()
                            if not proj_pts_text or proj_pts_text == "-":
                                continue
                            projected_points = float(proj_pts_text)
                        except (ValueError, IndexError):
                            continue
                        
                        # Map position to standard format
                        pos_map = {'qb': 'QB', 'rb': 'RB', 'wr': 'WR', 'te': 'TE', 'k': 'K', 'flex': 'FLEX'}
                        std_position = pos_map.get(position, position.upper())
                        
                        projection = {
                            'source': self.source,
                            'week': week,
                            'first_name': first_name,
                            'last_name': last_name,
                            'position': std_position,
                            'team': team,
                            'projected_points': round(projected_points, 1)
                        }
                        
                        all_projections.append(projection)
                        print(f"    {first_name} {last_name} ({team}): {projected_points} pts")
                        
                    except Exception as e:
                        continue
                
                print(f"  ✓ Scraped {len([p for p in all_projections if p['position'] == std_position])} {position.upper()} projections")
            
            except Exception as e:
                print(f"  ✗ Error scraping {position.upper()}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Remove duplicates (same player might appear in multiple tabs)
        seen = set()
        unique_projections = []
        for proj in all_projections:
            key = (proj['first_name'], proj['last_name'], proj['position'])
            if key not in seen:
                seen.add(key)
                unique_projections.append(proj)
        
        print(f"\nTotal unique players scraped: {len(unique_projections)}")
        return unique_projections
    
    def scrape_and_save(self, week: str = "Week 8", scoring: str = "PPR"):
        """Scrape projections and save to database."""
        projections = self.scrape_week_projections(week, scoring)
        
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
    with FirstDownStudioScraper(headless=False) as scraper:
        scraper.scrape_and_save(week="Week 8", scoring="PPR")

