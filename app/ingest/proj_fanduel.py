"""FanDuel Research projections ingestion."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import httpx
from sqlalchemy.orm import Session

from app.db import models

from .mapping import get_or_create_alias
from .projections import ProjectionResult

logger = logging.getLogger(__name__)

SOURCE = "fanduel"
DEFAULT_URL = "https://research.fanduel.com/resource/api/hub/fantasy-point-projections/download"


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def pick_name(row: dict[str, Any]) -> str | None:
    for key in ("Player", "Name", "player", "player_name", "Nickname"):
        if key in row and row[key]:
            return str(row[key])
    return None


def pick_team(row: dict[str, Any]) -> str | None:
    for key in ("Team", "team", "NFL Team"):
        if key in row and row[key]:
            return str(row[key])
    return None


def pick_position(row: dict[str, Any]) -> str | None:
    for key in ("Pos", "Position", "position"):
        if key in row and row[key]:
            return str(row[key])
    return None


def pick_points(row: dict[str, Any]) -> float | None:
    for key in ("Fpts", "FPTS", "Proj", "FPPG", "Projected Points"):
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


@dataclass
class FanDuelProjectionIngestor:
    source: str = SOURCE
    url: str = DEFAULT_URL

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        params = {
            "season": season,
            "week": week,
            "sport": "NFL",
            "league": "NFL",
            "timezone": "UTC",
        }
        logger.info("Downloading FanDuel CSV for season=%s week=%s", season, week)
        try:
            response = httpx.get(self.url, params=params, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("FanDuel request failed: %s", exc)
            return ProjectionResult(source=SOURCE, inserted=0, rows=0)

        df = pd.read_csv(io.StringIO(response.text))
        records = df.to_dict(orient="records")
        inserted = 0
        for record in records:
            cleaned = {key: clean_value(value) for key, value in record.items()}
            name = pick_name(cleaned)
            if not name:
                continue
            team = pick_team(cleaned)
            position = pick_position(cleaned)
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
                proj_points=pick_points(cleaned),
                stats=cleaned,
            )
            session.merge(projection)
            inserted += 1
        session.flush()
        return ProjectionResult(source=SOURCE, inserted=inserted, rows=len(records))
