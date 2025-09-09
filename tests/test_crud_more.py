from sqlmodel import SQLModel, create_engine, Session
from app import crud, models


def setup_db(tmp_path):
    db = tmp_path / 'crud_more.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine
    return engine


def test_player_token_sign_and_verify(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        p = crud.create_player(s, "bob", "GoodPass1")
        assert p is not None and p.id is not None
        pid = int(p.id)
        token = crud.sign_player_token(s, pid)
        assert token and "." in token
        pid2 = crud.verify_player_token(s, token)
        assert pid2 == pid

        # Tamper token -> verify fails
        parts = token.split('.')
        bad = parts[0] + '.deadbeef'
        assert crud.verify_player_token(s, bad) is None


def test_session_token_sign_verify_and_rotate(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        # Create a session first
        p = crud.create_player(s, "carol", "GoodPass1")
        assert p is not None and p.id is not None
        gs = crud.create_session(s, int(p.id), "2025-09-09", board=[1,2,3])
        assert gs is not None and gs.id is not None
        tok = crud.sign_session_token(s, str(gs.id))
        assert tok and "." in tok
        sid = crud.verify_session_token(s, tok)
        assert sid == str(gs.id)

    # Rotate secret invalidates old tokens
    new_secret = crud.rotate_session_secret(s, str(gs.id))
    assert isinstance(new_secret, str) and len(new_secret) > 0
    assert crud.verify_session_token(s, tok) is None


def test_leaderboard_and_status(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        p1 = crud.create_player(s, "dave", "GoodPass1")
        p2 = crud.create_player(s, "erin", "GoodPass1")
        assert p1 and p1.id is not None and p2 and p2.id is not None
        date = "2025-09-09"
        crud.record_time(s, int(p1.id), date, 80)
        crud.record_time(s, int(p2.id), date, 70)
        crud.record_time(s, int(p1.id), date, 60)

        leaders = crud.get_leaderboard(s, date, limit=5)
        assert leaders and leaders[0]["best"] == 60

        st1 = crud.get_player_daily_status(s, int(p1.id), date)
        st2 = crud.get_player_daily_status(s, int(p2.id), date)
        assert st1["seconds"] == 60 and st1["placement"] in (1, 2) # pyright: ignore[reportOptionalSubscript]
        assert st2["seconds"] == 70 and st2["placement"] in (1, 2) # pyright: ignore[reportOptionalSubscript]
