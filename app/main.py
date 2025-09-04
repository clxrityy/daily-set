from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import SQLModel, Session, create_engine, select
from . import models, crud, game
from pydantic import BaseModel
from typing import List, Optional
from .deps import get_session

import asyncio
import time
from sqlmodel import Session as SQLSession
import json
from datetime import datetime, timezone

# track websocket connections -> metadata {ws: {'player_id': int|None, 'last_sent': float}}
_WS_CONNECTIONS: dict = {}


async def broadcast_event(event: dict):
    """Enrich event with username and leaderboard snapshot, then send to connected clients with simple per-connection rate limiting."""
    print(f"broadcast_event called with: {event}")  # Debug log
    
    # enrich event if it contains player_id and date
    try:
        if event.get('type') == 'completion' and 'player_id' in event and 'date' in event:
            # lookup username and top leaders
            leaders = []
            uname = None
            try:
                with SQLSession(crud.engine) as s:
                    user = s.get(models.Player, event['player_id'])
                    if user:
                        uname = user.username
                    leaders = crud.get_leaderboard(s, event['date'], limit=5)
            except Exception:
                leaders = []
            event['username'] = uname
            event['leaders'] = leaders
    except Exception:
        pass

    print(f"Enriched event: {event}")  # Debug log
    print(f"Number of WebSocket connections: {len(_WS_CONNECTIONS)}")  # Debug log

    now = time.time()
    dead = []
    for ws, meta in _WS_CONNECTIONS.items():
        try:
            # rate limit per-connection to ~2 messages/sec
            last = meta.get('last_sent', 0)
            if now - last < 0.45:
                print("Rate limiting WebSocket message")  # Debug log
                continue
            print(f"Sending event to WebSocket: {event}")  # Debug log
            await ws.send_json(event)
            meta['last_sent'] = now
        except Exception as e:
            print(f"Error sending to WebSocket: {e}")  # Debug log
            dead.append(ws)
    for d in dead:
        _WS_CONNECTIONS.pop(d, None)

app = FastAPI(title="Daily Set")

# mount static frontend (files are under app/static) using package-relative path
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root():
    # redirect to the static index for convenience
    return RedirectResponse(url="/static/index.html")


@app.get("/health", include_in_schema=False)
def health():
    return JSONResponse({"status": "ok"})


@app.on_event("startup")
def on_startup():
    import os
    db_path = os.getenv("DATABASE_URL", "sqlite:///./set.db")
    engine = create_engine(db_path, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


@app.get("/api/daily")
def get_daily(date: str = "", session: Session = Depends(get_session)):
    # return the deterministic daily board for date (YYYY-MM-DD) or today
    board = game.daily_board(date)
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


class PlayerCreate(BaseModel):
    username: str
    password: str


@app.post("/api/player_json", status_code=201)
def create_player_json(body: PlayerCreate, session: Session = Depends(get_session)):
    p = crud.create_player(session, body.username, body.password)
    if not p:
        raise HTTPException(status_code=400, detail="username exists")
    return {"id": p.id, "username": p.username}


@app.get("/api/leaderboard")
def leaderboard(date: str = "", limit: int = 10, session: Session = Depends(get_session)):
    date = date or game.today_str()
    board = crud.get_leaderboard(session, date, limit)
    return {"date": date, "leaders": board}


@app.get("/api/test_event")
async def test_event():
    """Test endpoint to trigger a broadcast event"""
    print("Test event endpoint called")
    try:
        await broadcast_event({
            'type': 'test',
            'username': 'TestUser',
            'msg': 'Test event from backend endpoint'
        })
        return {"status": "Event broadcast successful"}
    except Exception as e:
        print(f"Error broadcasting test event: {e}")
        return {"status": f"Error: {e}"}


class SubmitSetRequest(BaseModel):
    username: Optional[str]
    indices: List[int]
    date: Optional[str] = None
    seconds: Optional[int] = None
    session_id: Optional[str] = None
    session_token: Optional[str] = None


class StartSessionRequest(BaseModel):
    username: Optional[str] = None
    date: Optional[str] = None


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

    board = game.daily_board(date)
    gs = crud.create_session(session, player_id, date, board)
    start_ts = gs.start_ts.isoformat() if gs.start_ts is not None else None
    token = None
    if gs.id is not None:
        token = crud.sign_session_token(session, gs.id)
        # also set session_token cookie for convenience
        response.set_cookie('session_token', token or '', httponly=True, samesite='lax')
    return {"session_id": gs.id, "session_token": token, "start_ts": start_ts}


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
    secure_cookie = False
    response.set_cookie('session_token', new_token or '', httponly=True, secure=secure_cookie, samesite='lax')
    return {"session_id": session_id}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _WS_CONNECTIONS[ws] = {'player_id': None, 'last_sent': 0}
    try:
        while True:
            # keep connection open; optionally receive pings from client
            await ws.receive_text()
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
    for i in sorted(body.indices, reverse=True):
        b_local.pop(i)
    gs_local.board_json = json.dumps(b_local)

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
def submit_set(body: SubmitSetRequest, session: Session = Depends(get_session)):
    sid = _get_sid_from_body(body, session)
    gs, board, date = _load_session_board(session, body, sid)
    cards = _validate_and_get_cards(body, board)
    _apply_session_changes(session, body, gs, board)
    _maybe_record_standalone(session, body, date)
    return {"valid": True, "cards": cards, "session_id": getattr(gs, 'id', None)}


@app.post("/api/player", status_code=201)
def create_player(username: str, password: str, session: Session = Depends(get_session)):
    p = crud.create_player(session, username, password)
    if not p:
        raise HTTPException(status_code=400, detail="username exists")
    return {"id": p.id, "username": p.username}


@app.post("/api/complete")
def complete_daily(username: str, seconds: int, date: str = "", session: Session = Depends(get_session)):
    date = date or game.today_str()
    p = crud.get_player_by_username(session, username)
    if not p:
        raise HTTPException(status_code=404, detail="player not found")
    player_id = p.id
    if player_id is None:
        raise HTTPException(status_code=500, detail="player has no id")
    crud.record_time(session, player_id, date, seconds)
    try:
        _task = asyncio.create_task(broadcast_event({
            'type': 'completion',
            'player_id': player_id,
            'date': date,
            'seconds': seconds,
        }))
    except Exception:
        pass
    return {"status": "ok"}
