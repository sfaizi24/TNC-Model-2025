"""Scrape fantasy football projections from all sources.

Runs each scraper independently with per-source error isolation.
Deletes stale data before each scraper run so row counts reflect
fresh results. Prints a structured summary at the end.

Usage:
    python scrape.py --week 17                        # all sources
    python scrape.py --week 17 --sources sleeper,espn # specific sources
    python scrape.py --week 17 --no-headless          # visible browser
    python scrape.py --week 17 --validate             # also run validation
"""

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from validate_scraping import DEFAULT_DB_PATH, normalize_week

SEASON_DEFAULT = "2025"

SOURCES = {
    "sleeper": "sleeper.com",
    "espn": "espn.com",
    "fantasypros": "fantasypros.com",
    "firstdown": "firstdown.studio",
    "fanduel": "fanduel.com",
}

MIN_SOURCES_FULL_RUN = 3
MIN_PROJECTIONS_FULL_RUN = 150


def delete_source_week(db_path, source_website, week):
    """Delete existing projections for a source+week before scraping."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM projections WHERE source_website = ? AND week = ?",
        (source_website, week),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def count_source_week(db_path, source_website, week):
    """Count projections for a source+week after scraping."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM projections WHERE source_website = ? AND week = ?",
        (source_website, week),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def run_scraper_in_process(name, week, season, headless, db_path):
    """Run a scraper in-process (Sleeper, ESPN, FantasyPros, FirstDown)."""
    if name == "sleeper":
        from backend.scrapers.scraper_sleeper import SleeperScraper

        with SleeperScraper(db_path=str(db_path)) as scraper:
            scraper.scrape_and_save(week=week, season=season)
    elif name == "espn":
        from backend.scrapers.scraper_espn import ESPNScraper

        with ESPNScraper(headless=headless, db_path=str(db_path)) as scraper:
            scraper.scrape_and_save(week=week, season=season)
    elif name == "fantasypros":
        from backend.scrapers.scraper_fantasypros import FantasyProsScraper

        with FantasyProsScraper(headless=headless, db_path=str(db_path)) as scraper:
            scraper.scrape_and_save(week=week)
    elif name == "firstdown":
        from backend.scrapers.scraper_firstdown import FirstDownStudioScraper

        with FirstDownStudioScraper(headless=headless, db_path=str(db_path)) as scraper:
            scraper.scrape_and_save(week=week, scoring="PPR")


def run_fanduel_subprocess(week, headless, db_path):
    """Run FanDuel scraper via subprocess (Playwright needs its own process)."""
    cmd = [
        sys.executable,
        "-m",
        "backend.scrapers.scraper_fanduel",
        "--week",
        week,
        "--db-path",
        str(db_path),
    ]
    if not headless:
        cmd.append("--no-headless")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "FanDuel subprocess failed")


def scrape_all(week, season, headless, sources, db_path):
    """Run scrapers and return list of result dicts."""
    results = []

    for name in sources:
        source_website = SOURCES[name]
        start = time.time()

        # Delete stale data first
        deleted = delete_source_week(db_path, source_website, week)
        if deleted:
            print(f"  Cleared {deleted} old rows for {source_website}")

        try:
            print(f"\n{'=' * 50}")
            print(f"Scraping: {source_website}")
            print(f"{'=' * 50}")

            if name == "fanduel":
                run_fanduel_subprocess(week, headless, db_path)
            else:
                run_scraper_in_process(name, week, season, headless, db_path)

            count = count_source_week(db_path, source_website, week)
            elapsed = time.time() - start

            results.append(
                {
                    "source": source_website,
                    "status": "OK" if count > 0 else "EMPTY",
                    "count": count,
                    "elapsed": elapsed,
                }
            )

        except Exception as e:
            elapsed = time.time() - start
            error_msg = str(e).split("\n")[0][:80]
            results.append(
                {
                    "source": source_website,
                    "status": "FAILED",
                    "count": 0,
                    "elapsed": elapsed,
                    "error": error_msg,
                }
            )

    return results


def print_summary(results):
    """Print structured summary table."""
    print(f"\n{'=' * 60}")
    print("SCRAPING SUMMARY")
    print(f"{'=' * 60}")
    print(f"{'Source':<22} {'Status':<10} {'Count':>6} {'Time':>8}")
    print("-" * 50)

    for r in results:
        status = r["status"]
        count = str(r["count"]) if r["count"] > 0 else "-"
        elapsed = f"{r['elapsed']:.1f}s"
        line = f"{r['source']:<22} {status:<10} {count:>6} {elapsed:>8}"
        if "error" in r:
            line += f"  ({r['error']})"
        print(line)

    succeeded = [r for r in results if r["status"] == "OK"]
    total = sum(r["count"] for r in results)
    print(f"\nTotal: {total} projections from {len(succeeded)}/{len(results)} sources")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape fantasy football projections")
    parser.add_argument("--week", required=True, help="Week number (e.g. 17 or 'Week 17')")
    parser.add_argument("--season", default=SEASON_DEFAULT, help=f"Season year (default: {SEASON_DEFAULT})")
    parser.add_argument("--sources", default=None, help="Comma-separated sources (default: all)")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--validate", action="store_true", help="Run validation after scraping")
    parser.add_argument("--db-path", default=None, help="Path to projections.db")
    args = parser.parse_args()

    week = normalize_week(args.week)
    db_path = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    # Parse source list
    if args.sources:
        requested = [s.strip().lower() for s in args.sources.split(",")]
        invalid = [s for s in requested if s not in SOURCES]
        if invalid:
            print(f"ERROR: Unknown sources: {', '.join(invalid)}", file=sys.stderr)
            print(f"Valid sources: {', '.join(SOURCES.keys())}", file=sys.stderr)
            sys.exit(1)
        sources = requested
    else:
        sources = list(SOURCES.keys())

    is_subset = args.sources is not None

    print(f"Scraping projections for {week} ({args.season})")
    print(f"Sources: {', '.join(sources)}")
    print(f"Database: {db_path}")

    results = scrape_all(week, args.season, args.headless, sources, db_path)
    print_summary(results)

    # Run validation if requested
    if args.validate:
        from validate_scraping import print_report, validate

        result = validate(db_path, week)
        print_report(result)

    # Exit code
    succeeded = [r for r in results if r["status"] == "OK"]
    total = sum(r["count"] for r in results)

    if is_subset:
        # Subset run: exit 0 if all requested sources succeeded
        sys.exit(0 if len(succeeded) == len(sources) else 1)
    else:
        # Full run: exit 0 if enough sources and projections
        sys.exit(0 if len(succeeded) >= MIN_SOURCES_FULL_RUN and total >= MIN_PROJECTIONS_FULL_RUN else 1)
