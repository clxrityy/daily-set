from sqlmodel import SQLModel, create_engine, Session
from app import crud, models, game


def setup_db(tmp_path):
    db = tmp_path / 'crudedge.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine
    return engine


def test_token_sign_verify_and_edgecases(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        # Non-existent session
        assert crud.sign_session_token(s, 'nope') is None

        # Create session and sign/verify
        board = game.daily_board('2099-01-02', size=12)
        gs = crud.create_session(s, None, '2099-01-02', board)
        assert gs.id is not None
        sid = str(gs.id)
        tok = crud.sign_session_token(s, sid)
        assert tok and tok.startswith(sid + '.')
        assert crud.verify_session_token(s, tok) == sid

        # Wrong format / wrong sig
        assert crud.verify_session_token(s, 'not_a_token') is None
        bad = tok[:-1] + ('0' if tok[-1] != '0' else '1')
        assert crud.verify_session_token(s, bad) is None

        # Player token edge cases
        assert crud.sign_player_token(s, 999999) is None  # player does not exist

        # Create anonymous player and verify tokens
        p = crud.create_anonymous_player(s)
        assert p.id is not None
        pid = int(p.id)
        ptok = crud.sign_player_token(s, pid)
        assert ptok and ptok.endswith('.' + ptok.split('.', 1)[1])
        assert crud.verify_player_token(s, ptok) == pid
        assert crud.verify_player_token(s, 'badformat') is None
        assert crud.verify_player_token(s, 'abc.def') is None  # non-int id
        # Tamper sig
        tampered = ptok.split('.')
        tampered[1] = tampered[1][:-1] + ('0' if tampered[1][-1] != '0' else '1')
        assert crud.verify_player_token(s, '.'.join(tampered)) is None


def test_session_rotation_and_finish_paths(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        board = game.daily_board('2099-01-03', size=12)
        gs = crud.create_session(s, None, '2099-01-03', board)
        assert gs.id is not None
        sid = str(gs.id)

        # Rotate non-existent
        assert crud.rotate_session_secret(s, 'missing') is None

    # Rotate existing, verify old token breaks and new one works
    old_token = crud.sign_session_token(s, sid)
    old_secret = gs.session_secret
    new_secret = crud.rotate_session_secret(s, sid)
    assert new_secret and new_secret != old_secret
    assert crud.verify_session_token(s, old_token) is None # type: ignore
    new_token = crud.sign_session_token(s, sid)
    assert crud.verify_session_token(s, new_token) == sid # type: ignore

    # Finish non-existent
    assert crud.finish_session(s, 'nope') is None


def test_leaderboard_and_status(tmp_path):
    engine = setup_db(tmp_path)
    with Session(engine) as s:
        # Create two users
        p1 = models.Player(username='u1', password_hash='x')
        p2 = models.Player(username='u2', password_hash='y')
        s.add(p1); s.add(p2); s.commit(); s.refresh(p1); s.refresh(p2)
        assert p1.id is not None and p2.id is not None
        p1id = int(p1.id); p2id = int(p2.id)

        # Record completions
        crud.record_time(s, p1id, '2099-01-10', 80)
        crud.record_time(s, p2id, '2099-01-10', 70)
        # Tie for p1 with same best seconds; placement computation still uses best
        crud.record_time(s, p1id, '2099-01-10', 80)

        leaders = crud.get_leaderboard(s, '2099-01-10', limit=5)
        assert leaders[0]['username'] == 'u2'
        assert leaders[0]['best'] == 70

        assert crud.has_completed(s, -1, '2099-01-10') is False
        assert crud.has_completed(s, p1id, '2099-01-10') is True

        status = crud.get_player_daily_status(s, p2id, '2099-01-10')
        assert status and status['seconds'] == 70 and status['placement'] == 1

        status_p1 = crud.get_player_daily_status(s, p1id, '2099-01-10')
        assert status_p1 and status_p1['seconds'] == 80 and status_p1['placement'] == 2

        # Username lookup and duplicate prevention
        u1 = crud.get_player_by_username(s, 'u1')
        assert u1 is not None and u1.id == p1id
        assert crud.create_player(s, 'u1', 'password') is None
