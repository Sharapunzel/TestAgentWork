from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.conftest import BACKEND_ROOT, sqlite_url


def test_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "migration.sqlite")
    config = Config(BACKEND_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"alembic_version", "log_entries", "log_imports"} == set(
        inspector.get_table_names()
    )
    assert {
        "ix_log_entries_import_method",
        "ix_log_entries_import_occurred",
        "ix_log_entries_import_status",
    } == {index["name"] for index in inspector.get_indexes("log_entries")}
    foreign_keys = inspector.get_foreign_keys("log_entries")
    assert foreign_keys[0]["options"] == {"ondelete": "CASCADE"}

    command.downgrade(config, "base")

    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


def test_explicit_url_takes_priority_over_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel_url = sqlite_url(tmp_path / "sentinel.sqlite")
    migration_url = sqlite_url(tmp_path / "migration.sqlite")
    sentinel_engine = create_engine(sentinel_url)
    with sentinel_engine.begin() as connection:
        connection.execute(text("CREATE TABLE sentinel_marker (value TEXT NOT NULL)"))
        connection.execute(
            text("INSERT INTO sentinel_marker (value) VALUES ('unchanged')")
        )
    monkeypatch.setenv("NLE_DATABASE_URL", sentinel_url)
    config = Config(BACKEND_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", migration_url)

    command.upgrade(config, "head")
    migration_engine = create_engine(migration_url)
    assert {"alembic_version", "log_entries", "log_imports"} == set(
        inspect(migration_engine).get_table_names()
    )
    command.downgrade(config, "base")
    migration_engine.dispose()

    assert inspect(sentinel_engine).get_table_names() == ["sentinel_marker"]
    with sentinel_engine.connect() as connection:
        assert connection.scalar(text("SELECT value FROM sentinel_marker")) == "unchanged"
    sentinel_engine.dispose()


def test_environment_url_is_used_without_explicit_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = sqlite_url(tmp_path / "environment.sqlite")
    monkeypatch.setenv("NLE_DATABASE_URL", database_url)
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert {"alembic_version", "log_entries", "log_imports"} == set(
        inspect(engine).get_table_names()
    )
    command.downgrade(config, "base")
    engine.dispose()


def test_migration_requires_a_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NLE_DATABASE_URL", raising=False)
    config = Config(BACKEND_ROOT / "alembic.ini")

    with pytest.raises(RuntimeError, match="Set NLE_DATABASE_URL"):
        command.upgrade(config, "head")
