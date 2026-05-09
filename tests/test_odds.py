from routes.helpers import get_team_mapping, query_analytics


def test_query_analytics_returns_dicts(seeded_analytics, betting_period):
    rows = query_analytics(
        "SELECT owner FROM betting_odds_team_ou WHERE week = :week",
        {"week": 10},
    )
    assert len(rows) == 2
    assert isinstance(rows[0], dict)
    assert "owner" in rows[0]


def test_query_analytics_empty_result(seeded_analytics, betting_period):
    rows = query_analytics(
        "SELECT * FROM betting_odds_team_ou WHERE week = :week",
        {"week": 999},
    )
    assert rows == []


def test_get_team_mapping(seeded_analytics, betting_period):
    mapping = get_team_mapping(10)
    assert mapping[1] == "Alice A"
    assert mapping[2] == "Bob B"


def test_get_matchups(client, seeded_analytics, betting_period):
    resp = client.get("/api/matchups")
    data = resp.get_json()

    assert len(data) == 1
    assert data[0]["team1_name"] == "Alice A"
    assert data[0]["team2_name"] == "Bob B"
    assert data[0]["team1_ml"] == "-150"
    assert data[0]["team2_ml"] == "+130"


def test_get_team_performance(client, seeded_analytics, betting_period):
    resp = client.get("/api/team_performance")
    data = resp.get_json()

    assert len(data) == 2
    owners = {d["owner"] for d in data}
    assert "Alice A" in owners
    assert "Bob B" in owners
    assert data[0]["line"] is not None


def test_get_highest_scorer(client, seeded_analytics, betting_period):
    resp = client.get("/api/highest_scorer")
    data = resp.get_json()

    assert len(data) == 2
    assert data[0]["win_prob"] == 35.0
    assert data[0]["odds"] == "+185"


def test_get_lowest_scorer(client, seeded_analytics, betting_period):
    resp = client.get("/api/lowest_scorer")
    data = resp.get_json()

    assert len(data) == 2
    assert data[0]["win_prob"] == 30.0
    assert data[0]["owner"] == "Bob B"


def test_get_first_place(client, seeded_analytics, betting_period):
    resp = client.get("/api/first_place")
    data = resp.get_json()

    assert len(data) == 2
    assert data[0]["owner"] == "Alice A"
    assert data[0]["odds"] == "-120"


def test_get_ammad_playoff(client, seeded_analytics, betting_period):
    resp = client.get("/api/ammad_playoff")
    data = resp.get_json()

    assert len(data) == 2
    assert data[0]["win_prob"] == 80.0


def test_get_lineup(client, seeded_analytics, betting_period):
    resp = client.get("/api/lineup/Alice A")
    data = resp.get_json()

    assert len(data) == 3
    assert data[0]["slot"] == "QB"
    assert data[0]["player_name"] == "Patrick Mahomes"
    assert data[0]["projected_points"] == 22.5


def test_get_teams(logged_in_client, seeded_analytics, betting_period):
    resp = logged_in_client.get("/api/teams")
    data = resp.get_json()

    assert len(data["teams"]) == 2
    slugs = [t["slug"] for t in data["teams"]]
    assert "alice" in slugs
    assert "bob" in slugs
    assert slugs.count("alice") == 1


def test_get_team_players(logged_in_client, seeded_analytics, betting_period):
    resp = logged_in_client.get("/api/team_players?team=alice")
    data = resp.get_json()

    assert len(data["starters"]) == 1
    assert data["starters"][0]["player_first_name"] == "Patrick"
    assert len(data["bench"]) == 1
    assert data["bench"][0]["player_last_name"] == "Player"
    assert data["starters"][0]["player_last_name"] != "League"


def test_get_team_players_falls_back_to_current_week_lineup(logged_in_client, seeded_analytics, betting_period):
    resp = logged_in_client.get("/api/team_players?team=bob")
    data = resp.get_json()

    assert len(data["starters"]) == 1
    assert data["starters"][0]["player_first_name"] == "Josh"
    assert data["starters"][0]["player_last_name"] == "Allen"
    assert data["starters"][0]["mu"] == 21.0
    assert data["bench"] == []


def test_matchups_empty_week(client, analytics_tables, betting_period):
    resp = client.get("/api/matchups")
    data = resp.get_json()
    assert data == []


def test_team_players_missing_param(logged_in_client, seeded_analytics, betting_period):
    resp = logged_in_client.get("/api/team_players")
    assert resp.status_code == 400


def test_team_players_not_found(logged_in_client, seeded_analytics, betting_period):
    resp = logged_in_client.get("/api/team_players?team=nonexistent")
    assert resp.status_code == 404
