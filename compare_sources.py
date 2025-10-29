"""
Compare projections from multiple sources for the same players.
"""

import sys
import os
from database import ProjectionsDB
from collections import defaultdict

# Fix encoding issues on Windows
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # In Jupyter or other environments where reconfigure is not available
        pass


def compare_projections(week: str = "Week 8", position: str = None):
    """
    Compare projections from different sources for the same players.
    
    Args:
        week: Week to compare (e.g., "Week 8")
        position: Optional position filter (QB, RB, WR, TE)
    """
    with ProjectionsDB() as db:
        # Get projections from all sources
        projections = db.get_projections(week=week, position=position)
        
        if not projections:
            print("No projections found in database.")
            return
        
        # Group projections by player
        player_projections = defaultdict(list)
        
        for proj in projections:
            player_key = (
                proj['player_first_name'].lower(),
                proj['player_last_name'].lower(),
                proj['position']
            )
            player_projections[player_key].append(proj)
        
        # Filter to only players with multiple sources
        multi_source_players = {
            k: v for k, v in player_projections.items() 
            if len(v) > 1
        }
        
        if not multi_source_players:
            print(f"No players found with projections from multiple sources for {week}.")
            print(f"Total players with projections: {len(player_projections)}")
            return
        
        # Display comparison
        print(f"\nProjection Comparison for {week}")
        if position:
            print(f"Position: {position}")
        print("=" * 100)
        print(f"{'Player':<30} {'Pos':<6} {'Source':<20} {'Proj. Pts':<12} {'Difference':<12}")
        print("-" * 100)
        
        # Sort by player name
        sorted_players = sorted(multi_source_players.items(), 
                               key=lambda x: (x[0][2], x[0][1], x[0][0]))
        
        for (first, last, pos), projs in sorted_players:
            player_name = f"{first.title()} {last.title()}"
            
            # Sort projections by source
            projs_sorted = sorted(projs, key=lambda x: x['source_website'])
            
            # Calculate average and differences
            avg_points = sum(p['projected_points'] for p in projs_sorted) / len(projs_sorted)
            
            for idx, proj in enumerate(projs_sorted):
                diff = proj['projected_points'] - avg_points
                diff_str = f"{diff:+.1f}" if abs(diff) > 0.01 else "avg"
                
                if idx == 0:
                    print(f"{player_name:<30} {pos:<6} {proj['source_website']:<20} "
                          f"{proj['projected_points']:<12.1f} {diff_str:<12}")
                else:
                    print(f"{'':<30} {'':<6} {proj['source_website']:<20} "
                          f"{proj['projected_points']:<12.1f} {diff_str:<12}")
            
            print(f"{'':<30} {'':<6} {'AVERAGE':<20} {avg_points:<12.1f}")
            print("-" * 100)
        
        print(f"\nTotal players with multiple source projections: {len(multi_source_players)}")


def find_biggest_differences(week: str = "Week 8", top_n: int = 10):
    """
    Find players with the biggest projection differences between sources.
    
    Args:
        week: Week to analyze
        top_n: Number of players to show
    """
    with ProjectionsDB() as db:
        projections = db.get_projections(week=week)
        
        if not projections:
            print("No projections found in database.")
            return
        
        # Group by player
        player_projections = defaultdict(list)
        
        for proj in projections:
            player_key = (
                proj['player_first_name'],
                proj['player_last_name'],
                proj['position']
            )
            player_projections[player_key].append(proj)
        
        # Calculate differences for players with multiple sources
        differences = []
        
        for (first, last, pos), projs in player_projections.items():
            if len(projs) > 1:
                points = [p['projected_points'] for p in projs]
                diff = max(points) - min(points)
                avg = sum(points) / len(points)
                
                differences.append({
                    'first_name': first,
                    'last_name': last,
                    'position': pos,
                    'difference': diff,
                    'average': avg,
                    'min': min(points),
                    'max': max(points),
                    'projections': projs
                })
        
        # Sort by difference
        differences.sort(key=lambda x: x['difference'], reverse=True)
        
        print(f"\nTop {top_n} Players with Biggest Projection Differences ({week})")
        print("=" * 100)
        print(f"{'Rank':<6} {'Player':<30} {'Pos':<6} {'Min':<10} {'Max':<10} {'Diff':<10} {'Avg':<10}")
        print("-" * 100)
        
        for idx, player in enumerate(differences[:top_n], 1):
            player_name = f"{player['first_name']} {player['last_name']}"
            print(f"{idx:<6} {player_name:<30} {player['position']:<6} "
                  f"{player['min']:<10.1f} {player['max']:<10.1f} "
                  f"{player['difference']:<10.1f} {player['average']:<10.1f}")
            
            # Show which sources
            for proj in player['projections']:
                print(f"       └─ {proj['source_website']}: {proj['projected_points']:.1f} pts")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare projections from different sources")
    parser.add_argument("--week", type=str, default="Week 8", help="Week to compare")
    parser.add_argument("--position", type=str, help="Filter by position")
    parser.add_argument("--differences", action="store_true", help="Show biggest differences")
    parser.add_argument("--top", type=int, default=10, help="Number of players to show in differences")
    
    args = parser.parse_args()
    
    if args.differences:
        find_biggest_differences(week=args.week, top_n=args.top)
    else:
        compare_projections(week=args.week, position=args.position)

