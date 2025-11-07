from datetime import datetime
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional

class Base(DeclarativeBase):
    pass

class User(UserMixin, Base):
    __tablename__ = 'users'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    account_balance: Mapped[float] = mapped_column(Float, default=1000.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    bets: Mapped[list["Bet"]] = relationship(back_populates="user")
    weekly_stats: Mapped[list["WeeklyStats"]] = relationship(back_populates="user")

class OAuth(OAuthConsumerMixin, Base):
    __tablename__ = 'oauth'
    
    user_id: Mapped[str] = mapped_column(String, ForeignKey(User.id))
    browser_session_key: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped["User"] = relationship()

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Bet(Base):
    __tablename__ = 'bets'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('users.id'), nullable=False)
    bet_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    odds: Mapped[str] = mapped_column(String, nullable=False)
    potential_win: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default='pending')
    result: Mapped[float] = mapped_column(Float, default=0.0)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    user: Mapped["User"] = relationship(back_populates="bets")

class WeeklyStats(Base):
    __tablename__ = 'weekly_stats'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('users.id'), nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    starting_balance: Mapped[float] = mapped_column(Float, nullable=False)
    ending_balance: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, nullable=False)
    bets_placed: Mapped[int] = mapped_column(Integer, default=0)
    bets_won: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    user: Mapped["User"] = relationship(back_populates="weekly_stats")
    
    __table_args__ = (UniqueConstraint('user_id', 'week', name='uq_user_week'),)
