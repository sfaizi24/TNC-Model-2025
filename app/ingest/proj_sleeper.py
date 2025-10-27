"""Sleeper native projections ingestion."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db import models

from .http import http_get_json
from .mapping import get_or_create_alias
from .projections import ProjectionResult

logger = logging.getLogger(__name__)

SOURCE = "sleeper"
PROJECTION_ENDPOINT = (
    "https://api.sleeper.app/projections/nfl/{season}/{week}?season_type=regular"
)


@dataclass
class SleeperProjectionIngestor:
    source: str = SOURCE
    positions: tuple[str, ...] = ("QB", "RB", "WR", "TE", "K", "DEF")

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        logger.info("Fetching Sleeper projections for %s week %s", season, week)
        data = asyncio.run(
            http_get_json(
                PROJECTION_ENDPOINT.format(season=season, week=week),
                params={"position[]": list(self.positions)},
            )
        )
        rows = data if isinstance(data, list) else data.get("data", [])
        inserted = 0
        for row in rows:
            sleeper_id = row.get("player_id")
            stats = row.get("stats") or {}
            proj_points = row.get("pts")
            team = row.get("team")
            position = row.get("position")
            if not sleeper_id:
                sleeper_id = get_or_create_alias(
                    session,
                    SOURCE,
                    str(row.get("player")),
                    candidate_names=[
                        (row.get("player"), row.get("team"), row.get("position"))
                    ],
                )
            if not sleeper_id:
                continue
            if dry_run:
                inserted += 1
                continue
            projection = models.Projection(
                source=SOURCE,
                season=season,
                week=week,
                sleeper_player_id=sleeper_id,
                team=team,
                position=position,
                proj_points=proj_points,
                stats=stats,
            )
            session.merge(projection)
            inserted += 1
        session.flush()
        return ProjectionResult(source=SOURCE, inserted=inserted, rows=len(rows))
