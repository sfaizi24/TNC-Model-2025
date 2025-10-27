"""Sleeper ingestion routines."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.db import models

from .http import HTTPCache, http_get_json

logger = logging.getLogger(__name__)

SLEEPER_API_BASE = "https://api.sleeper.app/v1"


@dataclass
class SleeperConfig:
    league_id: str
    cache_dir: Path = Path("cache")
    cache_ttl: int = 86_400  # 24 hours
    concurrency: int = 5
    timeout: float = 30.0
    retries: int = 3


class SleeperClient:
    def __init__(self, config: SleeperConfig) -> None:
        self.config = config
        self.cache = HTTPCache(config.cache_dir / "sleeper", ttl=config.cache_ttl)

    async def _get(self, path: str, *, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{SLEEPER_API_BASE}/{path.lstrip('/') }"
        return await http_get_json(
            url,
            params=params,
            timeout=self.config.timeout,
            retries=self.config.retries,
            cache=self.cache if "players" in path else None,
        )

    async def get_state(self) -> dict[str, Any]:
        return await self._get("state/nfl")

    async def get_league(self) -> dict[str, Any]:
        return await self._get(f"league/{self.config.league_id}")

    async def get_users(self) -> list[dict[str, Any]]:
        return await self._get(f"league/{self.config.league_id}/users")

    async def get_rosters(self) -> list[dict[str, Any]]:
        return await self._get(f"league/{self.config.league_id}/rosters")

    async def get_players_directory(self) -> dict[str, Any]:
        return await self._get("players/nfl")


def upsert_league(session: Session, payload: dict[str, Any]) -> models.League:
    league = models.League(
        league_id=str(payload.get("league_id")),
        name=payload.get("name"),
        season=int(payload.get("season", 0)) if payload.get("season") else None,
        settings=payload.get("settings"),
    )
    session.merge(league)
    session.flush()
    return league


def upsert_users(session: Session, payload: Iterable[dict[str, Any]]) -> list[models.LeagueUser]:
    users: list[models.LeagueUser] = []
    for item in payload:
        user = models.LeagueUser(
            user_id=str(item.get("user_id")),
            display_name=item.get("display_name"),
            team_name=item.get("metadata", {}).get("team_name"),
            metadata_json=item.get("metadata"),
        )
        session.merge(user)
        users.append(user)
    session.flush()
    return users


def upsert_rosters(session: Session, payload: Iterable[dict[str, Any]]) -> list[models.Roster]:
    rosters: list[models.Roster] = []
    for item in payload:
        roster = models.Roster(
            roster_id=int(item.get("roster_id")),
            league_id=str(item.get("league_id")),
            owner_id=str(item.get("owner_id")) if item.get("owner_id") else None,
            players=item.get("players", []),
            starters=item.get("starters"),
            reserves=item.get("reserve"),
            metadata_json={
                key: value
                for key, value in item.items()
                if key
                not in {
                    "roster_id",
                    "league_id",
                    "owner_id",
                    "players",
                    "starters",
                    "reserve",
                }
            },
        )
        session.merge(roster)
        rosters.append(roster)
    session.flush()
    return rosters


def upsert_players(session: Session, payload: dict[str, Any]) -> list[models.Player]:
    players: list[models.Player] = []
    for sleeper_id, item in payload.items():
        player = models.Player(
            sleeper_player_id=str(sleeper_id),
            full_name=item.get("full_name"),
            position=item.get("position"),
            team=item.get("team"),
            status=item.get("status"),
            metadata_json=item,
        )
        session.merge(player)
        players.append(player)
    session.flush()
    return players


async def ingest_all(session: Session, config: SleeperConfig) -> dict[str, Any]:
    """Ingest league, users, rosters and players from Sleeper."""

    client = SleeperClient(config)
    league, users, rosters, players = await asyncio.gather(
        client.get_league(), client.get_users(), client.get_rosters(), client.get_players_directory()
    )

    state = await client.get_state()

    upsert_league(session, league)
    upsert_users(session, users)
    upsert_rosters(session, rosters)
    upsert_players(session, players)

    return {
        "league": league,
        "users": len(users),
        "rosters": len(rosters),
        "players": len(players),
        "season": state.get("season"),
        "week": state.get("week"),
    }


def ingest_sleeper(session: Session, config: SleeperConfig) -> dict[str, Any]:
    """Synchronous entrypoint for Typer command."""

    return asyncio.run(ingest_all(session, config))
