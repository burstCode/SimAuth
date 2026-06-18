from sqlalchemy import create_engine, text
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
    _migrate()


def _migrate():
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(participants)"))}
        additions = [
            ("last_name",   "ALTER TABLE participants ADD COLUMN last_name TEXT NOT NULL DEFAULT ''"),
            ("first_name",  "ALTER TABLE participants ADD COLUMN first_name TEXT NOT NULL DEFAULT ''"),
            ("middle_name", "ALTER TABLE participants ADD COLUMN middle_name TEXT"),
        ]
        for col, ddl in additions:
            if col not in cols:
                conn.execute(text(ddl))
        conn.commit()
