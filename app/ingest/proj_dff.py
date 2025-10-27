"""DailyFantasyFuel projections ingestion."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.db import models

from .mapping import get_or_create_alias
from .projections import ProjectionResult

logger = logging.getLogger(__name__)

SOURCE = "dailyfantasyfuel"
DEFAULT_URL = "https://www.dailyfantasyfuel.com/api/fantasy/players"


def pick_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in ("", None):
            return row[key]
    return None


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class DailyFantasyFuelProjectionIngestor:
    source: str = SOURCE
    url: str = DEFAULT_URL

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        params = {
            "league": "nfl",
            "week": week,
            "season": season,
            "type": "projection",
            "format": "csv",
        }
        logger.info("Downloading DailyFantasyFuel CSV for season=%s week=%s", season, week)
        try:
            response = httpx.get(self.url, params=params, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("DailyFantasyFuel request failed: %s", exc)
            return ProjectionResult(source=SOURCE, inserted=0, rows=0)

        df = pd.read_csv(io.StringIO(response.text))
        records = df.to_dict(orient="records")
        inserted = 0
        for record in records:
            name = pick_value(record, "Player", "Name", "player")
            if not name:
                continue
            team = pick_value(record, "Team", "team")
            position = pick_value(record, "Pos", "Position", "position")
            sleeper_id = get_or_create_alias(
                session,
                SOURCE,
                source_player_key=name,
                candidate_names=[(name, team, position)],
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
                proj_points=to_float(pick_value(record, "Proj", "FPTS", "Fpts", "Projection")),
                stats={key: (value if pd.notna(value) else None) for key, value in record.items()},
            )
            session.merge(projection)
            inserted += 1
        session.flush()
        return ProjectionResult(source=SOURCE, inserted=inserted, rows=len(records))
