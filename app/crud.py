from sqlmodel import Session, create_engine, select as sqlmodel_select, col
from passlib.context import CryptContext
from . import models
from datetime import datetime, timezone
from sqlalchemy import func, select as sa_select, desc
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


def get_active_session_for_player_date(session: Session, player_id: Optional[int], date: str):
    """Return the most recent unfinished session for this player/date if any."""
    if player_id is None:
        return None
    return session.exec(
        sqlmodel_select(models.GameSession)
        .where(models.GameSession.player_id == player_id)
        .where(models.GameSession.date == date)
        .where(models.GameSession.finished == False)  # noqa: E712
        .order_by(desc(models.GameSession.start_ts))
    ).first()


def finish_session(session: Session, sid: str):
    gs = session.get(models.GameSession, sid)
    if not gs:
        return None
    gs.finished = True
    session.add(gs)
    session.commit()
    session.refresh(gs)
    return gs


def get_leaderboard(session: Session, date: str, limit: int | None = 10):
    """Return list of {username, best, completed_at, sets_found, effective}.
    - best: minimum seconds for the date
    - completed_at: earliest timestamp for that best
    - sets_found: total FoundSet rows for the date
    - effective: best adjusted by a 12% decrease per additional set beyond the first
                 effective = best * (0.88 ** max(0, sets_found - 1))
    Sorted ascending by effective; ties broken by best then completed_at.
    If limit is None, return all rows; otherwise return up to limit.
    """
    # Subquery: best seconds per player for the date
    best_subq = (
        sa_select(
            col(models.Completion.player_id).label('pid'),
            func.min(models.Completion.seconds).label('best')
        )
        .where(models.Completion.date == date)
        .group_by(models.Completion.player_id)
    ).subquery()

    # Subquery: count of found sets per player for the date
    sets_subq = (
        sa_select(
            col(models.FoundSet.player_id).label('pid'),
            func.count(models.FoundSet.id).label('sets_found')
        )
        .where(models.FoundSet.date == date)
        .group_by(models.FoundSet.player_id)
    ).subquery()

    # Join to get username, best, earliest completed_at for that best, and sets_found (COALESCE 0)
    stmt = (
        sa_select(
            models.Player.username,
            best_subq.c.best,
            func.min(models.Completion.completed_at).label('completed_at'),
            func.coalesce(sets_subq.c.sets_found, 0).label('sets_found')
        )
        .join(best_subq, models.Player.id == best_subq.c.pid)
        .join(
            models.Completion,
            (models.Completion.player_id == best_subq.c.pid)
            & (models.Completion.seconds == best_subq.c.best)
            & (models.Completion.date == date)
        )
        .join(sets_subq, sets_subq.c.pid == best_subq.c.pid, isouter=True)
        .group_by(models.Player.username, best_subq.c.best, sets_subq.c.sets_found)
    )

    rows = session.execute(stmt).all()
    leaders = []
    for username, best, completed_at, sets_found in rows:
        best_int = int(best) if best is not None else None
        sets_int = int(sets_found or 0)
        # Calculate effective time reduction
        extra = max(0, sets_int - 1)
        effective = None
        if best_int is not None:
            effective = float(best_int) * (0.88 ** extra)
        leaders.append({
            'username': username,
            'best': best_int,
            'completed_at': completed_at.isoformat() if completed_at else None,
            'sets_found': sets_int,
            'effective': effective,
        })
    # Sort by effective asc, then best asc, then completed_at asc
    leaders.sort(key=lambda r: (
        float('inf') if r['effective'] is None else r['effective'],
        float('inf') if r['best'] is None else r['best'],
        '' if r['completed_at'] is None else r['completed_at'],
    ))
    if isinstance(limit, int) and limit > 0:
        return leaders[:limit]
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

    # Sets found for this player/date
    sets_found = session.execute(
        sa_select(func.count(models.FoundSet.id))
        .where(models.FoundSet.player_id == player_id)
        .where(models.FoundSet.date == date)
    ).scalar() or 0

    # Effective time for this player
    extra = max(0, int(sets_found) - 1)
    effective = float(best_secs) * (0.88 ** extra)

    # Placement: compute via effective ranking
    all_leaders = get_leaderboard(session, date, limit=None)
    # Find this player's placement among all by matching best and username
    # We need username to match entries
    username = session.execute(
        sa_select(models.Player.username)
        .where(models.Player.id == player_id)
    ).scalar()
    placement = None
    if username is not None:
        for idx, row in enumerate(all_leaders, start=1):
            if row.get('username') == username:
                placement = idx
                break
    if placement is None:
        placement = 1

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
    'sets_found': int(sets_found),
    'effective': effective,
    }
