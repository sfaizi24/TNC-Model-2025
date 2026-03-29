import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from validate_scraping import normalize_week, validate


@pytest.fixture
def temp_db():
    """Create a temporary projections.db with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE projections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_website TEXT NOT NULL,
            week TEXT NOT NULL,
            player_first_name TEXT NOT NULL,
            player_last_name TEXT NOT NULL,
            position TEXT NOT NULL,
            team TEXT,
            projected_points REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_website, week, player_first_name, player_last_name, position)
        )
    """)
    conn.commit()
    conn.close()

    yield db_path
    db_path.unlink(missing_ok=True)


def seed_projections(db_path, source, week, count, positions=None):
    """Insert test projections into the database."""
    positions = positions or ["QB", "RB", "WR", "TE", "K", "DST"]
    conn = sqlite3.connect(str(db_path))
    for i in range(count):
        pos = positions[i % len(positions)]
        conn.execute(
            "INSERT INTO projections (source_website, week, player_first_name, player_last_name, position, projected_points) VALUES (?, ?, ?, ?, ?, ?)",
            (source, week, f"Player{i}", f"Last{i}", pos, 10.0 + i),
        )
    conn.commit()
    conn.close()


# --- normalize_week tests ---


def test_normalize_week_number():
    assert normalize_week("17") == "Week 17"


def test_normalize_week_already_formatted():
    assert normalize_week("Week 17") == "Week 17"


def test_normalize_week_lowercase():
    assert normalize_week("week 10") == "Week 10"


# --- validate tests ---


def test_validate_pass(temp_db):
    seed_projections(temp_db, "sleeper.com", "Week 17", 80)
    seed_projections(temp_db, "espn.com", "Week 17", 60)
    seed_projections(temp_db, "fantasypros.com", "Week 17", 70)

    result = validate(temp_db, "Week 17")
    assert result["status"] == "PASS"
    assert result["total"] == 210
    assert result["sources"] == 3
    assert len(result["missing_positions"]) == 0


def test_validate_fail_few_sources(temp_db):
    seed_projections(temp_db, "sleeper.com", "Week 17", 50)

    result = validate(temp_db, "Week 17")
    assert result["status"] == "FAIL"
    assert result["sources"] == 1


def test_validate_fail_low_count(temp_db):
    seed_projections(temp_db, "sleeper.com", "Week 17", 10)
    seed_projections(temp_db, "espn.com", "Week 17", 10)
    seed_projections(temp_db, "fantasypros.com", "Week 17", 10)

    result = validate(temp_db, "Week 17")
    assert result["status"] == "FAIL"
    assert result["total"] == 30


def test_validate_warn_missing_positions(temp_db):
    # Only QB and RB positions
    seed_projections(temp_db, "sleeper.com", "Week 17", 60, ["QB", "RB"])
    seed_projections(temp_db, "espn.com", "Week 17", 50, ["QB", "RB"])
    seed_projections(temp_db, "fantasypros.com", "Week 17", 50, ["QB", "RB"])

    result = validate(temp_db, "Week 17")
    assert result["status"] == "WARN"
    assert len(result["missing_positions"]) > 0


def test_validate_empty_week(temp_db):
    result = validate(temp_db, "Week 99")
    assert result["status"] == "FAIL"
    assert result["total"] == 0


def test_validate_json_output(temp_db):
    seed_projections(temp_db, "sleeper.com", "Week 17", 80)
    seed_projections(temp_db, "espn.com", "Week 17", 80)
    seed_projections(temp_db, "fantasypros.com", "Week 17", 80)

    result = validate(temp_db, "Week 17")
    serialized = json.dumps(result)
    parsed = json.loads(serialized)

    assert "status" in parsed
    assert "sources" in parsed
    assert "positions" in parsed
    assert "total" in parsed
    assert "missing_sources" in parsed
