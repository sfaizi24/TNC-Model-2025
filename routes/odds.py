import sqlite3

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from routes.helpers import (
    LEAGUE_DB_PATH,
    ODDS_DB_PATH,
    PROJECTIONS_DB_PATH,
    get_current_week,
    get_team_mapping,
)

odds_bp = Blueprint('odds', __name__)


@odds_bp.route('/api/matchups')
def get_matchups():
    try:
        week = get_current_week()
        team_mapping = get_team_mapping(week)

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM betting_odds_matchup_ml
                WHERE week = ?
                ORDER BY matchup
            """, (week,))

            matchups = []
            for row in cursor.fetchall():
                team1_owner = team_mapping.get(row['team1_id'], f"Team {row['team1_id']}")
                team2_owner = team_mapping.get(row['team2_id'], f"Team {row['team2_id']}")

                matchups.append({
                    'matchup': f"{team1_owner} vs {team2_owner}",
                    'original_matchup': row['matchup'],
                    'team1_id': row['team1_id'],
                    'team1_name': team1_owner,
                    'team1_win_prob': row['team1_win_prob'],
                    'team1_ml': row['team1_ml'],
                    'team2_id': row['team2_id'],
                    'team2_name': team2_owner,
                    'team2_win_prob': row['team2_win_prob'],
                    'team2_ml': row['team2_ml']
                })

        return jsonify(matchups)
    except Exception as e:
        print(f"Error getting matchups: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/team_performance')
def get_team_performance():
    try:
        week = get_current_week()

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM betting_odds_team_ou
                WHERE week = ?
                ORDER BY owner
            """, (week,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'team_id': row['team_id'],
                    'owner': row['owner'],
                    'line': row['line'],
                    'over_prob': row['over_prob'],
                    'under_prob': row['under_prob']
                })

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting team performance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/highest_scorer')
def get_highest_scorer():
    try:
        week = get_current_week()

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT owner, probability, odds
                FROM betting_odds_highest_scorer
                WHERE week = ?
                ORDER BY probability DESC
            """, (week,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'owner': row['owner'],
                    'win_prob': round(row['probability'] * 100, 1),
                    'odds': row['odds']
                })

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting highest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/lowest_scorer')
def get_lowest_scorer():
    try:
        week = get_current_week()

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT owner, probability, odds
                FROM betting_odds_lowest_scorer
                WHERE week = ?
                ORDER BY probability DESC
            """, (week,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'owner': row['owner'],
                    'win_prob': round(row['probability'] * 100, 1),
                    'odds': row['odds']
                })

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting lowest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/first_place')
def get_first_place():
    try:
        week = get_current_week()

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT owner, probability, american_odds
                FROM betting_odds_first_place
                WHERE week = ?
                ORDER BY probability DESC
            """, (week,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'owner': row['owner'],
                    'win_prob': round(row['probability'] * 100, 1),
                    'odds': row['american_odds']
                })

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting first place: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/ammad_playoff')
def get_ammad_playoff():
    try:
        week = get_current_week()

        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT owner, probability, american_odds
                FROM betting_odds_make_playoffs
                WHERE week = ?
                ORDER BY probability DESC
            """, (week,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'owner': row['owner'],
                    'win_prob': round(row['probability'] * 100, 1),
                    'odds': row['american_odds']
                })

        return jsonify(teams)
    except Exception as e:
        print(f"Error getting ammad playoff: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/lineup/<owner>')
def get_lineup(owner):
    try:
        week = get_current_week()

        with sqlite3.connect(PROJECTIONS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT slot, player_name, position, mu
                FROM team_lineups
                WHERE owner = ? AND week = ?
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
            """, (owner, week))

            lineup = []
            for row in cursor.fetchall():
                lineup.append({
                    'slot': row['slot'],
                    'player_name': row['player_name'],
                    'position': row['position'],
                    'projected_points': round(row['mu'], 1)
                })

        return jsonify(lineup)
    except Exception as e:
        print(f"Error getting lineup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@odds_bp.route('/api/teams')
@login_required
def get_teams():
    print(f"[TEAMS REQUEST] User: {current_user.id} ({current_user.username})")
    try:
        print(f"[TEAMS] Connecting to database: {LEAGUE_DB_PATH}")
        conn = sqlite3.connect(LEAGUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.roster_id, u.username, u.display_name
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            ORDER BY r.roster_id
        """)

        raw_results = cursor.fetchall()
        print(f"[TEAMS] Database returned {len(raw_results)} rows")

        teams = []
        for row in raw_results:
            username = row['username']
            display_name = row['display_name']
            roster_id = row['roster_id']

            label = display_name or username or f"Team {roster_id}"
            slug = username or display_name

            if slug:
                teams.append({
                    'label': label,
                    'slug': slug,
                    'roster_id': roster_id
                })
            else:
                print(f"[TEAMS WARNING] Skipping roster_id {roster_id} - no slug (username={username}, display_name={display_name})")

        conn.close()
        print(f"[TEAMS SUCCESS] Returning {len(teams)} teams to user {current_user.id}")
        return jsonify({'teams': teams})
    except Exception as e:
        print(f"[TEAMS ERROR] User {current_user.id} - Exception: {type(e).__name__}: {str(e)}")
        print(f"[TEAMS ERROR] Database path: {LEAGUE_DB_PATH}")
        import traceback
        traceback.print_exc()
        return jsonify({'teams': []})


@odds_bp.route('/api/team_players')
@login_required
def get_team_players():
    team_owner = request.args.get('team')
    print(f"[TEAM_PLAYERS REQUEST] User: {current_user.id} ({current_user.username}), Team: {team_owner}")

    if not team_owner:
        print(f"[TEAM_PLAYERS ERROR] User {current_user.id} - Missing team parameter")
        return jsonify({'error': 'Team parameter required'}), 400

    try:
        print(f"[TEAM_PLAYERS] Connecting to database: {LEAGUE_DB_PATH}")
        league_conn = sqlite3.connect(LEAGUE_DB_PATH)
        league_conn.row_factory = sqlite3.Row
        league_cursor = league_conn.cursor()

        league_cursor.execute("""
            SELECT r.roster_id, r.starters, r.players
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE u.username = ? OR u.display_name = ?
        """, (team_owner, team_owner))

        roster = league_cursor.fetchone()
        if not roster:
            print(f"[TEAM_PLAYERS ERROR] User {current_user.id} - Team '{team_owner}' not found in database")
            league_conn.close()
            return jsonify({'error': 'Team not found'}), 404

        roster_id = roster['roster_id']

        league_cursor.execute("""
            SELECT sleeper_player_id, first_name, last_name, position, mu, var, starting_status
            FROM projections_rosters
            WHERE roster_id = ?
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
        """, (roster_id,))

        starters = []
        bench = []

        for row in league_cursor.fetchall():
            player_data = {
                'player_first_name': row['first_name'] or '',
                'player_last_name': row['last_name'] or '',
                'position': row['position'],
                'mu': float(row['mu']) if row['mu'] is not None else None,
                'var': float(row['var']) if row['var'] is not None else None
            }

            if row['starting_status'] and str(row['starting_status']).strip():
                starters.append(player_data)
            else:
                bench.append(player_data)

        league_conn.close()

        bench.sort(key=lambda x: (
            {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'K': 5, 'DEF': 6}.get(x['position'], 7),
            -(x['mu'] if x['mu'] is not None else 0)
        ))

        print(f"[TEAM_PLAYERS SUCCESS] User {current_user.id} - Team '{team_owner}' (roster_id={roster_id}): {len(starters)} starters, {len(bench)} bench")
        return jsonify({'starters': starters, 'bench': bench})

    except Exception as e:
        print(f"[TEAM_PLAYERS ERROR] User {current_user.id} - Exception for team '{team_owner}': {type(e).__name__}: {str(e)}")
        print(f"[TEAM_PLAYERS ERROR] Database path: {LEAGUE_DB_PATH}")
        import traceback
        traceback.print_exc()
        return jsonify({'starters': [], 'bench': []})
