"""
Example script demonstrating how to use the Sleeper League Data System.

This script shows you how to:
1. Find your leagues
2. Load league data
3. Query and analyze your data
"""

from scraper_sleeper_league import SleeperLeagueScraper
from database_league import LeagueDB

# ==================== CONFIGURATION ====================
# Update these with your information
SLEEPER_USERNAME = "your_username_here"  # Your Sleeper username
SEASON = "2024"
CURRENT_WEEK = 9

# ==================== STEP 1: FIND YOUR LEAGUES ====================

def find_leagues():
    """Find all your leagues for the current season."""
    print("\n" + "="*70)
    print("STEP 1: FINDING YOUR LEAGUES")
    print("="*70 + "\n")
    
    with SleeperLeagueScraper() as scraper:
        # Get user
        user = scraper.get_user(SLEEPER_USERNAME)
        
        if not user:
            print(f"❌ User '{SLEEPER_USERNAME}' not found!")
            print("Please update SLEEPER_USERNAME in the configuration section above.")
            return None
        
        print(f"✓ Found user: {user.get('display_name', SLEEPER_USERNAME)}")
        
        # Get leagues
        user_id = user['user_id']
        leagues = scraper.get_user_leagues(user_id, SEASON)
        
        if not leagues:
            print(f"❌ No leagues found for {SEASON}")
            return None
        
        print(f"\nYour leagues for {SEASON}:")
        for i, league in enumerate(leagues, 1):
            print(f"  {i}. {league['name']}")
            print(f"     League ID: {league['league_id']}")
            print(f"     Teams: {league.get('total_rosters', 'N/A')}")
            print()
        
        return leagues

# ==================== STEP 2: LOAD DATA ====================

def load_league_data(league_id):
    """Load all data for a league."""
    print("\n" + "="*70)
    print("STEP 2: LOADING LEAGUE DATA")
    print("="*70 + "\n")
    
    print("This will take 2-3 minutes...")
    print(f"Loading data for league: {league_id}\n")
    
    with SleeperLeagueScraper() as scraper:
        # Load league data (users, rosters, matchups)
        print("📊 Loading league information...")
        scraper.save_league_data(
            league_id=league_id,
            weeks=list(range(1, CURRENT_WEEK + 1)),
            include_transactions=True
        )
        
        # Load NFL player database
        print("\n🏈 Loading NFL players...")
        scraper.save_nfl_players()
        
        # Load player stats
        print(f"\n📈 Loading player stats (weeks 1-{CURRENT_WEEK})...")
        scraper.save_player_stats(SEASON, 1, CURRENT_WEEK)
        
        # Load NFL schedule
        print("\n📅 Loading NFL schedule...")
        scraper.save_nfl_schedule(SEASON)
    
    print("\n✅ Data loading complete!\n")

# ==================== STEP 3: ANALYZE DATA ====================

def show_league_standings(league_id):
    """Display league standings."""
    print("\n" + "="*70)
    print("LEAGUE STANDINGS")
    print("="*70 + "\n")
    
    with LeagueDB() as db:
        rosters = db.get_rosters(league_id)
        
        print(f"{'Rank':<6} {'Record':<10} {'Points For':<12} {'Team (Owner)'}")
        print("-" * 70)
        
        for i, roster in enumerate(rosters, 1):
            team_name = roster.get('team_name') or f"Team {roster['roster_id']}"
            owner = roster.get('display_name', 'Unknown')
            record = f"{roster.get('wins', 0)}-{roster.get('losses', 0)}"
            pts = roster.get('fpts', 0) + roster.get('fpts_decimal', 0)
            
            print(f"{i:<6} {record:<10} {pts:<12.2f} {team_name} ({owner})")
        
        print()

def show_matchups(league_id, week):
    """Display matchups for a specific week."""
    print("\n" + "="*70)
    print(f"MATCHUPS - Week {week}")
    print("="*70 + "\n")
    
    with LeagueDB() as db:
        matchups = db.get_matchups(league_id, week)
        
        if not matchups:
            print(f"No matchups found for week {week}")
            return
        
        # Group by matchup_id
        matchup_groups = {}
        for m in matchups:
            mid = m.get('matchup_id_number')
            if mid not in matchup_groups:
                matchup_groups[mid] = []
            matchup_groups[mid].append(m)
        
        # Display each matchup
        for mid in sorted(matchup_groups.keys()):
            teams = matchup_groups[mid]
            
            if len(teams) == 2:
                t1, t2 = teams
                
                name1 = t1.get('team_name') or t1.get('display_name') or f"Team {t1['roster_id']}"
                name2 = t2.get('team_name') or t2.get('display_name') or f"Team {t2['roster_id']}"
                
                pts1 = t1.get('points', 0)
                pts2 = t2.get('points', 0)
                
                winner = "🏆" if pts1 > pts2 else "  "
                winner2 = "🏆" if pts2 > pts1 else "  "
                
                print(f"Matchup {mid}:")
                print(f"  {winner} {name1:<35} {pts1:>6.2f}")
                print(f"  {winner2} {name2:<35} {pts2:>6.2f}")
                print()

def show_bye_weeks():
    """Display bye weeks."""
    print("\n" + "="*70)
    print(f"BYE WEEKS - {SEASON}")
    print("="*70 + "\n")
    
    with LeagueDB() as db:
        bye_weeks = db.get_bye_weeks(SEASON)
        
        # Group by week
        weeks_dict = {}
        for team, week in bye_weeks.items():
            if week not in weeks_dict:
                weeks_dict[week] = []
            weeks_dict[week].append(team)
        
        for week in sorted(weeks_dict.keys()):
            teams = sorted(weeks_dict[week])
            print(f"Week {week:2}: {', '.join(teams)}")
        
        print()

def show_player_info(player_name):
    """Look up a player and show their stats."""
    print("\n" + "="*70)
    print(f"PLAYER LOOKUP: {player_name}")
    print("="*70 + "\n")
    
    with LeagueDB() as db:
        # Find player
        all_players = db.get_nfl_players()
        matches = [p for p in all_players 
                  if player_name.lower() in p.get('full_name', '').lower()]
        
        if not matches:
            print(f"No players found matching '{player_name}'")
            return
        
        if len(matches) > 1:
            print(f"Found {len(matches)} matching players:")
            for p in matches[:10]:
                print(f"  - {p.get('full_name')} ({p.get('position')}, {p.get('team', 'FA')})")
            print("\nPlease be more specific")
            return
        
        player = matches[0]
        
        # Show player info
        print(f"Name: {player.get('full_name')}")
        print(f"Position: {player.get('position')}")
        print(f"Team: {player.get('team', 'Free Agent')}")
        print(f"Number: #{player.get('number', 'N/A')}")
        print(f"College: {player.get('college', 'N/A')}")
        print(f"Years Exp: {player.get('years_exp', 'N/A')}")
        print(f"Status: {player.get('status', 'N/A')}")
        
        injury = player.get('injury_status')
        if injury:
            print(f"Injury: {injury} - {player.get('injury_body_part', 'N/A')}")
        
        # Get stats
        stats = db.get_player_stats(player_id=player['player_id'], season=SEASON)
        
        if stats:
            print(f"\n{SEASON} Stats:")
            print("-" * 70)
            
            total_pts = 0
            for stat in stats:
                week = stat.get('week')
                pts = stat.get('pts_ppr', 0)
                total_pts += pts
                
                # Show key stats
                pass_yd = stat.get('pass_yd', 0)
                rush_yd = stat.get('rush_yd', 0)
                rec = stat.get('rec', 0)
                rec_yd = stat.get('rec_yd', 0)
                
                stats_str = []
                if pass_yd > 0:
                    stats_str.append(f"{pass_yd:.0f} pass yd")
                if rush_yd > 0:
                    stats_str.append(f"{rush_yd:.0f} rush yd")
                if rec > 0:
                    stats_str.append(f"{rec} rec, {rec_yd:.0f} yd")
                
                detail = ", ".join(stats_str) if stats_str else "N/A"
                print(f"  Week {week:2}: {pts:5.2f} pts | {detail}")
            
            avg_pts = total_pts / len(stats) if stats else 0
            print("-" * 70)
            print(f"Total: {total_pts:.2f} pts | Average: {avg_pts:.2f} pts/game")
        else:
            print(f"\nNo stats found for {SEASON}")
        
        print()

def database_status():
    """Show database statistics."""
    print("\n" + "="*70)
    print("DATABASE STATUS")
    print("="*70 + "\n")
    
    with LeagueDB() as db:
        leagues = db.get_all_leagues()
        all_players = db.get_nfl_players()
        all_stats = db.get_player_stats()
        
        print(f"Leagues: {len(leagues)}")
        for league in leagues:
            print(f"  - {league['name']} ({league['season']})")
        
        print(f"\nNFL Players: {len(all_players)}")
        
        # Position breakdown
        positions = {}
        for p in all_players:
            pos = p.get('position', 'Unknown')
            positions[pos] = positions.get(pos, 0) + 1
        
        print("  By Position:")
        for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
            if pos in positions:
                print(f"    {pos}: {positions[pos]}")
        
        if all_stats:
            weeks_with_stats = len(set(s['week'] for s in all_stats))
            print(f"\nPlayer Stats: {len(all_stats)} records across {weeks_with_stats} weeks")
        
        print()

# ==================== MAIN EXECUTION ====================

def main():
    """Main execution flow."""
    print("\n" + "="*70)
    print("SLEEPER LEAGUE DATA SYSTEM - EXAMPLE USAGE")
    print("="*70)
    
    # Step 1: Find leagues
    leagues = find_leagues()
    
    if not leagues:
        print("\n❌ Cannot continue without leagues.")
        print("Please update SLEEPER_USERNAME in the script and try again.")
        return
    
    # Select a league (for this example, we'll use the first one)
    selected_league = leagues[0]
    league_id = selected_league['league_id']
    
    print(f"\n📌 Using league: {selected_league['name']}")
    print(f"   League ID: {league_id}")
    
    # Step 2: Load data (comment this out if already loaded)
    choice = input("\nLoad league data? This takes 2-3 minutes. (y/n): ")
    if choice.lower() == 'y':
        load_league_data(league_id)
    
    # Step 3: Analyze data
    print("\n" + "="*70)
    print("STEP 3: ANALYZING DATA")
    print("="*70)
    
    # Show database status
    database_status()
    
    # Show league standings
    show_league_standings(league_id)
    
    # Show recent matchups
    show_matchups(league_id, CURRENT_WEEK)
    
    # Show bye weeks
    show_bye_weeks()
    
    # Example player lookup
    print("\n" + "="*70)
    print("EXAMPLE: PLAYER LOOKUP")
    print("="*70)
    example_players = ["Christian McCaffrey", "Patrick Mahomes", "Justin Jefferson"]
    print(f"\nTry looking up players like: {', '.join(example_players)}")
    
    player_name = input("\nEnter a player name to look up (or press Enter to skip): ")
    if player_name:
        show_player_info(player_name)
    
    print("\n" + "="*70)
    print("✅ EXAMPLE COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Use league_control.ipynb for interactive analysis")
    print("2. Read LEAGUE_DATA_GUIDE.md for more examples")
    print("3. Build custom queries using the database_league.py API")
    print()


if __name__ == "__main__":
    main()

