import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import hashlib
import secrets

class UsersDB:
    """Database for user accounts and betting."""
    
    def __init__(self, db_path: str = "backend/data/databases/users.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        """Create database tables for users and bets."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                account_balance REAL DEFAULT 1000.0,
                total_pnl REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bet_type TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                odds TEXT NOT NULL,
                potential_win REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                result REAL DEFAULT 0,
                week INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settled_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week INTEGER NOT NULL,
                starting_balance REAL NOT NULL,
                ending_balance REAL NOT NULL,
                pnl REAL NOT NULL,
                bets_placed INTEGER DEFAULT 0,
                bets_won INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, week),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        self.conn.commit()
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            salt, pwd_hash = password_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except:
            return False
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> Optional[int]:
        """Create a new user account with $1000 starting balance."""
        cursor = self.conn.cursor()
        password_hash = self.hash_password(password)
        
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, account_balance)
                VALUES (?, ?, ?, ?, 1000.0)
            """, (username, email, password_hash, full_name))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def authenticate_user(self, username_or_email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users 
            WHERE username = ? OR email = ?
        """, (username_or_email, username_or_email))
        
        user = cursor.fetchone()
        if user and self.verify_password(password, user['password_hash']):
            return dict(user)
        return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    
    def update_balance(self, user_id: int, amount: float):
        """Update user account balance."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET account_balance = account_balance + ?,
                total_pnl = total_pnl + ?
            WHERE id = ?
        """, (amount, amount, user_id))
        self.conn.commit()
    
    def update_weekly_stats(self, user_id: int, week: int, starting_balance: float = None):
        """Update or create weekly stats for a user."""
        cursor = self.conn.cursor()
        user = self.get_user(user_id)
        if not user:
            return
        
        cursor.execute("""
            SELECT * FROM weekly_stats 
            WHERE user_id = ? AND week = ?
        """, (user_id, week))
        existing = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won
            FROM bets 
            WHERE user_id = ? AND week = ?
        """, (user_id, week))
        bet_stats = cursor.fetchone()
        
        ending_balance = user['account_balance']
        
        if existing:
            pnl = ending_balance - existing['starting_balance']
            bets_won = bet_stats['won'] if bet_stats['won'] else 0
            
            cursor.execute("""
                UPDATE weekly_stats 
                SET ending_balance = ?, pnl = ?, bets_placed = ?, bets_won = ?
                WHERE user_id = ? AND week = ?
            """, (ending_balance, pnl, bet_stats['total'], bets_won, user_id, week))
        else:
            if starting_balance is None:
                starting_balance = user['account_balance']
            pnl = ending_balance - starting_balance
            bets_won = bet_stats['won'] if bet_stats['won'] else 0
            
            cursor.execute("""
                INSERT INTO weekly_stats (user_id, week, starting_balance, ending_balance, pnl, bets_placed, bets_won)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, week, starting_balance, ending_balance, pnl, 
                  bet_stats['total'], bets_won))
        
        self.conn.commit()
    
    def place_bet(self, user_id: int, bet_type: str, description: str, 
                  amount: float, odds: str, potential_win: float, week: int = None) -> Optional[int]:
        """Place a bet and update weekly stats."""
        cursor = self.conn.cursor()
        
        user = self.get_user(user_id)
        if not user or user['account_balance'] < amount:
            return None
        
        if week is None:
            week = 10
        
        starting_balance_before_bet = user['account_balance']
        
        cursor.execute("""
            INSERT INTO bets (user_id, bet_type, description, amount, odds, potential_win, week)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, bet_type, description, amount, odds, potential_win, week))
        
        self.update_balance(user_id, -amount)
        self.update_weekly_stats(user_id, week, starting_balance_before_bet)
        self.conn.commit()
        return cursor.lastrowid
    
    def get_user_bets(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's betting history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM bets 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def settle_bet(self, bet_id: int, won: bool):
        """Settle a bet and update weekly stats."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bets WHERE id = ?", (bet_id,))
        bet = cursor.fetchone()
        
        if not bet or bet['status'] != 'pending':
            return
        
        result = bet['potential_win'] if won else -bet['amount']
        
        cursor.execute("""
            UPDATE bets 
            SET status = ?, result = ?, settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, ('won' if won else 'lost', result, bet_id))
        
        if won:
            self.update_balance(bet['user_id'], bet['potential_win'])
        
        self.update_weekly_stats(bet['user_id'], bet['week'])
        self.conn.commit()
    
    def get_weekly_stats(self, user_id: int, week: int) -> Optional[Dict]:
        """Get user's weekly stats."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM weekly_stats 
            WHERE user_id = ? AND week = ?
        """, (user_id, week))
        stats = cursor.fetchone()
        return dict(stats) if stats else None
    
    def get_all_weekly_stats(self, user_id: int) -> List[Dict]:
        """Get all weekly stats for a user."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM weekly_stats 
            WHERE user_id = ? 
            ORDER BY week DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
