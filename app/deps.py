from sqlmodel import Session
from . import crud


def get_session():
    # simple dependency that yields a session
    with Session(crud.engine) as session:
        yield session
