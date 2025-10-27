"""Projection ingestion orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy.orm import Session

from app.db import models

from . import proj_dff, proj_espn, proj_fanduel, proj_sleeper, proj_walter


@dataclass
class ProjectionResult:
    source: str
    inserted: int
    rows: int


class ProjectionIngestor(Protocol):
    source: str

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        ...


INGESTOR_MAP: dict[str, ProjectionIngestor] = {
    proj_sleeper.SOURCE: proj_sleeper.SleeperProjectionIngestor(),
    proj_fanduel.SOURCE: proj_fanduel.FanDuelProjectionIngestor(),
    proj_dff.SOURCE: proj_dff.DailyFantasyFuelProjectionIngestor(),
    proj_espn.SOURCE: proj_espn.EspnProjectionIngestor(),
    proj_walter.SOURCE: proj_walter.WalterFootballProjectionIngestor(),
}


def ingest_projections(
    session: Session,
    *,
    season: int,
    week: int,
    sources: Iterable[str] | None = None,
    dry_run: bool = False,
) -> list[ProjectionResult]:
    """Run one or more projection ingestors."""

    selected_sources = list(sources) if sources else list(INGESTOR_MAP.keys())
    results: list[ProjectionResult] = []
    for source in selected_sources:
        ingestor = INGESTOR_MAP.get(source)
        if not ingestor:
            raise ValueError(f"Unknown projection source: {source}")
        results.append(ingestor.ingest(session, season, week, dry_run=dry_run))
    return results
