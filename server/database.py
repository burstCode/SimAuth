from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from config import _base_dir, config

_db_path = _base_dir() / config.db_path
engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


def get_db():
    with Session(engine) as session:
        yield session


def init_db():
    Base.metadata.create_all(engine)
