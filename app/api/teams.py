"""Teams API endpoints."""
from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db_session
from app.db import models
from app.settings import Settings
from pydantic import BaseModel

router = APIRouter(prefix="/teams", tags=["teams"])


class OwnerModel(BaseModel):
    user_id: str | None
    display_name: str | None
    team_name: str | None


class PlayerModel(BaseModel):
    sleeper_player_id: str
    full_name: str | None
    position: str | None
    team: str | None
    status: str | None


class TeamSummary(BaseModel):
    roster_id: int
    owner: OwnerModel


class RosterDetail(BaseModel):
    roster_id: int
    owner: OwnerModel
    starters: list[PlayerModel]
    bench: list[PlayerModel]
    reserves: list[PlayerModel]


def to_owner_model(user: models.LeagueUser | None) -> OwnerModel:
    return OwnerModel(
        user_id=user.user_id if user else None,
        display_name=user.display_name if user else None,
        team_name=user.team_name if user else None,
    )


def to_player_model(player: models.Player | None, sleeper_player_id: str) -> PlayerModel:
    return PlayerModel(
        sleeper_player_id=sleeper_player_id,
        full_name=player.full_name if player else None,
        position=player.position if player else None,
        team=player.team if player else None,
        status=player.status if player else None,
    )


def fetch_players(session: Session, player_ids: Iterable[str]) -> dict[str, models.Player | None]:
    ids = [pid for pid in player_ids if pid]
    if not ids:
        return {}
    stmt = select(models.Player).where(models.Player.sleeper_player_id.in_(ids))
    players = session.execute(stmt).scalars().all()
    return {player.sleeper_player_id: player for player in players}


@router.get("", response_model=list[TeamSummary])
def list_teams(
    league_id: str | None = Query(None, description="Sleeper league identifier"),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[TeamSummary]:
    target_league = league_id or settings.sleeper_league_id
    stmt = (
        select(models.Roster, models.LeagueUser)
        .join(models.LeagueUser, models.Roster.owner_id == models.LeagueUser.user_id, isouter=True)
        .where(models.Roster.league_id == target_league)
        .order_by(models.Roster.roster_id)
    )
    rows = session.execute(stmt).all()
    return [
        TeamSummary(roster_id=roster.roster_id, owner=to_owner_model(owner))
        for roster, owner in rows
    ]


@router.get("/{roster_id}/roster", response_model=RosterDetail)
def get_roster(
    roster_id: int,
    session: Session = Depends(get_db_session),
) -> RosterDetail:
    roster = session.get(models.Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    owner = session.get(models.LeagueUser, roster.owner_id) if roster.owner_id else None
    players = fetch_players(session, roster.players or [])
    starters = roster.starters or []
    reserves = roster.reserves or []
    starter_set = set(starters)
    reserve_set = set(reserves)
    bench = [
        pid
        for pid in (roster.players or [])
        if pid not in starter_set and pid not in reserve_set
    ]
    return RosterDetail(
        roster_id=roster.roster_id,
        owner=to_owner_model(owner),
        starters=[to_player_model(players.get(pid), pid) for pid in starters],
        bench=[to_player_model(players.get(pid), pid) for pid in bench],
        reserves=[to_player_model(players.get(pid), pid) for pid in reserves],
    )
