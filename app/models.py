from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class GameSession(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    player_id: Optional[int] = None
    date: str = ""
    board_json: str = ""
    start_ts: Optional[datetime] = None
    finished: bool = False
    expires_at: Optional[datetime] = None
    session_secret: Optional[str] = None
    last_rotated: Optional[datetime] = None


class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password_hash: str


class Completion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int
    date: str  # YYYY-MM-DD
    seconds: int
    completed_at: Optional[datetime] = None
