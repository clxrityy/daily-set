from sqlmodel import create_engine, SQLModel
from . import models


def init_db(path='sqlite:///./set.db'):
    engine = create_engine(path, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    print('db initialized at', path)


if __name__ == '__main__':
    init_db()
