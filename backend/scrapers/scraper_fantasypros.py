import time
import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from .database import ProjectionsDB
from typing import List, Dict

# Fix encoding issues on Windows
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


class FantasyProsScraper:
    """Scraper for FantasyPros consensus rankings."""
    
    def __init__(self, headless: bool = True, db_path: str = None):
        """Initialize the scraper with Chrome options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        # Disable images for faster loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(20)  # 20 second timeout
        self.source = "fantasypros.com"
        self.db_path = db_path or "backend/data/databases/projections.db"
        
        # Position URLs - PPR for skill positions
        self.position_urls = {
            'QB': 'https://www.fantasypros.com/nfl/rankings/qb.php',
            'RB': 'https://www.fantasypros.com/nfl/rankings/ppr-rb.php',
            'WR': 'https://www.fantasypros.com/nfl/rankings/ppr-wr.php',
            'TE': 'https://www.fantasypros.com/nfl/rankings/ppr-te.php',
            'K': 'https://www.fantasypros.com/nfl/rankings/k.php',
            'DST': 'https://www.fantasypros.com/nfl/rankings/dst.php',
        }
    
    def _scrape_position(self, position: str, url: str, week: str) -> List[Dict]:
        """Scrape rankings for a specific position."""
        print(f"\n  [{position}] Loading {url}")
        projections = []
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                # Load page
                print(f"    → Loading page (attempt {attempt + 1})...", end=" ", flush=True)
                self.driver.get(url)
                print("OK")
                
                # Quick wait for table
                print(f"    → Waiting for table...", end=" ", flush=True)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                )
                print("OK")
                
                # Scroll to load all players
                print(f"    → Scrolling to load all players...", end=" ", flush=True)
                last_count = 0
                for _ in range(15):  # Max 15 scrolls
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.3)
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                    if len(rows) == last_count:
                        break
                    last_count = len(rows)
                print(f"found {last_count} rows")
                
                # Scroll back to top
                self.driver.execute_script("window.scrollTo(0, 0);")
                
                # Get all rows
                print(f"    → Parsing players...", flush=True)
                rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 4:
                            continue
                        
                        # Get rank
                        rank_text = cells[0].text.strip()
                        if not rank_text or not rank_text[0].isdigit():
                            continue
                        
                        # Find player cell (the one with parentheses for team)
                        player_cell_text = ""
                        for i in range(1, min(4, len(cells))):
                            txt = cells[i].text.strip()
                            if '(' in txt and ')' in txt:
                                player_cell_text = txt
                                break
                        
                        if not player_cell_text:
                            player_cell_text = cells[2].text.strip() if len(cells) > 2 else ""
                        
                        if not player_cell_text:
                            continue
                        
                        # Extract team
                        team = None
                        team_match = re.search(r'\(([A-Z]{2,3})\)', player_cell_text)
                        if team_match:
                            team = team_match.group(1)
                        
                        # Clean player name
                        player_name = re.sub(r'\s*\([^)]*\)\s*', '', player_cell_text).strip()
                        player_name = re.sub(r'\s*(Q|O|D|IR|PUP|SSPD|COV|OUT)$', '', player_name).strip()
                        
                        if not player_name:
                            continue
                        
                        # Get PROJ. FPTS from last cell
                        try:
                            projected_points = float(cells[-1].text.strip())
                        except ValueError:
                            try:
                                projected_points = float(cells[-2].text.strip())
                            except ValueError:
                                continue
                        
                        if projected_points < 0.1 or projected_points > 60:
                            continue
                        
                        # Parse name
                        if position == 'DST':
                            first_name, last_name = player_name, "Defense"
                        else:
                            parts = player_name.split()
                            if not parts:
                                continue
                            first_name = parts[0]
                            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                        
                        projections.append({
                            'source': self.source,
                            'week': week,
                            'first_name': first_name,
                            'last_name': last_name,
                            'position': position,
                            'team': team,
                            'projected_points': round(projected_points, 1)
                        })
                        
                        team_str = f" ({team})" if team else ""
                        print(f"      {len(projections):3}. {first_name} {last_name}{team_str}: {projected_points:.1f}")
                    
                    except Exception:
                        continue
                
                print(f"    ✓ {position}: {len(projections)} players scraped")
                return projections
                
            except TimeoutException:
                print(f"TIMEOUT")
                if attempt < max_retries:
                    print(f"    ⚠ Retrying...")
                    time.sleep(1)
                else:
                    print(f"    ✗ Failed after {max_retries + 1} attempts")
                    
            except WebDriverException as e:
                print(f"ERROR: {str(e)[:50]}")
                if attempt < max_retries:
                    print(f"    ⚠ Retrying...")
                    time.sleep(1)
                else:
                    print(f"    ✗ Failed after {max_retries + 1} attempts")
                    
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                if attempt < max_retries:
                    print(f"    ⚠ Retrying...")
                    time.sleep(1)
                else:
                    print(f"    ✗ Failed: {str(e)[:80]}")
        
        return projections
    
    def scrape_week_projections(self, week: str = "Week 14") -> List[Dict]:
        """Scrape projections for all positions."""
        print(f"\n{'='*60}")
        print(f"FANTASYPROS SCRAPER - {week}")
        print(f"{'='*60}")
        
        all_projections = []
        
        for position, url in self.position_urls.items():
            position_projs = self._scrape_position(position, url, week)
            all_projections.extend(position_projs)
            time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"Total: {len(all_projections)} players scraped")
        print(f"{'='*60}")
        
        return all_projections
    
    def scrape_and_save(self, week: str = "Week 14"):
        """Scrape projections and save to database."""
        projections = self.scrape_week_projections(week)
        
        if projections:
            print(f"\nSaving {len(projections)} projections to database...")
            with ProjectionsDB(db_path=self.db_path) as db:
                db.insert_projections_batch(projections)
            print("✓ Successfully saved to database!")
        else:
            print("No projections found to save.")
    
    def close(self):
        """Close the browser."""
        try:
            self.driver.quit()
        except:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    with FantasyProsScraper(headless=False) as scraper:
        scraper.scrape_and_save(week="Week 14")
