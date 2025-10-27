"""Ingest historical actuals from ESPN game summaries."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from sqlalchemy.orm import Session

from app.db import models

from .mapping import get_or_create_alias

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://site.web.api.espn.com/apis/v2/sports/football/nfl/scoreboard"
SUMMARY_URL = "https://site.web.api.espn.com/apis/v2/sports/football/nfl/summary"


async def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_game_summaries(season: int, week: int) -> list[dict[str, Any]]:
    scoreboard = await fetch_json(
        SCOREBOARD_URL,
        {"week": week, "year": season, "seasontype": 2, "lang": "en", "region": "us"},
    )
    summaries: list[dict[str, Any]] = []
    events = scoreboard.get("events", [])
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        summary = await fetch_json(
            SUMMARY_URL, {"event": event_id, "lang": "en", "region": "us"}
        )
        summaries.append(summary)
    return summaries


def flatten_statistics(statistics: Iterable[dict[str, Any]]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for group in statistics:
        group_name = group.get("name")
        labels = group.get("labels", [])
        totals = group.get("totals", [])
        if labels and totals and len(labels) == len(totals):
            for label, total in zip(labels, totals):
                key = f"{group_name}_{label}" if group_name else label
                flat[key.replace(" ", "_").lower()] = total
        # include raw group for future debugging
        if group_name:
            flat[f"{group_name}_raw"] = group
    return flat


@dataclass
class EspnActualsIngestor:
    source: str = "espn"

    def ingest(
        self,
        session: Session,
        *,
        season: int,
        weeks: Iterable[int],
        dry_run: bool = False,
    ) -> dict[int, int]:
        inserted: dict[int, int] = {}
        for week in weeks:
            try:
                summaries = asyncio.run(fetch_game_summaries(season, week))
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch ESPN summaries for week %s: %s", week, exc)
                inserted[week] = 0
                continue
            week_inserted = 0
            for summary in summaries:
                boxscore = summary.get("boxscore", {})
                for team_group in boxscore.get("players", []) or []:
                    team = (team_group.get("team") or {}).get("abbreviation")
                    for player in team_group.get("statistics", []) or []:
                        athlete = player.get("athlete", {})
                        name = athlete.get("displayName") or athlete.get("fullName")
                        position = (athlete.get("position") or {}).get("abbreviation")
                        if not name:
                            continue
                        sleeper_id = get_or_create_alias(
                            session,
                            "espn_actuals",
                            source_player_key=str(athlete.get("id") or name),
                            candidate_names=[(name, team, position)],
                        )
                        if not sleeper_id:
                            continue
                        stats = flatten_statistics(player.get("statistics", []))
                        if dry_run:
                            week_inserted += 1
                            continue
                        actual = models.PlayerActual(
                            season=season,
                            week=week,
                            sleeper_player_id=sleeper_id,
                            team=team,
                            position=position,
                            fantasy_points=None,
                            stats=stats,
                        )
                        session.merge(actual)
                        week_inserted += 1
            inserted[week] = week_inserted
        session.flush()
        return inserted
