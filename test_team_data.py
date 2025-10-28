"""Test that all scrapers are extracting team data correctly."""
import sys
import os

# Fix encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')

print("Testing team data extraction from all sources...\n")
print("="*80)

# Test each scraper
sources_to_test = [
    ('FanDuel', 'scraper_fanduel', 'FanDuelScraper'),
    ('Sleeper', 'scraper_sleeper', 'SleeperScraper'),
    ('FantasyPros', 'scraper_fantasypros', 'FantasyProsScraper'),
    ('First Down Studio', 'scraper_firstdown', 'FirstDownStudioScraper'),
    ('ESPN', 'scraper_espn', 'ESPNScraper'),
]

for source_name, module_name, class_name in sources_to_test:
    print(f"\n{source_name}:")
    print("-" * 80)
    
    try:
        module = __import__(module_name)
        scraper_class = getattr(module, class_name)
        
        # Create scraper instance
        if source_name == 'Sleeper':
            scraper = scraper_class()
            projs = scraper.scrape_week_projections("Week 9", "2024")
            scraper.__exit__(None, None, None)
        elif source_name in ['FanDuel', 'FantasyPros', 'ESPN']:
            scraper = scraper_class(headless=True)
            if source_name == 'ESPN':
                projs = scraper.scrape_week_projections("Week 8", "2024")
            else:
                projs = scraper.scrape_week_projections("Week 8")
            scraper.close()
        else:  # First Down Studio
            scraper = scraper_class(headless=True)
            projs = scraper.scrape_week_projections("Week 8", "PPR")
            scraper.close()
        
        # Check team data
        with_team = sum(1 for p in projs if p.get('team'))
        total = len(projs)
        
        print(f"\nTotal projections: {total}")
        print(f"With team data: {with_team} ({with_team/total*100:.1f}%)")
        
        # Show samples
        print("\nSample projections:")
        for p in projs[:3]:
            team_str = f"({p.get('team', 'NO TEAM')})" if p.get('team') else "(NO TEAM)"
            print(f"  {p['first_name']} {p['last_name']} {team_str} - {p['position']}: {p['projected_points']} pts")
        
        print(f"\n✓ {source_name}: PASS")
        
    except Exception as e:
        print(f"\n✗ {source_name}: FAIL - {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("Team data extraction test complete!")

