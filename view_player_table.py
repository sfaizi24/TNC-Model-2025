"""
Script to view all NFL players from the league database.
Shows player_id (Sleeper ID), first/last name, position, and NFL team.
"""

from database_league import LeagueDB

def view_all_players():
    """Display all NFL players in a clean format."""
    with LeagueDB() as db:
        players = db.get_nfl_players()
        
        print(f"\n{'='*100}")
        print(f"NFL PLAYERS TABLE - Complete Player List")
        print(f"{'='*100}\n")
        print(f"Total Players: {len(players)}\n")
        print(f"{'Sleeper ID':<15} {'First Name':<15} {'Last Name':<20} {'Pos':<5} {'Team':<5} {'Status':<10}")
        print("-" * 100)
        
        # Show first 50 players
        for player in players[:50]:
            player_id = (player.get('player_id') or '')[:13]  # Truncate long IDs
            first = (player.get('first_name') or '')[:15]
            last = (player.get('last_name') or '')[:20]
            pos = player.get('position') or ''
            team = player.get('team') or 'FA'
            status = player.get('status') or ''
            
            print(f"{player_id:<15} {first:<15} {last:<20} {pos:<5} {team:<5} {status:<10}")
        
        print(f"\n... and {len(players) - 50} more players")
        print(f"\n{'='*100}\n")

def view_by_position(position):
    """View players filtered by position."""
    with LeagueDB() as db:
        players = db.get_nfl_players(position=position)
        
        print(f"\n{'='*100}")
        print(f"{position} PLAYERS")
        print(f"{'='*100}\n")
        print(f"Total {position}s: {len(players)}\n")
        print(f"{'Sleeper ID':<15} {'Name':<30} {'Team':<5} {'Status':<10} {'Injury':<15}")
        print("-" * 100)
        
        for player in players[:25]:
            player_id = (player.get('player_id') or '')[:13]
            name = (player.get('full_name') or '')[:30]
            team = player.get('team') or 'FA'
            status = player.get('status') or ''
            injury = player.get('injury_status') or ''
            
            print(f"{player_id:<15} {name:<30} {team:<5} {status:<10} {injury:<15}")
        
        if len(players) > 25:
            print(f"\n... and {len(players) - 25} more {position}s")
        
        print(f"\n{'='*100}\n")

def export_to_csv(filename='nfl_players_export.csv'):
    """Export all players to a CSV file."""
    import csv
    
    with LeagueDB() as db:
        players = db.get_nfl_players()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['sleeper_player_id', 'first_name', 'last_name', 'full_name', 
                           'position', 'nfl_team', 'number', 'status', 'injury_status'])
            
            # Write data
            for player in players:
                writer.writerow([
                    player.get('player_id', ''),
                    player.get('first_name', ''),
                    player.get('last_name', ''),
                    player.get('full_name', ''),
                    player.get('position', ''),
                    player.get('team', ''),
                    player.get('number', ''),
                    player.get('status', ''),
                    player.get('injury_status', '')
                ])
        
        print(f"Exported {len(players)} players to {filename}")

def search_player(name):
    """Search for a player by name."""
    with LeagueDB() as db:
        all_players = db.get_nfl_players()
        matching = [p for p in all_players 
                   if name.lower() in (p.get('full_name') or '').lower()]
        
        print(f"\n{'='*100}")
        print(f"SEARCH RESULTS for '{name}'")
        print(f"{'='*100}\n")
        print(f"Found {len(matching)} matches\n")
        
        if matching:
            print(f"{'Sleeper ID':<15} {'Name':<30} {'Pos':<5} {'Team':<5} {'Status':<10}")
            print("-" * 100)
            
            for player in matching:
                player_id = (player.get('player_id') or '')[:13]
                full_name = (player.get('full_name') or '')[:30]
                pos = player.get('position') or ''
                team = player.get('team') or 'FA'
                status = player.get('status') or ''
                
                print(f"{player_id:<15} {full_name:<30} {pos:<5} {team:<5} {status:<10}")
        
        print(f"\n{'='*100}\n")

def show_stats():
    """Show database statistics."""
    with LeagueDB() as db:
        all_players = db.get_nfl_players()
        
        # Count by position
        positions = {}
        teams = {}
        for p in all_players:
            pos = p.get('position', 'Unknown')
            team = p.get('team', 'FA')
            positions[pos] = positions.get(pos, 0) + 1
            teams[team] = teams.get(team, 0) + 1
        
        print(f"\n{'='*70}")
        print(f"NFL PLAYERS DATABASE STATISTICS")
        print(f"{'='*70}\n")
        print(f"Total Players: {len(all_players)}")
        print(f"\nPlayers by Position:")
        for pos in sorted(positions.keys()):
            print(f"  {pos:<5}: {positions[pos]:>4}")
        
        print(f"\nTop 10 Teams by Player Count:")
        sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)[:10]
        for team, count in sorted_teams:
            team_str = team if team else 'None'
            print(f"  {team_str:<5}: {count:>3} players")
        
        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'stats':
            show_stats()
        elif command == 'export':
            export_to_csv()
        elif command == 'search' and len(sys.argv) > 2:
            search_player(' '.join(sys.argv[2:]))
        elif command == 'position' and len(sys.argv) > 2:
            view_by_position(sys.argv[2].upper())
        else:
            print("Usage:")
            print("  python view_player_table.py             # View first 50 players")
            print("  python view_player_table.py stats       # Show database statistics")
            print("  python view_player_table.py export      # Export to CSV")
            print("  python view_player_table.py search NAME # Search for player")
            print("  python view_player_table.py position QB # View by position")
    else:
        # Default: view all players
        view_all_players()

