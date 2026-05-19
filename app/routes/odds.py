import numpy as np
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .. import montecarlo
from .helpers import (
    display_name_for,
    get_current_week,
    get_league_id_for_week,
    get_team_mapping,
    query_analytics,
    resolve_owner,
)

odds_bp = Blueprint("odds", __name__)


@odds_bp.route("/api/matchups")
def get_matchups():
    try:
        week = get_current_week()
        team_mapping = get_team_mapping(week)

        rows = query_analytics(
            "SELECT * FROM betting_odds_matchup_ml WHERE week = :week ORDER BY matchup",
            {"week": week},
        )

        matchups = []
        for row in rows:
            team1_owner = team_mapping.get(row["team1_id"], f"Team {row['team1_id']}")
            team2_owner = team_mapping.get(row["team2_id"], f"Team {row['team2_id']}")

            matchups.append(
                {
                    "matchup": f"{team1_owner} vs {team2_owner}",
                    "original_matchup": row["matchup"],
                    "team1_id": row["team1_id"],
                    "team1_name": team1_owner,
                    "team1_win_prob": row["team1_win_prob"],
                    "team1_ml": row["team1_ml"],
                    "team2_id": row["team2_id"],
                    "team2_name": team2_owner,
                    "team2_win_prob": row["team2_win_prob"],
                    "team2_ml": row["team2_ml"],
                }
            )

        return jsonify(matchups)
    except Exception as e:
        print(f"Error getting matchups: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/team_performance")
def get_team_performance():
    try:
        week = get_current_week()

        rows = query_analytics(
            "SELECT * FROM betting_odds_team_ou WHERE week = :week ORDER BY owner",
            {"week": week},
        )

        teams = []
        for row in rows:
            teams.append(
                {
                    "team_id": row["team_id"],
                    "owner": display_name_for(row["owner"]),
                    "line": row["line"],
                    "over_prob": row["over_prob"],
                    "under_prob": row["under_prob"],
                }
            )

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting team performance: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


def _scorer_query(table_name):
    week = get_current_week()
    rows = query_analytics(
        f"""
        SELECT s.owner, s.probability, s.odds, ou.line AS proj_pts
        FROM {table_name} s
        LEFT JOIN betting_odds_team_ou ou
            ON ou.owner = s.owner AND ou.week = s.week
        WHERE s.week = :week
        ORDER BY s.probability DESC
        """,
        {"week": week},
    )
    return [
        {
            "owner": display_name_for(row["owner"]),
            "win_prob": round(row["probability"] * 100, 1),
            "odds": row["odds"],
            "proj_pts": round(row["proj_pts"], 1) if row["proj_pts"] is not None else None,
        }
        for row in rows
    ]


@odds_bp.route("/api/highest_scorer")
def get_highest_scorer():
    try:
        return jsonify(_scorer_query("betting_odds_highest_scorer"))
    except Exception as e:
        print(f"Error getting highest scorer: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/lowest_scorer")
def get_lowest_scorer():
    try:
        return jsonify(_scorer_query("betting_odds_lowest_scorer"))
    except Exception as e:
        print(f"Error getting lowest scorer: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/first_place")
def get_first_place():
    try:
        week = get_current_week()

        rows = query_analytics(
            "SELECT owner, probability, american_odds FROM betting_odds_first_place WHERE week = :week ORDER BY probability DESC",
            {"week": week},
        )

        teams = []
        for row in rows:
            teams.append(
                {
                    "owner": display_name_for(row["owner"]),
                    "win_prob": round(row["probability"] * 100, 1),
                    "odds": row["american_odds"],
                }
            )

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting first place: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/ammad_playoff")
def get_ammad_playoff():
    try:
        week = get_current_week()

        rows = query_analytics(
            "SELECT owner, probability, american_odds FROM betting_odds_make_playoffs WHERE week = :week ORDER BY probability DESC",
            {"week": week},
        )

        teams = []
        for row in rows:
            teams.append(
                {
                    "owner": display_name_for(row["owner"]),
                    "win_prob": round(row["probability"] * 100, 1),
                    "odds": row["american_odds"],
                }
            )

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting ammad playoff: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/lineup/<owner>")
def get_lineup(owner):
    try:
        week = get_current_week()

        rows = query_analytics(
            """
            SELECT slot, player_name, position, mu
            FROM team_lineups
            WHERE owner = :owner AND week = :week
                AND slot IN ('QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'K', 'DEF')
            ORDER BY
                CASE slot
                    WHEN 'QB' THEN 1
                    WHEN 'RB1' THEN 2
                    WHEN 'RB2' THEN 3
                    WHEN 'WR1' THEN 4
                    WHEN 'WR2' THEN 5
                    WHEN 'TE' THEN 6
                    WHEN 'FLEX' THEN 7
                    WHEN 'K' THEN 8
                    WHEN 'DEF' THEN 9
                    ELSE 10
                END
            """,
            {"owner": resolve_owner(owner), "week": week},
        )

        lineup = []
        for row in rows:
            lineup.append(
                {
                    "slot": row["slot"],
                    "player_name": row["player_name"],
                    "position": row["position"],
                    "projected_points": round(row["mu"], 1),
                }
            )

        return jsonify(lineup)
    except Exception as e:
        print(f"Error getting lineup: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@odds_bp.route("/api/teams")
@login_required
def get_teams():
    try:
        week = get_current_week()
        league_id = get_league_id_for_week(week)
        if not league_id:
            return jsonify({"teams": []})

        rows = query_analytics(
            """
            SELECT r.roster_id, u.username, u.display_name
            FROM sleeper_rosters r
            LEFT JOIN sleeper_users u ON r.owner_id = u.user_id
            WHERE r.league_id = :league_id
            ORDER BY r.roster_id
            """,
            {"league_id": league_id},
        )

        teams = []
        for row in rows:
            username = row["username"]
            display_name = row["display_name"]
            roster_id = row["roster_id"]

            raw_label = display_name or username or f"Team {roster_id}"
            label = display_name_for(raw_label)
            slug = username or display_name

            if slug:
                teams.append({"label": label, "slug": slug, "roster_id": roster_id})

        return jsonify({"teams": teams})
    except Exception as e:
        print(f"[TEAMS ERROR] User {current_user.id} - Exception: {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"teams": []})


@odds_bp.route("/api/team_distribution")
@login_required
def get_team_distribution():
    """Return KDE density curves for the selected team and (optionally) an opponent.

    When `opponent` is supplied, win probability is computed live from paired
    Monte Carlo samples (sims aligned by sim_id), letting users compare any
    two teams — not just the scheduled matchup. Without `opponent`, the
    endpoint falls back to the scheduled matchup from betting_odds_matchup_ml
    and reports the published moneylines.
    """
    team_slug = request.args.get("team")
    if not team_slug:
        return jsonify({"error": "Team parameter required"}), 400

    week_param = request.args.get("week", type=int)
    week = week_param or get_current_week()

    raw_owner = resolve_owner(team_slug)
    team_samples = montecarlo.get_samples(raw_owner, week)
    if team_samples is None:
        return jsonify({"error": f"No simulation data for {raw_owner} in week {week}"}), 404

    opponent_slug = request.args.get("opponent")
    if opponent_slug and opponent_slug != team_slug:
        opp_pair = _opponent_from_slug(opponent_slug, week, team_samples)
    else:
        opp_pair = _opponent_from_matchup(raw_owner, week)

    sample_sets = [team_samples] + ([opp_pair["samples"]] if opp_pair else [])
    x_grid = montecarlo.shared_x_grid(*sample_sets)

    team_win_prob = opp_pair["team_win_prob"] if opp_pair else None
    team_ml = opp_pair["team_ml"] if opp_pair else None

    response = {
        "week": week,
        "x": x_grid.tolist(),
        "team": _team_payload(raw_owner, display_name_for(raw_owner), team_samples, x_grid, team_win_prob, team_ml),
    }
    if opp_pair:
        response["opponent"] = _team_payload(
            opp_pair["owner"],
            opp_pair["label"],
            opp_pair["samples"],
            x_grid,
            opp_pair["opp_win_prob"],
            opp_pair["opp_ml"],
        )
        response["margin"] = _margin_payload(team_samples, opp_pair["samples"])

    return jsonify(response)


def _margin_payload(team_samples, opp_samples):
    """Empirical tail probabilities of the paired margin on [-40, +40].

    The left arm is P(margin <= x), answering "opponent wins by >= |x|".
    The right arm is P(margin >= x), answering "team wins by >= x".
    """
    margin = np.sort(team_samples - opp_samples)
    x = np.linspace(-40, 40, 161)
    cdf = np.searchsorted(margin, x, side="right") / margin.size
    left = x <= 0
    right = x >= 0
    return {
        "left_x": x[left].tolist(),
        "left_y": cdf[left].tolist(),
        "right_x": x[right].tolist(),
        "right_y": (1 - cdf[right]).tolist(),
    }


def _opponent_from_slug(opponent_slug, week, team_samples):
    """Build an opponent record for an arbitrary team chosen by the user.

    Win probability is computed empirically from paired sims (sim_id-aligned),
    so it stays honest even when the pair isn't the scheduled matchup.
    Moneylines are omitted because the published ones only apply to the
    scheduled pair.
    """
    opp_raw = resolve_owner(opponent_slug)
    opp_samples = montecarlo.get_samples(opp_raw, week)
    if opp_samples is None or len(opp_samples) != len(team_samples):
        return None

    team_wins = float((team_samples > opp_samples).mean())
    ties = float((team_samples == opp_samples).mean())
    return {
        "owner": opp_raw,
        "samples": opp_samples,
        "label": display_name_for(opp_raw),
        "team_win_prob": team_wins,
        "opp_win_prob": 1.0 - team_wins - ties,
        "team_ml": None,
        "opp_ml": None,
    }


def _opponent_from_matchup(raw_owner, week):
    """Look up the scheduled opponent for the team and inherit published odds."""
    league_id = get_league_id_for_week(week)
    roster_rows = query_analytics(
        """
        SELECT r.roster_id
        FROM sleeper_rosters r
        LEFT JOIN sleeper_users u ON r.owner_id = u.user_id
        WHERE r.league_id = :league_id
          AND (u.username = :owner OR u.display_name = :owner)
        """,
        {"league_id": league_id, "owner": raw_owner},
    )
    if not roster_rows:
        return None
    team_roster_id = roster_rows[0]["roster_id"]

    matchup_rows = query_analytics(
        """
        SELECT team1_id, team1_win_prob, team1_ml,
               team2_id, team2_win_prob, team2_ml
        FROM betting_odds_matchup_ml
        WHERE week = :week AND (team1_id = :rid OR team2_id = :rid)
        """,
        {"week": week, "rid": team_roster_id},
    )
    if not matchup_rows:
        return None
    matchup = matchup_rows[0]

    if matchup["team1_id"] == team_roster_id:
        opp_id = matchup["team2_id"]
        team_wp, opp_wp = matchup["team1_win_prob"], matchup["team2_win_prob"]
        team_ml, opp_ml = matchup["team1_ml"], matchup["team2_ml"]
    else:
        opp_id = matchup["team1_id"]
        team_wp, opp_wp = matchup["team2_win_prob"], matchup["team1_win_prob"]
        team_ml, opp_ml = matchup["team2_ml"], matchup["team1_ml"]

    opp_owner_rows = query_analytics(
        """
        SELECT u.username, u.display_name
        FROM sleeper_rosters r
        LEFT JOIN sleeper_users u ON r.owner_id = u.user_id
        WHERE r.roster_id = :rid AND r.league_id = :league_id
        """,
        {"rid": opp_id, "league_id": league_id},
    )
    if not opp_owner_rows:
        return None

    opp_raw = opp_owner_rows[0]["username"] or opp_owner_rows[0]["display_name"]
    opp_samples = montecarlo.get_samples(opp_raw, week)
    if opp_samples is None:
        return None

    return {
        "owner": opp_raw,
        "samples": opp_samples,
        "label": display_name_for(opp_raw),
        "team_win_prob": team_wp,
        "opp_win_prob": opp_wp,
        "team_ml": team_ml,
        "opp_ml": opp_ml,
    }


def _team_payload(owner, label, samples, x_grid, win_prob, moneyline):
    p10, p50, p90 = np.percentile(samples, [10, 50, 90])
    sorted_samples = np.sort(samples)
    return {
        "owner": owner,
        "label": label,
        "y": montecarlo.density_curve(samples, x_grid).tolist(),
        "cdf": (np.searchsorted(sorted_samples, x_grid, side="right") / samples.size).tolist(),
        "mean": float(samples.mean()),
        "p10": float(p10),
        "p50": float(p50),
        "p90": float(p90),
        "win_prob": win_prob,
        "moneyline": moneyline,
    }


@odds_bp.route("/api/team_players")
@login_required
def get_team_players():
    team_owner = request.args.get("team")

    if not team_owner:
        return jsonify({"error": "Team parameter required"}), 400

    try:
        week = get_current_week()
        league_id = get_league_id_for_week(week)
        if not league_id:
            return jsonify({"error": "Team not found"}), 404

        raw_owner = resolve_owner(team_owner)
        roster_rows = query_analytics(
            """
            SELECT r.roster_id, r.starters, r.players
            FROM sleeper_rosters r
            LEFT JOIN sleeper_users u ON r.owner_id = u.user_id
            WHERE r.league_id = :league_id
              AND (u.username = :team_owner OR u.display_name = :team_owner)
            """,
            {"league_id": league_id, "team_owner": raw_owner},
        )

        if not roster_rows:
            return jsonify({"error": "Team not found"}), 404

        roster_id = roster_rows[0]["roster_id"]

        player_rows = query_analytics(
            """
            SELECT sleeper_player_id, first_name, last_name, position, mu, var, starting_status
            FROM projections_rosters
            WHERE roster_id = :roster_id AND week = :week
            ORDER BY
                CASE position
                    WHEN 'QB' THEN 1
                    WHEN 'RB' THEN 2
                    WHEN 'WR' THEN 3
                    WHEN 'TE' THEN 4
                    WHEN 'K' THEN 5
                    WHEN 'DEF' THEN 6
                    ELSE 7
                END,
                mu DESC
            """,
            {"roster_id": roster_id, "week": week},
        )

        if not player_rows:
            lineup_rows = query_analytics(
                """
                SELECT player_name, position, mu, var
                FROM team_lineups
                WHERE roster_id = :roster_id AND week = :week
                    AND slot IN ('QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'K', 'DEF')
                ORDER BY
                    CASE slot
                        WHEN 'QB' THEN 1
                        WHEN 'RB1' THEN 2
                        WHEN 'RB2' THEN 3
                        WHEN 'WR1' THEN 4
                        WHEN 'WR2' THEN 5
                        WHEN 'TE' THEN 6
                        WHEN 'FLEX' THEN 7
                        WHEN 'K' THEN 8
                        WHEN 'DEF' THEN 9
                        ELSE 10
                    END
                """,
                {"roster_id": roster_id, "week": week},
            )

            starters = []
            for row in lineup_rows:
                player_name = row["player_name"] or ""
                first_name, _, last_name = player_name.partition(" ")
                starters.append(
                    {
                        "player_first_name": first_name,
                        "player_last_name": last_name,
                        "position": row["position"],
                        "mu": float(row["mu"]) if row["mu"] is not None else None,
                        "var": float(row["var"]) if row["var"] is not None else None,
                    }
                )

            return jsonify({"starters": starters, "bench": []})

        starters = []
        bench = []

        for row in player_rows:
            player_data = {
                "player_first_name": row["first_name"] or "",
                "player_last_name": row["last_name"] or "",
                "position": row["position"],
                "mu": float(row["mu"]) if row["mu"] is not None else None,
                "var": float(row["var"]) if row["var"] is not None else None,
            }

            if row["starting_status"] and str(row["starting_status"]).strip():
                starters.append(player_data)
            else:
                bench.append(player_data)

        bench.sort(
            key=lambda x: (
                {"QB": 1, "RB": 2, "WR": 3, "TE": 4, "K": 5, "DEF": 6}.get(x["position"], 7),
                -(x["mu"] if x["mu"] is not None else 0),
            )
        )

        return jsonify({"starters": starters, "bench": bench})

    except Exception as e:
        print(f"[TEAM_PLAYERS ERROR] {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"starters": [], "bench": []})
