from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, _dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, _dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class LogImportModel(Base):
    __tablename__ = "log_imports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_log_imports_status",
        ),
        CheckConstraint("total_lines >= 0", name="ck_log_imports_total_lines"),
        CheckConstraint(
            "accepted_lines >= 0", name="ck_log_imports_accepted_lines"
        ),
        CheckConstraint(
            "rejected_lines >= 0", name="ck_log_imports_rejected_lines"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    total_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String)


class LogEntryModel(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        CheckConstraint(
            "status_code BETWEEN 100 AND 599", name="ck_log_entries_status_code"
        ),
        CheckConstraint(
            "body_bytes_sent >= 0", name="ck_log_entries_body_bytes_sent"
        ),
        Index("ix_log_entries_import_occurred", "import_id", "occurred_at"),
        Index("ix_log_entries_import_status", "import_id", "status_code"),
        Index("ix_log_entries_import_method", "import_id", "method"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("log_imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    remote_addr: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    request_path: Mapped[str] = mapped_column(String, nullable=False)
    request_protocol: Mapped[str] = mapped_column(String, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    body_bytes_sent: Mapped[int] = mapped_column(Integer, nullable=False)
    referer: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)
    raw_line: Mapped[str] = mapped_column(Text, nullable=False)
    log_import: Mapped[LogImportModel] = relationship()
