# --- Import smoke tests ---


def test_all_scrapers_importable():
    from backend.scrapers.scraper_espn import ESPNScraper
    from backend.scrapers.scraper_fanduel import FanDuelScraper
    from backend.scrapers.scraper_fantasypros import FantasyProsScraper
    from backend.scrapers.scraper_firstdown import FirstDownStudioScraper
    from backend.scrapers.scraper_sleeper import SleeperScraper
    from backend.scrapers.scraper_sleeper_league import SleeperLeagueScraper

    assert ESPNScraper is not None
    assert FanDuelScraper is not None
    assert FantasyProsScraper is not None
    assert FirstDownStudioScraper is not None
    assert SleeperScraper is not None
    assert SleeperLeagueScraper is not None


def test_projections_db_importable():
    from backend.scrapers.database import ProjectionsDB

    assert ProjectionsDB is not None


def test_sleeper_scraper_instantiates():
    from backend.scrapers.scraper_sleeper import SleeperScraper

    scraper = SleeperScraper(db_path="nonexistent.db")
    assert scraper.source == "sleeper.com"
    assert scraper.session is not None


# --- ESPN utility method tests ---


def test_espn_parse_player_name():
    from backend.scrapers.scraper_espn import ESPNScraper

    parse = ESPNScraper._parse_player_name
    assert parse(None, "Patrick Mahomes", "QB") == ("Patrick", "Mahomes")
    assert parse(None, "Travis Kelce", "TE") == ("Travis", "Kelce")
    assert parse(None, "", "QB") == ("", "")


def test_espn_parse_player_name_dst():
    from backend.scrapers.scraper_espn import ESPNScraper

    parse = ESPNScraper._parse_player_name
    assert parse(None, "Kansas City", "D/ST") == ("Kansas City", "Defense")
    assert parse(None, "San Francisco", "DST") == ("San Francisco", "Defense")


def test_espn_map_team_name():
    from backend.scrapers.scraper_espn import ESPNScraper

    mapper = ESPNScraper._map_team_name
    assert mapper(None, "Chiefs") == "KC"
    assert mapper(None, "49ers") == "SF"
    assert mapper(None, "Ravens") == "BAL"
    assert mapper(None, "Packers") == "GB"


# --- FanDuel utility method tests ---


def test_fanduel_parse_player_name():
    from backend.scrapers.scraper_fanduel import FanDuelScraper

    scraper = FanDuelScraper(headless=True)
    assert scraper._parse_player_name("Patrick Mahomes") == ("Patrick", "Mahomes")
    assert scraper._parse_player_name("Patrick Mahomes (Q)") == ("Patrick", "Mahomes")
    assert scraper._parse_player_name("Christian McCaffrey (O)") == ("Christian", "McCaffrey")
    assert scraper._parse_player_name("") == ("", "")


# --- Sleeper utility method tests ---


def test_sleeper_parse_player_name():
    from backend.scrapers.scraper_sleeper import SleeperScraper

    scraper = SleeperScraper(db_path="nonexistent.db")
    assert scraper._parse_player_name("Patrick Mahomes") == ("Patrick", "Mahomes")
    assert scraper._parse_player_name("Odell Beckham Jr") == ("Odell", "Beckham Jr")
    assert scraper._parse_player_name("") == ("", "")


def test_sleeper_calculate_fantasy_points():
    from backend.scrapers.scraper_sleeper import SleeperScraper

    scraper = SleeperScraper(db_path="nonexistent.db")

    # QB stat line: 300 pass yds, 2 pass TDs, 1 INT, 30 rush yds
    # 300*0.04 + 2*4 + 1*(-2) + 30*0.1 = 12 + 8 - 2 + 3 = 21.0
    qb_stats = {"pass_yd": 300, "pass_td": 2, "pass_int": 1, "rush_yd": 30}
    assert scraper._calculate_fantasy_points(qb_stats, "QB") == 21.0

    # RB stat line: 100 rush yds, 1 rush TD, 3 receptions, 25 rec yds
    # 100*0.1 + 1*6 + 3*1.0 + 25*0.1 = 10 + 6 + 3 + 2.5 = 21.5
    rb_stats = {"rush_yd": 100, "rush_td": 1, "rec": 3, "rec_yd": 25}
    assert scraper._calculate_fantasy_points(rb_stats, "RB") == 21.5

    # Empty stats
    assert scraper._calculate_fantasy_points({}, "QB") == 0.0
    assert scraper._calculate_fantasy_points(None, "QB") == 0.0


# --- ProjectionsDB tests ---


def test_projections_db_insert_and_retrieve(tmp_path):
    from backend.scrapers.database import ProjectionsDB

    db_path = str(tmp_path / "test_projections.db")
    pdb = ProjectionsDB(db_path=db_path)

    pdb.insert_projection(
        source="espn.com",
        week="10",
        first_name="Patrick",
        last_name="Mahomes",
        position="QB",
        projected_points=22.5,
        team="KC",
    )

    results = pdb.get_projections(source="espn.com", week="10")
    assert len(results) == 1
    assert results[0]["player_first_name"] == "Patrick"
    assert results[0]["player_last_name"] == "Mahomes"
    assert results[0]["projected_points"] == 22.5

    pdb.close()


def test_projections_db_position_standardization(tmp_path):
    from backend.scrapers.database import ProjectionsDB

    db_path = str(tmp_path / "test_positions.db")
    pdb = ProjectionsDB(db_path=db_path)

    assert pdb._standardize_position("D/ST") == "DST"
    assert pdb._standardize_position("DEF") == "DST"
    assert pdb._standardize_position("FB") == "RB"
    assert pdb._standardize_position("QB") == "QB"
    assert pdb._standardize_position("wr") == "WR"

    pdb.close()
