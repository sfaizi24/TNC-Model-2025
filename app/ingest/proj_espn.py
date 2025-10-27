"""ESPN projections ingestion (community endpoints)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.db import models

from .mapping import get_or_create_alias
from .projections import ProjectionResult

logger = logging.getLogger(__name__)

SOURCE = "espn"
BASE_URL = (
    "https://site.web.api.espn.com/apis/v2/sports/football/nfl/athletes/projections"
)


async def fetch_espn_projections(season: int, week: int) -> list[dict[str, Any]]:
    params = {
        "season": season,
        "week": week,
        "region": "us",
        "lang": "en",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    items = payload.get("items", [])
    return items


@dataclass
class EspnProjectionIngestor:
    source: str = SOURCE

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        try:
            rows = asyncio.run(fetch_espn_projections(season, week))
        except httpx.HTTPError as exc:
            logger.warning("ESPN request failed: %s", exc)
            return ProjectionResult(source=SOURCE, inserted=0, rows=0)

        inserted = 0
        for row in rows:
            athlete = row.get("athlete", {})
            name = athlete.get("displayName") or athlete.get("fullName")
            team = (athlete.get("team") or {}).get("abbreviation")
            position = (athlete.get("position") or {}).get("abbreviation")
            sleeper_id = get_or_create_alias(
                session,
                SOURCE,
                source_player_key=str(athlete.get("id") or name),
                candidate_names=[(name, team, position)] if name else (),
            )
            if not sleeper_id:
                continue
            stats = row.get("stats") or {}
            proj_points = stats.get("appliedTotal") or row.get("projectedPoints")
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
