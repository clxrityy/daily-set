from sqlmodel import Session, create_engine, select as sqlmodel_select, col
from passlib.context import CryptContext
from . import models
from datetime import datetime, timezone
from sqlalchemy import func, select as sa_select
import json
from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional
from . import models
import hmac
import hashlib
import os

# secret for signing session tokens; override with SESSION_SECRET env var in production
_SECRET = os.environ.get('SESSION_SECRET', 'dev-secret-change-me')


def sign_session_token(db_session: Session, sid: str) -> Optional[str]:
    """Sign a session id using the session's per-session secret.

    Returns the token "sid.sig" or None if the session doesn't exist.
    """
    gs = db_session.get(models.GameSession, sid)
    if not gs:
        return None
    secret = gs.session_secret or _SECRET
    sig = hmac.new(secret.encode(), sid.encode(), hashlib.sha256).hexdigest()
    return f"{sid}.{sig}"


def sign_player_token(db_session: Session, pid: int) -> Optional[str]:
    """Sign a player id into a token for cookie-based persistent identity."""
    # simple HMAC of pid using global secret
    if pid is None:
        return None
    # Utilize session: ensure the player exists before signing
    try:
        if db_session.get(models.Player, pid) is None:
            return None
    except Exception:
        return None
    val = str(pid)
    sig = hmac.new(_SECRET.encode(), val.encode(), hashlib.sha256).hexdigest()
    return f"{val}.{sig}"


def verify_player_token(db_session: Session, token: str) -> Optional[int]:
    try:
        pid_s, sig = token.rsplit('.', 1)
    except Exception:
        return None
    expected = hmac.new(_SECRET.encode(), pid_s.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        pid = int(pid_s)
    except Exception:
        return None
    # Utilize session: ensure the player exists
    try:
        if db_session.get(models.Player, pid) is None:
            return None
    except Exception:
        return None
    return pid


def create_anonymous_player(session: Session) -> models.Player:
    # create a lightweight player record without password so we can persist identity
    uname = f"anon-{uuid.uuid4().hex[:8]}"
    p = models.Player(username=uname, password_hash="")
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def verify_session_token(db_session: Session, token: str) -> Optional[str]:
    """Verify a session token using the per-session secret.

    Returns the session id (sid) when valid, otherwise None.
    """
    try:
        sid, sig = token.rsplit('.', 1)
    except Exception:
        return None
    gs = db_session.get(models.GameSession, sid)
    if not gs:
        return None
    secret = gs.session_secret or _SECRET
    expected = hmac.new(secret.encode(), sid.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, sig):
        return sid
    return None

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = None


def create_player(session: Session, username: str, password: str):
    q = session.exec(sqlmodel_select(models.Player).where(models.Player.username == username)).first()
    if q:
        return None
    h = pwd.hash(password)
    p = models.Player(username=username, password_hash=h)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def get_player_by_username(session: Session, username: str):
    return session.exec(sqlmodel_select(models.Player).where(models.Player.username == username)).first()


def record_time(session: Session, player_id: int, date: str, seconds: int):
    comp = models.Completion(player_id=player_id, date=date, seconds=seconds, completed_at=datetime.now(timezone.utc))
    session.add(comp)
    session.commit()
    
    # Invalidate leaderboard cache for this date
    try:
        from .cache import invalidate_leaderboard_cache
        invalidate_leaderboard_cache(date)
    except ImportError:
        pass  # Cache module not available
    
    return comp


def create_session(session: Session, player_id: Optional[int], date: str, board, ttl_minutes: int = 60):
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    sess_secret = uuid.uuid4().hex
    gs = models.GameSession(
        id=sid,
        player_id=player_id,
        date=date,
        board_json=json.dumps(board),
        start_ts=now,
        finished=False,
        expires_at=now + timedelta(minutes=ttl_minutes),
        session_secret=sess_secret,
        last_rotated=now,
    )
    session.add(gs)
    session.commit()
    session.refresh(gs)
    return gs


def rotate_session_secret(session: Session, sid: str) -> Optional[str]:
    gs = session.get(models.GameSession, sid)
    if not gs:
        return None
    new_secret = uuid.uuid4().hex
    gs.session_secret = new_secret
    gs.last_rotated = datetime.now(timezone.utc)
    session.add(gs)
    session.commit()
    session.refresh(gs)
    return new_secret


def get_session_by_id(session: Session, sid: str):
    return session.get(models.GameSession, sid)


def finish_session(session: Session, sid: str):
    gs = session.get(models.GameSession, sid)
    if not gs:
        return None
    gs.finished = True
    session.add(gs)
    session.commit()
    session.refresh(gs)
    return gs


def get_leaderboard(session: Session, date: str, limit: int = 10):
    """Return list of {username, best, completed_at} where completed_at corresponds to the best time.
    If multiple completions share the same best seconds for a player, pick the earliest completed_at.
    """
    best_subq = (
        sa_select(
            col(models.Completion.player_id).label('pid'),
            func.min(models.Completion.seconds).label('best')
        )
        .where(models.Completion.date == date)
        .group_by(models.Completion.player_id)
    ).subquery()

    stmt = (
        sa_select(
            models.Player.username,
            best_subq.c.best,
            func.min(models.Completion.completed_at).label('completed_at')
        )
        .join(best_subq, models.Player.id == best_subq.c.pid)
        .join(
            models.Completion,
            (models.Completion.player_id == best_subq.c.pid)
            & (models.Completion.seconds == best_subq.c.best)
            & (models.Completion.date == date)
        )
        .group_by(models.Player.username, best_subq.c.best)
        .order_by(best_subq.c.best)
        .limit(limit)
    )
    res = session.execute(stmt)
    rows = res.fetchall()
    leaders = []
    for r in rows:
        username = r[0]
        best = int(r[1]) if r[1] is not None else None
        completed_at = r[2]
        leaders.append({
            'username': username,
            'best': best,
            'completed_at': completed_at.isoformat() if completed_at else None,
        })
    return leaders


def has_completed(session: Session, player_id: int, date: str) -> bool:
    """Return True if the player has at least one completion for the given date."""
    if player_id is None:
        return False
    row = session.exec(
        sqlmodel_select(models.Completion.id)
        .where(models.Completion.player_id == player_id)
        .where(models.Completion.date == date)
        .limit(1)
    ).first()
    return row is not None


def get_player_daily_status(session: Session, player_id: int, date: str):
    """Return dict with keys: seconds (best), completed_at (earliest for best), placement (1-indexed).
    Returns None if the player has no completion for the date.
    """
    if player_id is None:
        return None
    # Best seconds for this player/date
    best_val = session.execute(
        sa_select(func.min(models.Completion.seconds))
        .where(models.Completion.player_id == player_id)
        .where(models.Completion.date == date)
    ).scalar()
    if best_val is None:
        return None
    best_secs = int(best_val)

    # Placement: count how many players have a strictly better (lower) best time
    best_subq = (
        sa_select(
            col(models.Completion.player_id).label('pid'),
            func.min(models.Completion.seconds).label('best')
        )
        .where(models.Completion.date == date)
        .group_by(models.Completion.player_id)
    ).subquery()
    better_count = session.execute(
        sa_select(func.count())
        .where(best_subq.c.best < best_secs)
    ).scalar() or 0
    placement = int(better_count) + 1

    # Earliest completion timestamp for the best time
    completed_at = session.execute(
        sa_select(func.min(models.Completion.completed_at))
        .where(models.Completion.player_id == player_id)
        .where(models.Completion.date == date)
        .where(models.Completion.seconds == best_secs)
    ).scalar()

    return {
        'seconds': best_secs,
        'completed_at': completed_at.isoformat() if completed_at else None,
        'placement': placement,
    }
