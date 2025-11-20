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
        
        Args:
            week: Week to scrape (e.g., "Week 8")
            scoring: Scoring format - "PPR", "Half PPR", or "Standard"
        
        Returns:
            List of projection dictionaries
        """
        url = "https://www.firstdown.studio/rankings"
        print(f"Navigating to {url}...")
        self.driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Note: We calculate PPR manually for FLEX players from component stats
        # QB projections are taken directly from the site
        print(f"Note: {scoring} points will be calculated from component stats for FLEX players")
        
        all_projections = []
        
        # Tabs to scrape - QB and FLEX should cover all players
        tabs = ["QB", "FLEX"]
        
        for tab in tabs:
            print(f"\nScraping {tab} tab...")
            try:
                # Click the tab
                tab_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{tab}')]"))
                )
                tab_button.click()
                time.sleep(2)
                
                # Wait for table to load
                table = self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                # Get header row to find column indices
                header_row = table.find_element(By.TAG_NAME, "tr")
                headers = [th.text.strip() for th in header_row.find_elements(By.TAG_NAME, "th")]
                
                print(f"  Table headers: {headers}")
                
                # Find column indices for stats we need
                col_indices = {}
                for idx, header in enumerate(headers):
                    if "Proj" in header and "Pts" in header:
                        col_indices['proj_pts'] = idx
                    elif header == "Rush Yds":
                        col_indices['rush_yds'] = idx
                    elif header == "Rec Yds":
                        col_indices['rec_yds'] = idx
                    elif header == "Rec":
                        col_indices['rec'] = idx
                    elif header == "TDs":
                        col_indices['tds'] = idx
                    elif header == "Pass Yds":
                        col_indices['pass_yds'] = idx
                    elif header == "Pass TDs":
                        col_indices['pass_tds'] = idx
                
                print(f"  Column indices found: {col_indices}")
                
                # Determine if we should calculate PPR for this tab
                calculate_ppr = (tab == "FLEX" and 'rush_yds' in col_indices and 
                               'rec_yds' in col_indices and 'rec' in col_indices and 
                               'tds' in col_indices)
                
                if calculate_ppr:
                    print(f"  ✓ Will calculate PPR points from component stats for {tab}")
                elif 'proj_pts' not in col_indices:
                    print(f"  ⚠ Could not find 'Proj. Pts' column or required stats, skipping {tab} tab")
                    continue
                
                # Get all data rows
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows[1:]:  # Skip header row
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 3:
                            continue
                        
                        # Extract player name and position
                        player_cell = cells[1].text
                        pos_cell = cells[2].text
                        
                        # Parse player name and team
                        # Format is usually "FirstName LastName (TEAM vs OPP)"
                        team = None
                        match = re.match(r"(.+?)\s*\(", player_cell)
                        if match:
                            full_name = match.group(1).strip()
                            name_parts = full_name.split()
                            first_name = name_parts[0]
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            
                            # Extract team from matchup info (TEAM vs OPP)
                            team_match = re.search(r'\(([A-Z]{2,3})\s+(?:vs|@)', player_cell)
                            if team_match:
                                team = team_match.group(1)
                        else:
                            # Fallback parsing
                            name_parts = player_cell.strip().split()
                            first_name = name_parts[0] if name_parts else ""
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        
                        # Extract position (remove number like RB1 -> RB)
                        position = re.sub(r'\d+', '', pos_cell).strip()
                        
                        # Calculate or extract projected points
                        if calculate_ppr:
                            # Calculate PPR points manually
                            try:
                                # Helper function to parse stat values (handles "-" as 0)
                                def parse_stat(text):
                                    text = text.strip()
                                    if not text or text == "-":
                                        return 0.0
                                    try:
                                        return float(text)
                                    except ValueError:
                                        return 0.0
                                
                                rush_yds = parse_stat(cells[col_indices['rush_yds']].text)
                                rec_yds = parse_stat(cells[col_indices['rec_yds']].text)
                                rec = parse_stat(cells[col_indices['rec']].text)
                                tds = parse_stat(cells[col_indices['tds']].text)
                                
                                # PPR Formula: ((Rush Yds + Rec Yds) / 10) + Receptions + (TDs * 6)
                                projected_points = ((rush_yds + rec_yds) / 10) + rec + (tds * 6)
                                print(f"  {first_name} {last_name} ({position}): {projected_points:.1f} pts (calculated: {rush_yds} rush + {rec_yds} rec yds, {rec} rec, {tds} TDs)")
                            except (ValueError, IndexError) as e:
                                print(f"  Error calculating PPR for {first_name} {last_name}: {e}")
                                continue
                        else:
                            # Use the Proj. Pts column directly (for QB tab)
                            try:
                                proj_pts_cell = cells[col_indices['proj_pts']].text
                                projected_points = float(proj_pts_cell)
                                print(f"  {first_name} {last_name} ({position}): {projected_points} pts")
                            except (ValueError, IndexError):
                                continue
                        
                        projection = {
                            'source': self.source,
                            'week': week,
                            'first_name': first_name,
                            'last_name': last_name,
                            'position': position,
                            'team': team,
                            'projected_points': round(projected_points, 1)
                        }
                        
                        all_projections.append(projection)
                        
                    except Exception as e:
                        print(f"Error parsing row: {e}")
                        continue
            
            except Exception as e:
                print(f"Error scraping {tab} tab: {e}")
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

