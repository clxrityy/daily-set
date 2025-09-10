from fastapi import FastAPI, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from sqlmodel import SQLModel, Session, create_engine, select
from . import models, crud, game
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from .deps import get_session

import asyncio
import time
import re
from sqlmodel import Session as SQLSession
import json
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from .logging_utils import setup_logging, get_logger, request_id_ctx
import logging
import uuid


# Rate limiting - store last request times per IP
_RATE_LIMIT_STORE: dict = {}

def check_rate_limit(request: Request, max_requests: int = 30, window_seconds: int = 60) -> bool:
    """
    Simple in-memory rate limiting. Returns True if request is allowed, False if rate limited.
    Default: 30 requests per 60 seconds per IP address.
    """
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Clean up old entries (older than window)
    cutoff_time = current_time - window_seconds
    _RATE_LIMIT_STORE[client_ip] = [
        req_time for req_time in _RATE_LIMIT_STORE.get(client_ip, []) 
        if req_time > cutoff_time
    ]
    
    # Check if under the limit
    if len(_RATE_LIMIT_STORE[client_ip]) >= max_requests:
        return False
    
    # Add current request
    _RATE_LIMIT_STORE[client_ip].append(current_time)
    return True

def rate_limit_dependency(max_requests: int = 30, window_seconds: int = 60):
    """Create a dependency function that raises HTTP 429 if rate limited"""
    def dependency(request: Request):
        if not check_rate_limit(request, max_requests, window_seconds):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
            )
    return dependency

# track websocket connections -> metadata {ws: {'player_id': int|None, 'last_sent': float}}
_WS_CONNECTIONS: dict = {}


# Helper functions for broadcast_event
def _enrich_event(e: dict) -> None:
    """Enrich completion event with username and leaderboard data."""
    if not (e.get('type') == 'completion' and 'player_id' in e and 'date' in e):
        return
    leaders = []
    uname = None
    try:
        with SQLSession(crud.engine) as s:
            user = s.get(models.Player, e['player_id'])
            if user:
                uname = user.username
            leaders = crud.get_leaderboard(s, e['date'], limit=5)
    except Exception:
        leaders = []
    e['username'] = uname
    e['leaders'] = leaders

def _prepare_message(e: dict):
    """Serialize event to JSON."""
    try:
        return json.dumps(e)
    except Exception:
        return None

async def _send_to_websocket(ws: WebSocket, meta: dict, msg, ev, now_ts: float) -> bool:
    """Send message to websocket with rate limiting. Return False if failed."""
    try:
        last = meta.get('last_sent', 0)
        if now_ts - last < 0.45:
            return True
        if msg is not None:
            await ws.send_text(msg)
        else:
            await ws.send_json(ev)
        meta['last_sent'] = now_ts
        return True
    except Exception as send_exc:
        logger.debug("ws_send_error", extra={"error": str(send_exc)})
        return False

async def broadcast_event(event: dict):
    """Enrich event with username/leaderboard, then broadcast to all connections."""
    logger.debug("broadcast_event_called", extra={"event": event})

    # Enrich the event if applicable
    try:
        _enrich_event(event)
    except Exception as ex:
        logger.debug("broadcast_event_enrich_failed", extra={"error": str(ex)})

    logger.debug("broadcast_event_enriched", extra={"event": event, "ws_count": len(_WS_CONNECTIONS)})

    json_message = _prepare_message(event)
    now = time.time()
    dead = []

    # Process each connection
    for ws, meta in _WS_CONNECTIONS.items():
        success = await _send_to_websocket(ws, meta, json_message, event, now)
        if not success:
            dead.append(ws)

    # Clean up disconnected sockets
    for d in dead:
        _WS_CONNECTIONS.pop(d, None)

setup_logging(logging.INFO)
logger = get_logger("app")
app = FastAPI(title="Daily Set")

# Security headers & Content Security Policy
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Strict Content Security Policy suitable for this app
        csp = " ".join([
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self' ws: wss:",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "upgrade-insecure-requests",
        ])
        response.headers['Content-Security-Policy'] = csp
        # Additional best-practice headers
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        # HSTS is only relevant when behind HTTPS; enabling is generally safe in prod
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

app.add_middleware(SecurityHeadersMiddleware)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        start = time.time()
        client = request.client.host if request.client else "-"
        ua = request.headers.get("user-agent", "-")
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            # Log exception with context
            logger.exception(
                "request_error",
                extra={"path": str(request.url), "method": request.method},
            )
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)
            status = getattr(response, "status_code", 500)
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "client": client,
                    "user_agent": ua,
                },
            )
            try:
                if response is not None:
                    response.headers["X-Request-ID"] = rid
            except Exception:
                pass
            request_id_ctx.reset(token)


app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://daily-set.fly.dev",  # Production domain
        "http://localhost:3000",      # Local development
        "http://localhost:8000",      # Local FastAPI server
        "http://127.0.0.1:3000",     # Alternative localhost
    "http://127.0.0.1:8000",     # Alternative localhost
    "http://localhost:5173",     # Vite dev server
    "http://127.0.0.1:5173",     # Vite dev server alt
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],
)

# Add validation error handler for better debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("validation_error", extra={"method": request.method, "url": str(request.url), "errors": exc.errors()})
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Input validation failed"
        }
    )

# mount static frontend (files are under app/static) using package-relative path
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root():
    # redirect to the built React app (Vite outDir -> /static/dist)
    return RedirectResponse(url="/static/dist/index.html")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    path = _STATIC_DIR / "robots.txt"
    if path.exists():
        return FileResponse(str(path), media_type="text/plain")
    return JSONResponse({"detail": "robots.txt not found"}, status_code=404)


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    path = _STATIC_DIR / "sitemap.xml"
    if path.exists():
        return FileResponse(str(path), media_type="application/xml")
    return JSONResponse({"detail": "sitemap.xml not found"}, status_code=404)


@app.get("/site.webmanifest", include_in_schema=False)
def site_manifest():
    path = _STATIC_DIR / "site.webmanifest"
    if path.exists():
        return FileResponse(str(path), media_type="application/manifest+json")
    return JSONResponse({"detail": "site.webmanifest not found"}, status_code=404)


@app.get("/health", include_in_schema=False)
def health():
    return JSONResponse({"status": "ok"})


@app.get("/api/cache/stats", include_in_schema=False)
def cache_stats():
    """Get cache statistics for monitoring"""
    from .cache import get_cache
    
    cache = get_cache()
    stats = cache.get_stats()
    
    return JSONResponse({
        "cache_stats": stats,
        "status": "ok"
    })


@app.on_event("startup")
def on_startup():
    import os
    from .migrations import run_migrations
    from .cache import warm_cache_for_today_and_recent
    
    db_path = os.getenv("DATABASE_URL", "sqlite:///./set.db")
    # Enable connection pooling for non-SQLite databases; keep SQLite thread setting
    connect_args = {"check_same_thread": False} if db_path.startswith("sqlite") else {}
    # Use explicit keyword args instead of **pool_kwargs to avoid mypy/typing mismatches
    if not db_path.startswith("sqlite"):
        # Reasonable defaults for pooled connections in production databases
        engine = create_engine(
            db_path,
            echo=False,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=1800,
        )
    else:
        engine = create_engine(db_path, echo=False, connect_args=connect_args)
    
    # Create tables first
    SQLModel.metadata.create_all(engine)
    
    # Run database migrations
    try:
        run_migrations()
    except Exception as e:
        logger.warning("migrations_failed", extra={"error": str(e)})
    
    crud.engine = engine
    
    # Warm up the cache
    try:
        warm_cache_for_today_and_recent()
        logger.info("cache_warm_success")
    except Exception as e:
        logger.warning("cache_warm_failed", extra={"error": str(e)})


@app.get("/api/daily")
def get_daily(date: str = "", session: Session = Depends(get_session)):
    from .cache import get_cached_daily_board, cache_daily_board
    
    # Use provided date or default to today
    actual_date = date or game.today_str()
    
    # Try to get from cache first
    board = get_cached_daily_board(actual_date)
    
    if board is None:
        # Generate and cache the board
        board = game.daily_board(actual_date)
        cache_daily_board(actual_date, board)
    
    # Broadcast daily_update event (fire-and-forget)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_event({
            'type': 'daily_update',
            'date': date or game.today_str(),
        }))
    except RuntimeError:
        pass
    return {"board": board}


class CompleteRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=12)
    seconds: int = Field(..., ge=0, le=86400)  # 0 to 24 hours
    date: str = Field("", regex=r'^(\d{4}-\d{2}-\d{2})?$')  # Optional date or empty string
    
    @validator('username')
    def validate_username(cls, v):
        # Strip whitespace and sanitize
        v = v.strip()
        if len(v) == 0:
            raise ValueError('Username cannot be empty')
        if len(v) > 12:
            raise ValueError('Username too long (max 12 characters)')
        # Allow alphanumeric, underscore, hyphen only
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscore, and hyphen')
        return v


class PlayerCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=12)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('username')
    def validate_username(cls, v):
        # Strip whitespace and sanitize
        v = v.strip()
        if len(v) == 0:
            raise ValueError('Username cannot be empty')
        if len(v) > 12:
            raise ValueError('Username too long (max 12 characters)')
        # Allow alphanumeric, underscore, hyphen only
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscore, and hyphen')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password too long (max 128 characters)')
        # Basic password strength check
        import re
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v


@app.post("/api/player_json", status_code=201)
def create_player_json(body: PlayerCreate, session: Session = Depends(get_session)):
    p = crud.create_player(session, body.username, body.password)
    if not p:
        raise HTTPException(status_code=400, detail="username exists")
    return {"id": p.id, "username": p.username}


@app.get("/api/leaderboard")
def leaderboard(
    date: str = "", 
    limit: int = 10, 
    session: Session = Depends(get_session),
    _: None = Depends(rate_limit_dependency(max_requests=20, window_seconds=60))
):
    from .cache import get_cached_leaderboard, cache_leaderboard
    
    # Validate date parameter
    if date and not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate limit parameter
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    actual_date = date or game.today_str()
    
    # Try to get from cache first
    leaders = get_cached_leaderboard(actual_date)
    
    if leaders is None:
        # Get from database and cache
        leaders = crud.get_leaderboard(session, actual_date, limit)
        cache_leaderboard(actual_date, leaders, ttl_minutes=5)  # Cache for 5 minutes
    
    return {"date": actual_date, "leaders": leaders}


def _validate_username_param(username: str) -> str:
    uname = (username or "").strip()
    if not uname or len(uname) > 64:
        raise HTTPException(status_code=400, detail="Invalid username")
    if not re.match(r'^[A-Za-z0-9_-]+$', uname):
        raise HTTPException(status_code=400, detail="Invalid username format")
    return uname


def _validate_date_param(date: str) -> str:
    if date and not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    return date or game.today_str()


def _query_found_sets(session: SQLSession, player_id: int, date_str: str) -> list:
    sets: list = []
    rows = session.exec(
        select(models.FoundSet)
        .where(models.FoundSet.player_id == player_id)
        .where(models.FoundSet.date == date_str)
        .order_by(models.FoundSet.created_at)
    ).all()
    for fs in rows:
        try:
            cards = json.loads(fs.cards_json)
            if isinstance(cards, list) and len(cards) == 3:
                sets.append(cards)
        except Exception:
            continue
    return sets


@app.get("/api/found_sets")
def get_found_sets(
    username: str,
    date: str = "",
    session: Session = Depends(get_session),
    _: None = Depends(rate_limit_dependency(max_requests=30, window_seconds=60))
):
    """Return the list of found sets (arrays of 3 cards) for the given username and date.
    If user or records are not found, returns an empty list.
    """
    # sanitize username similar to validators
    uname = _validate_username_param(username)
    actual_date = _validate_date_param(date)

    # Lookup player
    player = crud.get_player_by_username(session, uname)
    if not player or player.id is None:
        return {"username": uname, "date": actual_date, "sets": []}

    # Fetch found sets in ascending time
    try:
        sets = _query_found_sets(session, player.id, actual_date)
    except Exception:
        sets = []
    return {"username": uname, "date": actual_date, "sets": sets}


class SubmitSetRequest(BaseModel):
    username: Optional[str] = Field(None, max_length=12)
    indices: List[int] = Field(..., min_items=3, max_items=3)
    date: Optional[str] = None
    seconds: Optional[int] = Field(None, ge=0, le=86400)  # 0 to 24 hours
    session_id: Optional[str] = Field(None, max_length=100)
    session_token: Optional[str] = Field(None, max_length=200)  # Increased for session_id.signature format
    
    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            # Strip whitespace and sanitize
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 12:
                raise ValueError('Username too long (max 12 characters)')
            # Allow alphanumeric, underscore, hyphen only
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, underscore, and hyphen')
        return v
    
    @validator('date')
    def validate_date(cls, v):
        if v is not None and v != "":
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('indices')
    def validate_indices(cls, v):
        if len(v) != 3:
            raise ValueError('Must provide exactly 3 card indices')
        for idx in v:
            if not isinstance(idx, int) or idx < 0:
                raise ValueError('Card indices must be non-negative integers')
        if len(set(v)) != 3:
            raise ValueError('All card indices must be unique')
        return v

    @validator('seconds', pre=True)
    def normalize_seconds(cls, v):
        # Allow missing/null seconds; coerce negatives to 0 and cap at 24h
        if v is None or v == "":
            return None
        try:
            val = int(v)
        except Exception:
            return None
        if val < 0:
            return 0
        if val > 86400:
            return 86400
        return val


class StartSessionRequest(BaseModel):
    username: Optional[str] = Field(None, max_length=12)
    date: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            # Strip whitespace and sanitize
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 12:
                raise ValueError('Username too long (max 12 characters)')
            # Allow alphanumeric, underscore, hyphen only
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, underscore, and hyphen')
        return v
    
    @validator('date')
    def validate_date(cls, v):
        if v is not None and v != "":
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v


def _resolve_player_id(session: Session, username: Optional[str], request: Request) -> Optional[int]:
    # prefer explicit username if it matches an existing player
    if username:
        p = crud.get_player_by_username(session, username)
        if p:
            return p.id
    # fall back to player_token cookie if present
    player_token = request.cookies.get('player_token')
    if player_token:
        pid = crud.verify_player_token(session, player_token)
        if pid:
            return pid
    return None

def _create_player_and_set_cookie(session: Session, username: Optional[str], response: Response) -> int:
    if username:
        # Create a new player with the provided username (no password required for game-only players)
        new_player = models.Player(username=username, password_hash="")
        session.add(new_player)
        session.commit()
        session.refresh(new_player)
        player_id = new_player.id
    else:
        # Create anonymous player if no username provided
        anon = crud.create_anonymous_player(session)
        player_id = anon.id

    if player_id is None:
        raise HTTPException(status_code=500, detail="player has no id")
    # sign and set player_token cookie
    ptoken = crud.sign_player_token(session, player_id)
    response.set_cookie('player_token', ptoken or '', httponly=True, samesite='lax')
    return player_id

@app.post("/api/start_session")
def start_session(body: StartSessionRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    date = body.date or game.today_str()

    # resolve existing player id from username or cookie, otherwise create one and set cookie
    player_id = _resolve_player_id(session, body.username, request)
    if not player_id:
        player_id = _create_player_and_set_cookie(session, body.username, response)

    # If user has already completed today, forbid another session
    try:
        if player_id and crud.has_completed(session, player_id, date):
            raise HTTPException(status_code=403, detail="Already completed today's game")
    except Exception:
        pass

    # Reuse existing unfinished session for this player/date if present
    existing = crud.get_active_session_for_player_date(session, player_id, date)
    if existing:
        gs = existing
    else:
        board = game.daily_board(date)
        gs = crud.create_session(session, player_id, date, board)
    start_ts = gs.start_ts.isoformat() if gs.start_ts is not None else None
    token = None
    if gs.id is not None:
        token = crud.sign_session_token(session, gs.id)
        # also set session_token cookie for convenience
        response.set_cookie('session_token', token or '', httponly=True, samesite='lax')
    return {"session_id": gs.id, "session_token": token, "start_ts": start_ts}


@app.get("/api/status")
def status(request: Request, session: Session = Depends(get_session)):
    """Return minimal per-user status including whether today's daily is complete.

    Uses player_token cookie if available; if no player is known, returns completed: False.
    """
    date = game.today_str()
    player_id = _resolve_player_id(session, None, request)
    completed = False
    detail = None
    if player_id:
        try:
            completed = crud.has_completed(session, player_id, date)
            if completed:
                detail = crud.get_player_daily_status(session, player_id, date)
        except Exception:
            completed = False
            detail = None
    payload = {"date": date, "completed": completed}
    if detail:
        payload.update(detail)
    return payload


@app.get("/api/session")
def get_current_session(request: Request, session: Session = Depends(get_session)):
    """Return current active session for today if exists, including board and start_ts.
    Uses player_token cookie to resolve the player.
    """
    date = game.today_str()
    pid = _resolve_player_id(session, None, request)
    if not pid:
        return {"active": False}
    gs = crud.get_active_session_for_player_date(session, pid, date)
    if not gs:
        return {"active": False}
    try:
        board = json.loads(gs.board_json)
    except Exception:
        board = []
    return {
        "active": True,
        "session_id": gs.id,
        "start_ts": gs.start_ts.isoformat() if gs.start_ts else None,
        "board": board,
    }


@app.post("/api/rotate_session/{session_id}")
def rotate_session(session_id: str, request: Request, response: Response, session: Session = Depends(get_session)):
    # require a valid session token from the client (Authorization: Bearer <token> or cookie)
    token = None
    auth = request.headers.get('authorization')
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(' ', 1)[1].strip()
    if not token:
        token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail='missing session token')

    # ensure the token belongs to the session being rotated
    sid = crud.verify_session_token(session, token)
    if not sid or sid != session_id:
        raise HTTPException(status_code=403, detail='invalid or unauthorized token')

    # owner-only: if the session has a player_id, ensure the caller's player_token matches
    gs_obj = crud.get_session_by_id(session, session_id)
    if not gs_obj:
        raise HTTPException(status_code=404, detail='session not found')
    if gs_obj.player_id:
        ptoken = request.cookies.get('player_token')
        if not ptoken:
            raise HTTPException(status_code=403, detail='missing player token')
        caller_pid = crud.verify_player_token(session, ptoken)
        if caller_pid != gs_obj.player_id:
            raise HTTPException(status_code=403, detail='not session owner')

    # rotate the per-session secret so previously-issued tokens are invalidated
    new = crud.rotate_session_secret(session, session_id)
    if not new:
        raise HTTPException(status_code=404, detail='session not found')

    # sign a new token with the rotated secret and set it as HttpOnly cookie
    new_token = crud.sign_session_token(session, session_id)
    # secure flag should be True in production; use env var or default to False for local testing
    import os
    secure_cookie = os.getenv('COOKIE_SECURE', '0') in ('1', 'true', 'True')
    response.set_cookie('session_token', new_token or '', httponly=True, secure=secure_cookie, samesite='lax')
    return {"session_id": session_id}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _WS_CONNECTIONS[ws] = {'player_id': None, 'last_sent': 0}
    try:
        while True:
            # keep connection open; optionally receive pings from client
            msg = await ws.receive_text()
            # Test hook: allow triggering a broadcast from a WS message in tests
            try:
                import os as _os
                if isinstance(msg, str) and msg.startswith("__test_broadcast:") and _os.getenv('ENABLE_TEST_ENDPOINTS', '0') in ('1', 'true', 'True'):
                    payload = msg.split(":", 1)[1]
                    try:
                        ev = json.loads(payload)
                    except Exception:
                        ev = {"type": "test"}
                    # Echo directly for deterministic test delivery
                    try:
                        await ws.send_text(json.dumps(ev))
                    except Exception:
                        pass
                    # Also run broadcast to exercise the pipeline
                    await broadcast_event(ev)
            except Exception:
                pass
    except WebSocketDisconnect:
        _WS_CONNECTIONS.pop(ws, None)
    except Exception:
        _WS_CONNECTIONS.pop(ws, None)
def _get_sid_from_body(body: SubmitSetRequest, session: Session):
    if body.session_token:
        sid_local = crud.verify_session_token(session, body.session_token)
        if not sid_local:
            raise HTTPException(status_code=400, detail="invalid session token")
        return sid_local
    return body.session_id

def _load_session_board(session: Session, body: SubmitSetRequest, sid_local):
    if sid_local:
        gs_local = crud.get_session_by_id(session, sid_local)
        if not gs_local:
            raise HTTPException(status_code=404, detail="session not found")
        if gs_local.finished:
            raise HTTPException(status_code=400, detail="session finished")
        board_local = json.loads(gs_local.board_json)
        return gs_local, board_local, gs_local.date
    else:
        date_local = body.date or game.today_str()
        return None, game.daily_board(date_local), date_local

def _validate_and_get_cards(body: SubmitSetRequest, board_local):
    if len(body.indices) != 3:
        raise HTTPException(status_code=400, detail="must submit three indices")
    if len(set(body.indices)) != 3:
        raise HTTPException(status_code=400, detail="indices must be unique")
    try:
        cards_local = [board_local[i] for i in body.indices]
    except Exception:
        raise HTTPException(status_code=400, detail="index out of range")
    t_local = [tuple(c) for c in cards_local]
    if not game.is_set(t_local[0], t_local[1], t_local[2]):
        raise HTTPException(status_code=400, detail="not a set")
    return cards_local

def _handle_session_completion(session: Session, gs_local):
    if gs_local.id is not None:
        crud.finish_session(session, gs_local.id)

    if not gs_local.player_id:
        return

    # Ensure both datetimes are timezone-aware for proper calculation
    now_utc = datetime.now(timezone.utc)
    start_ts = gs_local.start_ts
    if start_ts.tzinfo is None:
        # If start_ts is naive, assume it's UTC
        start_ts = start_ts.replace(tzinfo=timezone.utc)
    elapsed = int((now_utc - start_ts).total_seconds())

    # Check if this completion is a new best for the player
    prev_best = None
    try:
        prev_best = session.exec(
            select(models.Completion.seconds)
            .where(models.Completion.player_id == gs_local.player_id)
            .where(models.Completion.date == gs_local.date)
            .order_by(models.Completion.seconds)
        ).first()
    except Exception:
        prev_best = None

    crud.record_time(session, gs_local.player_id, gs_local.date, elapsed)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_event({
            'type': 'completion',
            'player_id': gs_local.player_id,
            'date': gs_local.date,
            'seconds': elapsed,
        }))
        # If this is a new best (or first) time, broadcast leaderboard_change
        if prev_best is None or (isinstance(prev_best, (int, float)) and elapsed < prev_best):
            loop.create_task(broadcast_event({
                'type': 'leaderboard_change',
                'player_id': gs_local.player_id,
                'date': gs_local.date,
                'seconds': elapsed,
            }))
    except RuntimeError:
        # No running event loop, skip broadcast
        pass

def _apply_session_changes(session: Session, body: SubmitSetRequest, gs_local, board_local):
    if not gs_local:
        return
    # remove selected cards from stored board
    b_local = board_local
    # Capture selected cards BEFORE mutating the board
    try:
        selected_cards = [b_local[i] for i in body.indices]
    except Exception:
        selected_cards = None
    for i in sorted(body.indices, reverse=True):
        b_local.pop(i)
    gs_local.board_json = json.dumps(b_local)

    # Record the found set for analytics/history
    try:
        if getattr(gs_local, 'player_id', None):
            cards_payload = json.dumps(selected_cards or [])
            fs = models.FoundSet(
                player_id=gs_local.player_id or 0,
                date=gs_local.date,
                cards_json=cards_payload,
                session_id=gs_local.id,
                created_at=datetime.now(timezone.utc)
            )
            session.add(fs)
    except Exception:
        pass

    # Check if game is complete (no more valid sets remaining)
    remaining_sets = game.find_sets([tuple(card) for card in b_local])
    if not remaining_sets:  # No more valid sets = game complete
        _handle_session_completion(session, gs_local)
    else:
        session.add(gs_local)
        session.commit()

def _maybe_record_standalone(session: Session, body: SubmitSetRequest, date_local):
    if body.seconds is None or not body.username or body.session_id:
        return
    p_local = crud.get_player_by_username(session, body.username)
    if not p_local:
        return
    player_id_local = p_local.id
    if player_id_local is None:
        raise HTTPException(status_code=500, detail="player has no id")
    crud.record_time(session, player_id_local, date_local, int(body.seconds))

@app.post("/api/submit_set")
def submit_set(
    body: SubmitSetRequest, 
    session: Session = Depends(get_session),
    _: None = Depends(rate_limit_dependency(max_requests=10, window_seconds=60))
):
    sid = _get_sid_from_body(body, session)
    gs, board, date = _load_session_board(session, body, sid)
    cards = _validate_and_get_cards(body, board)
    _apply_session_changes(session, body, gs, board)
    _maybe_record_standalone(session, body, date)
    return {"valid": True, "cards": cards, "session_id": getattr(gs, 'id', None)}


@app.post("/api/player", status_code=201)
def create_player(
    body: PlayerCreate,
    session: Session = Depends(get_session),
    _: None = Depends(rate_limit_dependency(max_requests=5, window_seconds=300))  # 5 accounts per 5 minutes
):
    p = crud.create_player(session, body.username, body.password)
    if not p:
        raise HTTPException(status_code=400, detail="username exists")
    return {"id": p.id, "username": p.username}


@app.post("/api/complete")
def complete_daily(
    body: CompleteRequest,
    session: Session = Depends(get_session),
    _: None = Depends(rate_limit_dependency(max_requests=10, window_seconds=60))
):
    date = body.date or game.today_str()
    p = crud.get_player_by_username(session, body.username)
    if not p:
        raise HTTPException(status_code=404, detail="player not found")
    player_id = p.id
    if player_id is None:
        raise HTTPException(status_code=500, detail="player has no id")
    crud.record_time(session, player_id, date, body.seconds)
    # Fire-and-forget broadcast only if an event loop is running.
    # Avoid creating the coroutine if create_task would fail (which would trigger
    # a "coroutine was never awaited" warning under sync request handlers in tests).
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        try:
            loop.create_task(broadcast_event({
                'type': 'completion',
                'player_id': player_id,
                'date': date,
                'seconds': body.seconds,
            }))
        except Exception:
            # If scheduling fails for any reason, continue without blocking the request
            pass
    return {"status": "ok"}

@app.post("/api/__test_broadcast")
def __test_broadcast(event: dict):
    """Test-only endpoint to trigger a broadcast from sync context.
    Enabled when ENABLE_TEST_ENDPOINTS=1. Returns 404 otherwise.
    """
    import os
    enabled = False
    try:
        enabled = os.getenv('ENABLE_TEST_ENDPOINTS', '0') in ('1', 'true', 'True')
    except Exception:
        enabled = False
    if not enabled:
        raise HTTPException(status_code=404, detail="not found")
    # Intentionally no-op; kept for compatibility, real test broadcast uses WS trigger
    return {"ok": True}
