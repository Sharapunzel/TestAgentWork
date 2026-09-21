from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models import ImportStatus, LogEntry, LogImport
from app.persistence.database import create_session_factory
from app.persistence.repository import SqlAlchemyLogRepository
from tests.conftest import migrate_database, sqlite_url


def make_import(import_id: UUID | None = None) -> LogImport:
    return LogImport(
        id=import_id or uuid4(),
        original_filename="access.log",
        status=ImportStatus.PROCESSING,
        started_at=datetime(2026, 9, 21, 10, 30, tzinfo=UTC),
    )


def make_entry(
    import_id: UUID,
    *,
    occurred_at: datetime | None = None,
    request_path: str = "/путь",
) -> LogEntry:
    return LogEntry(
        id=None,
        import_id=import_id,
        occurred_at=occurred_at or datetime(2026, 9, 21, 10, 31, tzinfo=UTC),
        remote_addr="192.0.2.10",
        method="GET",
        request_path=request_path,
        request_protocol="HTTP/1.1",
        status_code=200,
        body_bytes_sent=512,
        referer=None,
        user_agent="Тестовый агент",
        raw_line='192.0.2.10 - - [date] "GET /путь HTTP/1.1" 200 512',
    )


def test_import_round_trip(session: Session) -> None:
    repository = SqlAlchemyLogRepository(session)
    expected = LogImport(
        id=uuid4(),
        original_filename="журнал.log",
        status=ImportStatus.COMPLETED,
        started_at=datetime(2026, 9, 21, 10, 30, tzinfo=UTC),
        completed_at=datetime(2026, 9, 21, 10, 35, tzinfo=UTC),
        total_lines=5,
        accepted_lines=4,
        rejected_lines=1,
        failure_code=None,
    )

    repository.add_import(expected)
    session.commit()

    assert repository.get_import(expected.id) == expected


def test_entry_round_trip_normalizes_time_to_utc(session: Session) -> None:
    repository = SqlAlchemyLogRepository(session)
    log_import = make_import()
    repository.add_import(log_import)
    source_time = datetime(2026, 9, 21, 15, 31, tzinfo=timezone(timedelta(hours=5)))
    expected = make_entry(log_import.id, occurred_at=source_time)
    expected.referer = "https://example.test/источник"
    expected.user_agent = None

    repository.add_entries([expected])
    session.commit()
    actual = repository.list_entries(log_import.id)[0]

    assert actual.id is not None
    assert actual.occurred_at == datetime(2026, 9, 21, 10, 31, tzinfo=UTC)
    assert actual.remote_addr == expected.remote_addr
    assert actual.method == expected.method
    assert actual.request_path == expected.request_path
    assert actual.request_protocol == expected.request_protocol
    assert actual.status_code == expected.status_code
    assert actual.body_bytes_sent == expected.body_bytes_sent
    assert actual.referer == expected.referer
    assert actual.user_agent is None
    assert actual.raw_line == expected.raw_line


def test_entries_are_isolated_and_stably_ordered(session: Session) -> None:
    repository = SqlAlchemyLogRepository(session)
    first_import = make_import()
    second_import = make_import()
    repository.add_import(first_import)
    repository.add_import(second_import)
    later = datetime(2026, 9, 21, 10, 32, tzinfo=UTC)
    earlier = datetime(2026, 9, 21, 10, 31, tzinfo=UTC)
    repository.add_entries(
        [
            make_entry(first_import.id, occurred_at=later, request_path="/later"),
            make_entry(first_import.id, occurred_at=earlier, request_path="/earlier"),
        ]
    )
    repository.add_entries([make_entry(second_import.id, request_path="/other")])
    session.commit()

    assert [entry.request_path for entry in repository.list_entries(first_import.id)] == [
        "/earlier",
        "/later",
    ]
    assert [entry.request_path for entry in repository.list_entries(second_import.id)] == [
        "/other"
    ]


def test_mixed_import_batch_is_rejected(session: Session) -> None:
    repository = SqlAlchemyLogRepository(session)

    with pytest.raises(ValueError, match="same import_id"):
        repository.add_entries([make_entry(uuid4()), make_entry(uuid4())])


def test_delete_import_cascades_entries(session: Session) -> None:
    repository = SqlAlchemyLogRepository(session)
    log_import = make_import()
    repository.add_import(log_import)
    repository.add_entries([make_entry(log_import.id)])
    session.commit()

    assert repository.delete_import(log_import.id) is True
    session.commit()

    assert repository.get_import(log_import.id) is None
    assert repository.list_entries(log_import.id) == []
    assert repository.delete_import(log_import.id) is False


def test_rollback_discards_uncommitted_changes(tmp_path) -> None:
    database_url = sqlite_url(tmp_path / "rollback.sqlite")
    migrate_database(database_url)
    factory = create_session_factory(database_url)
    log_import = make_import()

    with factory() as first_session:
        repository = SqlAlchemyLogRepository(first_session)
        repository.add_import(log_import)
        assert repository.get_import(log_import.id) == log_import
        first_session.rollback()

    with factory() as second_session:
        repository = SqlAlchemyLogRepository(second_session)
        assert repository.get_import(log_import.id) is None


@pytest.mark.parametrize(
    ("column", "value"),
    [("status", "unknown"), ("total_lines", -1)],
)
def test_import_database_constraints_reject_invalid_values(
    session: Session, column: str, value: str | int
) -> None:
    values: dict[str, str | int] = {
        "id": str(uuid4()),
        "original_filename": "access.log",
        "status": "processing",
        "started_at": "2026-09-21 10:30:00",
        "total_lines": 0,
        "accepted_lines": 0,
        "rejected_lines": 0,
    }
    values[column] = value

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                """
                INSERT INTO log_imports (
                    id, original_filename, status, started_at,
                    total_lines, accepted_lines, rejected_lines
                ) VALUES (
                    :id, :original_filename, :status, :started_at,
                    :total_lines, :accepted_lines, :rejected_lines
                )
                """
            ),
            values,
        )
