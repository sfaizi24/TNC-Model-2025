"""
Main script to scrape fantasy football projections from multiple sources and save to database.
"""

import argparse
from scraper_firstdown import FirstDownStudioScraper
from scraper_fanduel import FanDuelScraper
from scraper_sleeper import SleeperScraper
from scraper_fantasypros import FantasyProsScraper
from scraper_espn import ESPNScraper
from database import ProjectionsDB


def main():
    parser = argparse.ArgumentParser(
        description="Scrape fantasy football projections from multiple sources"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="firstdown.studio",
        choices=["firstdown.studio", "fanduel.com", "sleeper.com", "fantasypros.com", "espn.com", "all"],
        help="Source to scrape from"
    )
    parser.add_argument(
        "--season",
        type=str,
        default="2025",
        help="Season year (for Sleeper API)"
    )
    parser.add_argument(
        "--week",
        type=str,
        default="Week 8",
        help="Week to scrape (e.g., 'Week 8')"
    )
    parser.add_argument(
        "--scoring",
        type=str,
        default="PPR",
        choices=["PPR", "Half PPR", "Standard"],
        help="Scoring format (only applies to First Down Studio)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Show browser window (opposite of headless)"
    )
    parser.add_argument(
        "--view",
        action="store_true",
        help="View existing projections instead of scraping"
    )
    parser.add_argument(
        "--position",
        type=str,
        help="Filter by position when viewing (QB, RB, WR, TE)"
    )
    
    args = parser.parse_args()
    
    # Handle headless setting
    headless = not args.show_browser if args.show_browser else args.headless
    
    if args.view:
        # View existing projections
        print(f"\nViewing projections from database...")
        print("=" * 80)
        
        # Determine which source to filter by
        source_filter = None if args.source == "all" else args.source
        
        with ProjectionsDB() as db:
            projections = db.get_projections(
                source=source_filter,
                week=args.week,
                position=args.position
            )
            
            if not projections:
                print("No projections found in database.")
                print(f"\nRun without --view to scrape projections first.")
            else:
                print(f"Found {len(projections)} projections:\n")
                print(f"{'Rank':<6} {'Player':<30} {'Pos':<6} {'Source':<20} {'Proj. Pts':<10}")
                print("-" * 80)
                
                for idx, proj in enumerate(projections, 1):
                    player_name = f"{proj['player_first_name']} {proj['player_last_name']}"
                    print(f"{idx:<6} {player_name:<30} {proj['position']:<6} {proj['source_website']:<20} {proj['projected_points']:<10.1f}")
    
    else:
        # Scrape projections
        print(f"\nStarting scraper for {args.week}...")
        print(f"Source: {args.source}")
        print(f"Headless mode: {headless}")
        print("=" * 80)
        
        sources_to_scrape = []
        if args.source == "all":
            sources_to_scrape = ["firstdown.studio", "fanduel.com", "sleeper.com", "fantasypros.com", "espn.com"]
        else:
            sources_to_scrape = [args.source]
        
        for source in sources_to_scrape:
            print(f"\n{'=' * 80}")
            print(f"Scraping from {source}...")
            print("=" * 80)
            
            try:
                if source == "firstdown.studio":
                    with FirstDownStudioScraper(headless=headless) as scraper:
                        scraper.scrape_and_save(week=args.week, scoring=args.scoring)
                
                elif source == "fanduel.com":
                    with FanDuelScraper(headless=headless) as scraper:
                        scraper.scrape_and_save(week=args.week)
                
                elif source == "sleeper.com":
                    with SleeperScraper() as scraper:
                        scraper.scrape_and_save(week=args.week, season=args.season)
                
                elif source == "fantasypros.com":
                    with FantasyProsScraper(headless=headless) as scraper:
                        scraper.scrape_and_save(week=args.week)
                
                elif source == "espn.com":
                    with ESPNScraper(headless=headless) as scraper:
                        scraper.scrape_and_save(week=args.week, season=args.season)
                
            except Exception as e:
                print(f"✗ Error scraping {source}: {e}")
                continue
        
        print("\n" + "=" * 80)
        print("Scraping complete! Use --view to see the results.")


if __name__ == "__main__":
    main()

