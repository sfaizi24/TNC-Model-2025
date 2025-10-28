"""
Quick test script to verify scrapers are working correctly.
"""

import sys
import os

# Fix encoding issues on Windows
if os.name == 'nt':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

def test_firstdown():
    """Test First Down Studio scraper."""
    print("\n" + "="*80)
    print("Testing First Down Studio Scraper...")
    print("="*80)
    
    try:
        from scraper_firstdown import FirstDownStudioScraper
        print("✓ Import successful")
        
        with FirstDownStudioScraper(headless=True) as scraper:
            projections = scraper.scrape_week_projections(week="Week 8", scoring="PPR")
            
            if projections and len(projections) > 0:
                print(f"✓ Successfully scraped {len(projections)} projections")
                print(f"Sample: {projections[0]}")
                return True
            else:
                print("✗ No projections returned")
                return False
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fanduel():
    """Test FanDuel scraper."""
    print("\n" + "="*80)
    print("Testing FanDuel Scraper...")
    print("="*80)
    
    try:
        from scraper_fanduel import FanDuelScraper
        print("✓ Import successful")
        
        # Check if playwright is installed
        try:
            from playwright.sync_api import sync_playwright
            print("✓ Playwright installed")
        except ImportError:
            print("✗ Playwright not installed. Run: pip install playwright")
            print("  Then run: playwright install chromium")
            return False
        
        with FanDuelScraper(headless=True) as scraper:
            projections = scraper.scrape_week_projections(week="Week 8")
            
            if projections and len(projections) > 0:
                print(f"✓ Successfully scraped {len(projections)} projections")
                print(f"Sample: {projections[0]}")
                return True
            else:
                print("✗ No projections returned")
                return False
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """Check what's currently in the database."""
    print("\n" + "="*80)
    print("Checking Database Contents...")
    print("="*80)
    
    try:
        from database import ProjectionsDB
        
        with ProjectionsDB() as db:
            all_projs = db.get_projections()
            
            if not all_projs:
                print("Database is empty")
                return
            
            print(f"\nTotal projections: {len(all_projs)}")
            
            # Count by source
            sources = {}
            for proj in all_projs:
                source = proj['source_website']
                sources[source] = sources.get(source, 0) + 1
            
            print("\nBreakdown by source:")
            for source, count in sources.items():
                print(f"  {source}: {count} projections")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_sleeper():
    """Test Sleeper scraper."""
    print("\n" + "="*80)
    print("Testing Sleeper Scraper...")
    print("="*80)
    
    try:
        from scraper_sleeper import SleeperScraper
        print("✓ Import successful")
        
        with SleeperScraper() as scraper:
            projections = scraper.scrape_week_projections(week="Week 8", season="2024")
            
            if projections and len(projections) > 0:
                print(f"✓ Successfully scraped {len(projections)} projections")
                print(f"Sample: {projections[0]}")
                return True
            else:
                print("✗ No projections returned")
                return False
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fantasypros():
    """Test FantasyPros scraper."""
    print("\n" + "="*80)
    print("Testing FantasyPros Scraper...")
    print("="*80)
    
    try:
        from scraper_fantasypros import FantasyProsScraper
        print("✓ Import successful")
        
        with FantasyProsScraper(headless=True) as scraper:
            projections = scraper.scrape_week_projections(week="Week 8")
            
            if projections and len(projections) > 0:
                print(f"✓ Successfully scraped {len(projections)} projections")
                print(f"Sample: {projections[0]}")
                return True
            else:
                print("✗ No projections returned")
                return False
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCRAPER TEST SUITE")
    print("="*80)
    
    # Check current database state
    check_database()
    
    # Test scrapers
    fd_result = test_firstdown()
    fanduel_result = test_fanduel()
    sleeper_result = test_sleeper()
    fantasypros_result = test_fantasypros()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"First Down Studio: {'✓ PASS' if fd_result else '✗ FAIL'}")
    print(f"FanDuel: {'✓ PASS' if fanduel_result else '✗ FAIL'}")
    print(f"Sleeper: {'✓ PASS' if sleeper_result else '✗ FAIL'}")
    print(f"FantasyPros: {'✓ PASS' if fantasypros_result else '✗ FAIL'}")
    print("="*80)
    
    if not fanduel_result:
        print("\n📝 To fix FanDuel scraper:")
        print("1. Install Playwright: pip install playwright")
        print("2. Install browser: playwright install chromium")
        print("3. Run again: python test_scrapers.py")

