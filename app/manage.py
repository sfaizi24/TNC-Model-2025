"""Typer-based CLI for ingestion tasks."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from dataclasses import asdict

from app.db.database import session_scope
from app.ingest import actuals_espn, projections, sleeper
from app.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Management commands for the Sleeper ingestion service")


@app.command()
def ingest_sleeper(
    league_id: Optional[str] = typer.Option(
        None, "--league", help="Sleeper league identifier", show_default=False
    ),
    cache_dir: Optional[Path] = typer.Option(None, help="Cache directory for Sleeper responses"),
    timeout: float = typer.Option(30.0, help="HTTP timeout in seconds"),
    retries: int = typer.Option(3, help="Number of retry attempts for HTTP requests"),
) -> None:
    """Ingest Sleeper league metadata and roster information."""

    settings = get_settings()
    config = sleeper.SleeperConfig(
        league_id=league_id or settings.sleeper_league_id,
        cache_dir=cache_dir or Path(settings.cache_dir),
        timeout=timeout,
        retries=retries,
    )
    with session_scope() as session:
        result = sleeper.ingest_sleeper(session, config)
        typer.echo(json.dumps(result, indent=2))


@app.command()
def ingest_projections(
    season: int = typer.Option(..., min=2000, help="Season year"),
    week: int = typer.Option(..., min=1, max=23, help="Week number"),
    sources: Optional[str] = typer.Option(
        None,
        help="Comma-separated list of projection sources (default: all)",
    ),
    dry_run: bool = typer.Option(False, help="Simulate ingest without writing to DB"),
) -> None:
    """Ingest projections from configured sources."""

    selected_sources = [s.strip() for s in sources.split(",")] if sources else None
    with session_scope() as session:
        results = projections.ingest_projections(
            session,
            season=season,
            week=week,
            sources=selected_sources,
            dry_run=dry_run,
        )
    typer.echo(json.dumps([asdict(result) for result in results], indent=2))


@app.command()
def ingest_actuals(
    season: int = typer.Option(..., min=2000, help="Season year"),
    weeks: str = typer.Option(..., help="Comma-separated list or range of weeks, e.g. 1-4"),
    dry_run: bool = typer.Option(False, help="Simulate ingest without writing to DB"),
) -> None:
    """Ingest historical actuals from ESPN."""

    week_values: list[int] = []
    for part in weeks.split(","):
        part = part.strip()
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            week_values.extend(range(start, end + 1))
        else:
            week_values.append(int(part))
    with session_scope() as session:
        ingestor = actuals_espn.EspnActualsIngestor()
        result = ingestor.ingest(session, season=season, weeks=week_values, dry_run=dry_run)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def ingest_all(
    season: int = typer.Option(..., min=2000, help="Season year for projections/actuals"),
    week: int = typer.Option(..., min=1, max=23, help="Week number for projections"),
    league_id: Optional[str] = typer.Option(None, help="Sleeper league identifier"),
    weeks_actuals: Optional[str] = typer.Option(None, help="Weeks to ingest actuals, e.g. 1-8"),
) -> None:
    """Run all ingestion pipelines sequentially."""

    ingest_sleeper(league_id=league_id)
    ingest_projections(season=season, week=week, sources=None)
    if weeks_actuals:
        ingest_actuals(season=season, weeks=weeks_actuals)


if __name__ == "__main__":
    app()
