"""Validate projection data quality after scraping.

Checks source coverage, position coverage, row counts, and duplicates
in projections.db for a given week. Used by the /scrape skill and
scrape.py orchestrator.

Usage:
    python validate_scraping.py --week 17
    python validate_scraping.py --week 17 --json
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "backend/data/databases/projections.db"

EXPECTED_SOURCES = [
    "sleeper.com",
    "espn.com",
    "fantasypros.com",
    "firstdown.studio",
    "fanduel.com",
]
REQUIRED_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}

MIN_SOURCES = 3
MIN_PROJECTIONS = 150


def normalize_week(week_arg):
    """Normalize week input: '17' -> 'Week 17', 'Week 17' -> 'Week 17'."""
    week_str = str(week_arg).strip()
    if week_str.lower().startswith("week"):
        return week_str
    match = re.search(r"\d+", week_str)
    return f"Week {match.group()}" if match else week_str


def validate(db_path, week):
    """Run all validation checks and return a result dict."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Source coverage
    cursor.execute(
        "SELECT source_website, COUNT(*) FROM projections WHERE week = ? GROUP BY source_website",
        (week,),
    )
    source_counts = dict(cursor.fetchall())

    present_sources = list(source_counts.keys())
    missing_sources = [s for s in EXPECTED_SOURCES if s not in source_counts]

    # Position coverage
    cursor.execute(
        "SELECT position, COUNT(*) FROM projections WHERE week = ? GROUP BY position",
        (week,),
    )
    position_counts = dict(cursor.fetchall())
    present_positions = set(position_counts.keys())
    missing_positions = REQUIRED_POSITIONS - present_positions

    # Duplicates
    cursor.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT source_website, player_first_name, player_last_name, position, COUNT(*) as cnt
            FROM projections WHERE week = ?
            GROUP BY source_website, player_first_name, player_last_name, position
            HAVING cnt > 1
        )
        """,
        (week,),
    )
    duplicate_count = cursor.fetchone()[0]

    total = sum(source_counts.values())
    conn.close()

    # Determine status
    if len(present_sources) >= MIN_SOURCES and total >= MIN_PROJECTIONS and not missing_positions:
        status = "PASS"
    elif len(present_sources) >= MIN_SOURCES and total >= MIN_PROJECTIONS:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "status": status,
        "week": week,
        "total": total,
        "sources": len(present_sources),
        "source_counts": source_counts,
        "missing_sources": missing_sources,
        "positions": sorted(present_positions),
        "position_counts": position_counts,
        "missing_positions": sorted(missing_positions),
        "duplicates": duplicate_count,
    }


def print_report(result):
    """Print a human-readable validation report."""
    print(f"\nProjection Validation — {result['week']}")
    print("=" * 45)

    print(f"\nSources ({result['sources']}/{len(EXPECTED_SOURCES)} present)")
    for source in EXPECTED_SOURCES:
        count = result["source_counts"].get(source)
        if count:
            print(f"  {source:<22} {count:>5} rows  PASS")
        else:
            print(f"  {source:<22}   ---       MISSING")

    print(f"\nPositions ({len(result['positions'])}/{len(REQUIRED_POSITIONS)} covered)")
    parts = [f"{p}: {result['position_counts'].get(p, 0)}" for p in sorted(REQUIRED_POSITIONS)]
    print(f"  {', '.join(parts)}")
    if result["missing_positions"]:
        print(f"  Missing: {', '.join(result['missing_positions'])}")

    print("\nQuality")
    print(f"  Duplicates:  {result['duplicates']:>4}   {'PASS' if result['duplicates'] == 0 else 'WARN'}")
    print(f"  Total rows:  {result['total']:>4}   {'PASS' if result['total'] >= MIN_PROJECTIONS else 'FAIL'}")

    print(f"\nResult: {result['status']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate projection data quality")
    parser.add_argument("--week", required=True, help="Week number (e.g. 17 or 'Week 17')")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--db-path", default=None, help="Path to projections.db")
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    week = normalize_week(args.week)
    result = validate(db_path, week)

    if args.json:
        print(json.dumps(result))
    else:
        print_report(result)

    sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
