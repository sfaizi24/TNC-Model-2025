from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint
from database import db

# Replit Auth User Model - ID is String (Replit user ID)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    
    account_balance = db.Column(db.Float, default=1000.0)
    total_pnl = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# OAuth table for Replit Auth
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey('users.id'))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

# Betting tables
class Bet(db.Model):
    __tablename__ = 'bets'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    bet_type = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    odds = db.Column(db.String, nullable=False)
    potential_win = db.Column(db.Float, nullable=False)
    status = db.Column(db.String, default='pending')
    result = db.Column(db.Float, default=0.0)
    week = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    settled_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship(User, backref='bets')

class WeeklyStats(db.Model):
    __tablename__ = 'weekly_stats'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    starting_balance = db.Column(db.Float, nullable=False)
    ending_balance = db.Column(db.Float, nullable=False)
    pnl = db.Column(db.Float, nullable=False)
    bets_placed = db.Column(db.Integer, default=0)
    bets_won = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship(User, backref='weekly_stats')
    
    __table_args__ = (UniqueConstraint('user_id', 'week', name='uq_user_week'),)
