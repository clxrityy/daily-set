from app import crud, models, game
from sqlmodel import SQLModel, create_engine, Session


def test_leaderboard_aggregation(tmp_path):
    db = tmp_path / 'test.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # create players
        p1 = models.Player(username='alice', password_hash='x')
        p2 = models.Player(username='bob', password_hash='y')
        s.add(p1); s.add(p2); s.commit(); s.refresh(p1); s.refresh(p2)
        # record completions
        assert p1.id is not None
        assert p2.id is not None
        crud.record_time(s, p1.id, '2025-08-30', 30)
        crud.record_time(s, p1.id, '2025-08-30', 25)
        crud.record_time(s, p2.id, '2025-08-30', 40)
        # leaderboard
        leaders = crud.get_leaderboard(s, '2025-08-30', limit=10)
        assert leaders[0]['username'] == 'alice'
        assert leaders[0]['best'] == 25
