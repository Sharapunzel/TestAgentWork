from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.persistence.database import create_session_factory

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def migrate_database(database_url: str, revision: str = "head") -> None:
    config = Config(BACKEND_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    database_url = sqlite_url(tmp_path / "test.sqlite")
    migrate_database(database_url)
    factory = create_session_factory(database_url)
    with factory() as database_session:
        yield database_session
