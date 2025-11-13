"""
Migration Script: Move Monte Carlo Simulation Data
From: projections.db → To: montecarlo.db

This script:
1. Creates montecarlo.db with proper schema
2. Migrates simulation_runs and monte_carlo_simulations tables
3. Verifies data integrity
4. Optionally cleans up old data from projections.db
"""

import sqlite3
import os
from pathlib import Path

# Get database paths
BACKEND_DIR = Path(__file__).parent / "backend"
DB_PROJ_PATH = str(BACKEND_DIR / "data" / "databases" / "projections.db")
DB_MONTECARLO_PATH = str(BACKEND_DIR / "data" / "databases" / "montecarlo.db")

print("="*70)
print("MONTE CARLO SIMULATION DATA MIGRATION")
print("="*70)
print()
print(f"Source:      {DB_PROJ_PATH}")
print(f"Destination: {DB_MONTECARLO_PATH}")
print()

# Check if projections.db exists
if not os.path.exists(DB_PROJ_PATH):
    print("ERROR: projections.db not found!")
    exit(1)

# Connect to both databases
conn_proj = sqlite3.connect(DB_PROJ_PATH)
conn_mc = sqlite3.connect(DB_MONTECARLO_PATH)

cursor_proj = conn_proj.cursor()
cursor_mc = conn_mc.cursor()

# Check if tables exist in source
cursor_proj.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('monte_carlo_simulations', 'simulation_runs')")
source_tables = [row[0] for row in cursor_proj.fetchall()]

if not source_tables:
    print("No simulation data found in projections.db - nothing to migrate!")
    conn_proj.close()
    conn_mc.close()
    exit(0)

print(f"Found tables to migrate: {', '.join(source_tables)}")
print()

# Create schema in montecarlo.db
print("Creating tables in montecarlo.db...")

cursor_mc.execute("""
    CREATE TABLE IF NOT EXISTS simulation_runs (
        run_id TEXT PRIMARY KEY,
        week INTEGER NOT NULL,
        seed INTEGER NOT NULL,
        n_simulations INTEGER NOT NULL,
        distribution_type TEXT,
        n_teams INTEGER,
        n_matchups INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor_mc.execute("""
    CREATE TABLE IF NOT EXISTS monte_carlo_simulations (
        run_id TEXT NOT NULL,
        week INTEGER NOT NULL,
        sim_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        team_name TEXT,
        owner TEXT,
        total_points REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (run_id, week, sim_id, team_id)
    )
""")

print("Tables created")
print()

# Migrate simulation_runs
if 'simulation_runs' in source_tables:
    print("Migrating simulation_runs...")
    cursor_proj.execute("SELECT COUNT(*) FROM simulation_runs")
    source_count = cursor_proj.fetchone()[0]
    
    if source_count > 0:
        cursor_proj.execute("SELECT * FROM simulation_runs")
        rows = cursor_proj.fetchall()
        
        cursor_mc.executemany("""
            INSERT OR REPLACE INTO simulation_runs 
            (run_id, week, seed, n_simulations, distribution_type, n_teams, n_matchups, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        
        print(f"  Migrated {len(rows)} simulation run records")
    else:
        print("  No simulation_runs data to migrate")

# Migrate monte_carlo_simulations
if 'monte_carlo_simulations' in source_tables:
    print()
    print("Migrating monte_carlo_simulations...")
    cursor_proj.execute("SELECT COUNT(*) FROM monte_carlo_simulations")
    source_count = cursor_proj.fetchone()[0]
    
    if source_count > 0:
        print(f"  Found {source_count:,} simulation rows to migrate...")
        print("  (This may take a moment for large datasets)")
        
        # Migrate in batches for efficiency
        batch_size = 10000
        cursor_proj.execute("SELECT * FROM monte_carlo_simulations")
        
        migrated = 0
        while True:
            rows = cursor_proj.fetchmany(batch_size)
            if not rows:
                break
            
            cursor_mc.executemany("""
                INSERT OR REPLACE INTO monte_carlo_simulations 
                (run_id, week, sim_id, team_id, team_name, owner, total_points, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            
            migrated += len(rows)
            print(f"  Progress: {migrated:,} / {source_count:,} rows", end='\r')
        
        print(f"\n  Migrated {migrated:,} simulation records")
    else:
        print("  No monte_carlo_simulations data to migrate")

# Commit changes
conn_mc.commit()

# Verify migration
print()
print("="*70)
print("VERIFICATION")
print("="*70)

cursor_mc.execute("SELECT COUNT(*) FROM simulation_runs")
mc_runs_count = cursor_mc.fetchone()[0]

cursor_mc.execute("SELECT COUNT(*) FROM monte_carlo_simulations")
mc_sims_count = cursor_mc.fetchone()[0]

print(f"montecarlo.db:")
print(f"  simulation_runs:          {mc_runs_count:,} rows")
print(f"  monte_carlo_simulations:  {mc_sims_count:,} rows")
print()

# Check source counts
cursor_proj.execute("SELECT COUNT(*) FROM simulation_runs")
proj_runs_count = cursor_proj.fetchone()[0]

cursor_proj.execute("SELECT COUNT(*) FROM monte_carlo_simulations")
proj_sims_count = cursor_proj.fetchone()[0]

print(f"projections.db (original):")
print(f"  simulation_runs:          {proj_runs_count:,} rows")
print(f"  monte_carlo_simulations:  {proj_sims_count:,} rows")
print()

# Ask if user wants to clean up
if proj_sims_count > 0:
    print("="*70)
    print("CLEANUP (Optional)")
    print("="*70)
    print()
    print("Would you like to remove simulation data from projections.db?")
    print("This will free up disk space but cannot be undone.")
    print()
    response = input("Remove simulation data from projections.db? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        cursor_proj.execute("DROP TABLE IF EXISTS monte_carlo_simulations")
        cursor_proj.execute("DROP TABLE IF EXISTS simulation_runs")
        conn_proj.commit()
        
        print()
        print("Removed simulation tables from projections.db")
        print()
        
        # Check new size
        print("Database sizes:")
        proj_size = os.path.getsize(DB_PROJ_PATH) / (1024*1024)
        mc_size = os.path.getsize(DB_MONTECARLO_PATH) / (1024*1024)
        
        print(f"  projections.db:  {proj_size:.2f} MB")
        print(f"  montecarlo.db:   {mc_size:.2f} MB")
    else:
        print("Skipped cleanup - simulation data remains in projections.db")

# Close connections
conn_proj.close()
conn_mc.close()

print()
print("="*70)
print("MIGRATION COMPLETE!")
print("="*70)
print()
print("Next steps:")
print("  1. Run notebook 07_monte_carlo_simulations.ipynb")
print("  2. Verify simulations save to montecarlo.db")
print("  3. Check that odds save to odds.db")
print()

