"""
Summary of all databases after migration
"""
import sqlite3
import os
from pathlib import Path

BACKEND_DIR = Path("backend")
DB_DIR = BACKEND_DIR / "data" / "databases"

databases = {
    "projections.db": "Player Projections & Stats",
    "league.db": "League & Roster Data",
    "odds.db": "Betting Odds",
    "montecarlo.db": "Monte Carlo Simulations"
}

print("="*80)
print("DATABASE STRUCTURE SUMMARY")
print("="*80)
print()

total_size = 0

for db_name, description in databases.items():
    db_path = DB_DIR / db_name
    
    if not os.path.exists(db_path):
        print(f"{db_name:<20} NOT FOUND")
        continue
    
    size_mb = os.path.getsize(db_path) / (1024*1024)
    total_size += size_mb
    
    print(f"{db_name:<20} {description:<35} {size_mb:>10.2f} MB")
    
    # Get tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Get row counts for each table
    table_info = []
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:  # Only show non-empty tables
            table_info.append((table, count))
    
    conn.close()
    
    if table_info:
        for table, count in table_info:
            print(f"  - {table:<35} {count:>15,} rows")
    print()

print("="*80)
print(f"Total database size: {total_size:.2f} MB")
print("="*80)

