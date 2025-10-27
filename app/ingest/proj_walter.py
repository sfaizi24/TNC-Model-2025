"""WalterFootball HTML projections ingestion."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.db import models

from .mapping import get_or_create_alias
from .projections import ProjectionResult

logger = logging.getLogger(__name__)

SOURCE = "walterfootball"
DEFAULT_POSITION_URLS = {
    "QB": "https://walterfootball.com/fantasyweeklyqb.php",
    "RB": "https://walterfootball.com/fantasyweeklyrb.php",
    "WR": "https://walterfootball.com/fantasyweeklywr.php",
    "TE": "https://walterfootball.com/fantasyweeklyte.php",
}


def clean_points(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


@dataclass
class WalterFootballProjectionIngestor:
    source: str = SOURCE
    position_urls: dict[str, str] = field(default_factory=lambda: DEFAULT_POSITION_URLS.copy())

    def ingest(
        self, session: Session, season: int, week: int, *, dry_run: bool = False
    ) -> ProjectionResult:
        inserted = 0
        total_rows = 0
        for position, url in self.position_urls.items():
            try:
                response = httpx.get(url, params={"season": season, "week": week}, timeout=30.0)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("WalterFootball request failed for %s: %s", position, exc)
                continue
            try:
                tables = pd.read_html(response.text)
            except ValueError:
                logger.warning("No tables found in WalterFootball page for %s", position)
                continue
            if not tables:
                continue
            df = tables[0]
            records = df.to_dict(orient="records")
            total_rows += len(records)
            for record in records:
                name = record.get("Player") or record.get("Name")
                if not name:
                    continue
                team = record.get("Team")
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
                    proj_points=clean_points(record.get("Fantasy Points") or record.get("FP")),
                    stats=record,
                )
                session.merge(projection)
                inserted += 1
        session.flush()
        return ProjectionResult(source=SOURCE, inserted=inserted, rows=total_rows)
