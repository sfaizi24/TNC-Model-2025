"""Read raw Monte Carlo samples for interactive team charts.

Local-only: reads backend/data/databases/montecarlo.db, which is gitignored.
The production publish flow only pushes summary odds, not the 50K-row
simulation tables, so callers must handle a missing file gracefully.
"""

import sqlite3
from pathlib import Path

import numpy as np
from scipy.stats import gaussian_kde

DB_PATH = Path(__file__).resolve().parent.parent / "backend/data/databases/montecarlo.db"


def available_weeks():
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT DISTINCT week FROM monte_carlo_simulations ORDER BY week").fetchall()
    return [row[0] for row in rows]


def get_samples(owner, week):
    """Return simulated point totals for an owner in a given week, ordered by sim_id.

    The sim_id ordering matters when callers want to pair samples across two
    teams (so sim N for team A and sim N for team B reflect the same week-wide
    scenario, e.g. matchup win-probabilities).
    """
    if not DB_PATH.exists():
        return None
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT total_points FROM monte_carlo_simulations WHERE owner = ? AND week = ? ORDER BY sim_id",
            (owner, week),
        ).fetchall()
    if not rows:
        return None
    return np.fromiter((r[0] for r in rows), dtype=np.float64, count=len(rows))


def density_curve(samples, x_grid):
    kde = gaussian_kde(samples)
    return kde(x_grid)


def shared_x_grid(*sample_arrays, n_points=160, padding=0.05):
    """Build a common x-axis covering all input distributions, with light padding."""
    lows = [np.percentile(s, 0.5) for s in sample_arrays if s is not None]
    highs = [np.percentile(s, 99.5) for s in sample_arrays if s is not None]
    lo, hi = min(lows), max(highs)
    pad = (hi - lo) * padding
    return np.linspace(lo - pad, hi + pad, n_points)
