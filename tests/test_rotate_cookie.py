from app.main import rotate_session
from app import crud, game
from sqlmodel import SQLModel, create_engine, Session
from fastapi import Response, Request
import asyncio


# build a real FastAPI/Starlette Request from a minimal ASGI scope so type checks pass
async def _dummy_receive():
    # include an await to satisfy linters that the function uses async features
    await asyncio.sleep(0)
    return {"type": "http.request"}

def _make_request_with_auth(old_token: str):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {old_token}".encode())],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 5000),
        "scheme": "http",
    }
    return Request(scope, _dummy_receive)


def test_rotate_session_sets_cookie_and_invalidates(tmp_path):
    # setup DB
    db = tmp_path / 'test.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine

    with Session(engine) as s:
        # create session
        board = game.daily_board('2025-08-30')
        gs = crud.create_session(s, None, '2025-08-30', board)
        assert gs.id is not None
        # sign existing token
        old_token = crud.sign_session_token(s, gs.id)
        assert old_token is not None

        # build request and response
        req = _make_request_with_auth(old_token)
        resp = Response()

        # call handler directly (synchronous call is fine)
        result = rotate_session(gs.id, req, resp, session=s)
        assert result == {"session_id": gs.id}
        # check set-cookie header
        sc = resp.headers.get('set-cookie')
        assert sc is not None
        # extract cookie value
        # format: session_token=<val>; Path=/; httponly
        token_part = [p for p in sc.split(';') if p.strip().startswith('session_token=')][0]
        new_token = token_part.split('=', 1)[1]
        assert new_token != old_token

        # verify old token invalid
        assert crud.verify_session_token(s, old_token) is None
        assert crud.verify_session_token(s, new_token) == gs.id
