"""Entity resolution helpers for mapping external players to Sleeper IDs."""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models

_NAME_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv)\.?$", re.IGNORECASE)
_PUNCTUATION_RE = re.compile(r"[^a-z0-9 ]+")

TEAM_ALIASES = {
    "JAX": "JAC",
    "LA": "LAR",
    "SD": "LAC",
    "WSH": "WAS",
}


def normalize_name(name: str) -> str:
    """Return a normalised version of a player's full name."""

    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = _PUNCTUATION_RE.sub("", text)
    text = _NAME_SUFFIX_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_team(team: Optional[str]) -> Optional[str]:
    if not team:
        return team
    team = team.upper()
    return TEAM_ALIASES.get(team, team)


def resolve_player_by_name(
    session: Session, name: str, team: Optional[str], position: Optional[str]
) -> Optional[models.Player]:
    """Attempt to resolve a player by normalised name/team/position."""

    normalized_name = normalize_name(name)
    normalized_team = normalize_team(team)

    stmt = select(models.Player).where(models.Player.full_name.is_not(None))
    candidates = session.execute(stmt).scalars().all()
    for candidate in candidates:
        if not candidate.full_name:
            continue
        candidate_name = normalize_name(candidate.full_name)
        candidate_team = normalize_team(candidate.team)
        if candidate_name != normalized_name:
            continue
        if normalized_team and candidate_team and candidate_team != normalized_team:
            continue
        if position and candidate.position and candidate.position.upper() != position.upper():
            continue
        return candidate
    return None


def get_or_create_alias(
    session: Session,
    source: str,
    source_player_key: str,
    *,
    sleeper_player_id: Optional[str] = None,
    candidate_names: Iterable[tuple[str, Optional[str], Optional[str]]] = (),
) -> Optional[str]:
    """Resolve an alias, optionally creating it if a matching player is found."""

    alias = session.get(
        models.PlayerAlias, {"source": source, "source_player_key": source_player_key}
    )
    if alias:
        return alias.sleeper_player_id

    resolved_id: Optional[str] = None
    if sleeper_player_id:
        resolved_id = sleeper_player_id
    else:
        for name, team, position in candidate_names:
            player = resolve_player_by_name(session, name, team, position)
            if player:
                resolved_id = player.sleeper_player_id
                break

    if resolved_id:
        alias = models.PlayerAlias(
            source=source,
            source_player_key=source_player_key,
            sleeper_player_id=resolved_id,
        )
        session.merge(alias)
        session.flush()
        return resolved_id
    return None
