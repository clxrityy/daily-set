from app import crud, models, game
from sqlmodel import SQLModel, create_engine, Session


def test_session_rotation_invalidates_token(tmp_path):
    db = tmp_path / 'test.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # create anonymous session
        board = game.daily_board('2025-08-30')
        gs = crud.create_session(s, None, '2025-08-30', board)
        assert gs.id is not None
        # sign token using current per-session secret
        token = crud.sign_session_token(s, gs.id)
        assert token is not None
        # verify token is valid
        sid = crud.verify_session_token(s, token)
        assert sid == gs.id
        # rotate the session secret
        new = crud.rotate_session_secret(s, gs.id)
        assert new is not None
        # old token should now be invalid
        old_ok = crud.verify_session_token(s, token)
        assert old_ok is None
        # new token signed after rotation should be valid
        new_token = crud.sign_session_token(s, gs.id)
        assert new_token is not None
        assert crud.verify_session_token(s, new_token) == gs.id
