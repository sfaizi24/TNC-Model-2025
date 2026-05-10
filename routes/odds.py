from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from routes.helpers import (
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
