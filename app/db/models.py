"""Database models for the Sleeper ingestion service."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""


class Player(Base):
    __tablename__ = "players"

    sleeper_player_id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[str | None] = mapped_column(String(10))
    team: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str | None] = mapped_column(String(20))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    projections: Mapped[list["Projection"]] = relationship(back_populates="player")
    actuals: Mapped[list["PlayerActual"]] = relationship(back_populates="player")


class League(Base):
    __tablename__ = "leagues"

    league_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    season: Mapped[int | None] = mapped_column(Integer)
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    rosters: Mapped[list["Roster"]] = relationship(back_populates="league")


class LeagueUser(Base):
    __tablename__ = "league_users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    team_name: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    rosters: Mapped[list["Roster"]] = relationship(back_populates="owner")


class Roster(Base):
    __tablename__ = "rosters"

    roster_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[str] = mapped_column(String, ForeignKey("leagues.league_id"))
    owner_id: Mapped[str | None] = mapped_column(String, ForeignKey("league_users.user_id"))
    players: Mapped[list[str]] = mapped_column(JSON)
    starters: Mapped[list[str] | None] = mapped_column(JSON)
    reserves: Mapped[list[str] | None] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    league: Mapped[League] = relationship(back_populates="rosters")
    owner: Mapped[LeagueUser | None] = relationship(back_populates="rosters")


class Projection(Base):
    __tablename__ = "projections"

    source: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    sleeper_player_id: Mapped[str] = mapped_column(
        String, ForeignKey("players.sleeper_player_id"), primary_key=True
    )
    team: Mapped[str | None] = mapped_column(String(10))
    position: Mapped[str | None] = mapped_column(String(10))
    proj_points: Mapped[float | None] = mapped_column(Numeric)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    player: Mapped[Player] = relationship(back_populates="projections")


class PlayerActual(Base):
    __tablename__ = "player_actuals"

    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    sleeper_player_id: Mapped[str] = mapped_column(
        String, ForeignKey("players.sleeper_player_id"), primary_key=True
    )
    team: Mapped[str | None] = mapped_column(String(10))
    position: Mapped[str | None] = mapped_column(String(10))
    fantasy_points: Mapped[float | None] = mapped_column(Numeric)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    player: Mapped[Player] = relationship(back_populates="actuals")


class PlayerAlias(Base):
    __tablename__ = "player_aliases"

    source: Mapped[str] = mapped_column(String, primary_key=True)
    source_player_key: Mapped[str] = mapped_column(String, primary_key=True)
    sleeper_player_id: Mapped[str] = mapped_column(String, ForeignKey("players.sleeper_player_id"))
    notes: Mapped[str | None] = mapped_column(Text)

