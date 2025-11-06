import time
import re
import sys
import os
from playwright.sync_api import sync_playwright
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


class FanDuelScraper:
    """Scraper for FanDuel fantasy projections using Playwright."""
    
    def __init__(self, headless: bool = True):
        """Initialize the scraper."""
        self.headless = headless
        self.source = "fanduel.com"
        self.url = "https://www.fanduel.com/research/nfl/fantasy/ppr"
    
    def _parse_player_name(self, full_name: str) -> tuple[str, str]:
        """
        Parse full name into first and last name.
        
        Args:
            full_name: Full player name (e.g., "Christian McCaffrey" or "Christian McCaffrey (O)")
        
        Returns:
            Tuple of (first_name, last_name)
        """
        # Clean injury/status indicators
        full_name = re.sub(r'\s*\([^)]*\)\s*$', '', full_name).strip()
        
        name_parts = full_name.split()
        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name
    
    def _intercept_network_request(self) -> Optional[List[Dict]]:
        """
        Uses Playwright to intercept network requests and capture projection data.
        
        Returns:
            List of projection dictionaries from FanDuel API
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            try:
                print(f"Navigating to {self.url}...")
                
                # Capture data from network responses
                captured_data = []
                
                def handle_response(response):
                    """Handle network response and extract projection data."""
                    if "api.fanduel.com/graphql" in response.url and response.request.method == 'POST':
                        print(f"  Intercepted data from {response.url}")
                        try:
                            data = response.json()
                            projections = data.get("data", {}).get("getProjections", [])
                            if projections:
                                print(f"  ✓ Found {len(projections)} projections in response")
                                if not captured_data:  # Only capture first valid response
                                    captured_data.append(projections)
                        except Exception as e:
                            log.warning(f"Could not parse JSON from response: {e}")
                
                page.on("response", handle_response)
                page.goto(self.url, timeout=60000)
                
                # Wait for table to load
                page.wait_for_selector('table', timeout=30000)
                
                if captured_data:
                    return max(captured_data, key=len)
                else:
                    log.error("Did not intercept any valid projection data")
                    return None
                    
            except Exception as e:
                log.error(f"Error during Playwright network interception: {e}")
                return None
            finally:
                browser.close()
    
    def scrape_week_projections(self, week: str = "Week 8") -> List[Dict]:
        """
        Scrape projections for a specific week.
        
        Args:
            week: Week to scrape (e.g., "Week 8")
        
        Returns:
            List of projection dictionaries
        """
        projection_data = self._intercept_network_request()
        
        if not projection_data:
            log.error("Failed to extract projection data")
            return []
        
        all_projections = []
        
        print(f"\nParsing {len(projection_data)} projections...")
        
        for item in projection_data:
            try:
                # Extract player info from nested structure
                player_info = item.get('player', {})
                team_info = item.get('team', {})
                
                full_name = player_info.get('name', '')
                position = player_info.get('position', '')
                team = team_info.get('abbreviation', '')
                proj_points = item.get('fantasy', 0)
                
                if not full_name or not position:
                    continue
                
                # Parse name into first and last
                first_name, last_name = self._parse_player_name(full_name)
                
                # Remove any numbers from position (just in case)
                position = re.sub(r'\d+', '', position).strip()
                
                # Convert projected points to float
                try:
                    projected_points = float(proj_points)
                except (ValueError, TypeError):
                    projected_points = 0.0
                
                projection = {
                    'source': self.source,
                    'week': week,
                    'first_name': first_name,
                    'last_name': last_name,
                    'position': position,
                    'team': team.upper() if team else None,
                    'projected_points': projected_points
                }
                
                all_projections.append(projection)
                print(f"  {first_name} {last_name} ({position}): {projected_points:.1f} pts")
                
            except Exception as e:
                log.warning(f"Error parsing projection: {e}")
                continue
        
        print(f"\nTotal players scraped: {len(all_projections)}")
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
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


if __name__ == "__main__":
    # Example usage
    with FanDuelScraper(headless=False) as scraper:
        scraper.scrape_and_save(week="Week 8")

