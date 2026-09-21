from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class ImportStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LogImport:
    id: UUID
    original_filename: str
    status: ImportStatus
    started_at: datetime
    completed_at: datetime | None = None
    total_lines: int = 0
    accepted_lines: int = 0
    rejected_lines: int = 0
    failure_code: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        if self.completed_at is not None:
            _require_aware(self.completed_at, "completed_at")


@dataclass
class LogEntry:
    id: int | None
    import_id: UUID
    occurred_at: datetime
    remote_addr: str
    method: str
    request_path: str
    request_protocol: str
    status_code: int
    body_bytes_sent: int
    referer: str | None
    user_agent: str | None
    raw_line: str

    def __post_init__(self) -> None:
        _require_aware(self.occurred_at, "occurred_at")
