from sqlmodel import create_engine, SQLModel
from . import models
from .logging_utils import get_logger

logger = get_logger("app.init_db")


def init_db(path='sqlite:///./set.db'):
    engine = create_engine(path, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    logger.info("db_initialized", extra={"path": path})


if __name__ == '__main__':
    init_db()
