import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import os

class ProjectionsDB:
    """Light and fast SQLite database for fantasy football projections."""
    
    def __init__(self, db_path: str = "projections.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.create_tables()
    
    def create_tables(self):
        """Create database tables with flexible schema for multiple sources."""
        cursor = self.conn.cursor()
        
        # Main projections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projections (
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
        
        # Add team column if it doesn't exist (for backward compatibility)
        try:
            cursor.execute("ALTER TABLE projections ADD COLUMN team TEXT")
            self.conn.commit()
        except:
            pass  # Column already exists
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_week 
            ON projections(source_website, week)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_name 
            ON projections(player_first_name, player_last_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_position 
            ON projections(position)
        """)
        
        self.conn.commit()
    
    def insert_projection(self, source: str, week: str, first_name: str, 
                         last_name: str, position: str, projected_points: float,
                         team: str = None):
        """Insert or update a single projection."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO projections 
            (source_website, week, player_first_name, player_last_name, position, team, projected_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_website, week, player_first_name, player_last_name, position)
            DO UPDATE SET 
                team = excluded.team,
                projected_points = excluded.projected_points,
                updated_at = CURRENT_TIMESTAMP
        """, (source, week, first_name, last_name, position, team, projected_points))
        
        self.conn.commit()
    
    def insert_projections_batch(self, projections: List[Dict]):
        """Insert multiple projections efficiently."""
        cursor = self.conn.cursor()
        
        data = [
            (p['source'], p['week'], p['first_name'], p['last_name'], 
             p['position'], p.get('team'), p['projected_points'])
            for p in projections
        ]
        
        cursor.executemany("""
            INSERT INTO projections 
            (source_website, week, player_first_name, player_last_name, position, team, projected_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_website, week, player_first_name, player_last_name, position)
            DO UPDATE SET 
                team = excluded.team,
                projected_points = excluded.projected_points,
                updated_at = CURRENT_TIMESTAMP
        """, data)
        
        self.conn.commit()
    
    def get_projections(self, source: Optional[str] = None, 
                       week: Optional[str] = None,
                       position: Optional[str] = None) -> List[Dict]:
        """Retrieve projections with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM projections WHERE 1=1"
        params = []
        
        if source:
            query += " AND source_website = ?"
            params.append(source)
        
        if week:
            query += " AND week = ?"
            params.append(week)
        
        if position:
            query += " AND position = ?"
            params.append(position)
        
        query += " ORDER BY projected_points DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_player_projection(self, first_name: str, last_name: str, 
                             source: str, week: str) -> Optional[Dict]:
        """Get projection for a specific player."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM projections 
            WHERE player_first_name = ? 
            AND player_last_name = ?
            AND source_website = ?
            AND week = ?
        """, (first_name, last_name, source, week))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_week(self, source: str, week: str):
        """Delete all projections for a specific source and week."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM projections 
            WHERE source_website = ? AND week = ?
        """, (source, week))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    with ProjectionsDB() as db:
        # Insert a sample projection
        db.insert_projection(
            source="firstdown.studio",
            week="Week 8",
            first_name="Bijan",
            last_name="Robinson",
            position="RB",
            projected_points=23.7
        )
        
        # Retrieve projections
        projections = db.get_projections(source="firstdown.studio", week="Week 8")
        for proj in projections:
            print(f"{proj['player_first_name']} {proj['player_last_name']} ({proj['position']}): {proj['projected_points']} pts")

