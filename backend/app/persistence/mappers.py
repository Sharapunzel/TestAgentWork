from app.domain.models import ImportStatus, LogEntry, LogImport
from app.persistence.models import LogEntryModel, LogImportModel


def import_to_model(log_import: LogImport) -> LogImportModel:
    return LogImportModel(
        id=str(log_import.id),
        original_filename=log_import.original_filename,
        status=log_import.status.value,
        started_at=log_import.started_at,
        completed_at=log_import.completed_at,
        total_lines=log_import.total_lines,
        accepted_lines=log_import.accepted_lines,
        rejected_lines=log_import.rejected_lines,
        failure_code=log_import.failure_code,
    )


def import_to_domain(model: LogImportModel) -> LogImport:
    from uuid import UUID

    return LogImport(
        id=UUID(model.id),
        original_filename=model.original_filename,
        status=ImportStatus(model.status),
        started_at=model.started_at,
        completed_at=model.completed_at,
        total_lines=model.total_lines,
        accepted_lines=model.accepted_lines,
        rejected_lines=model.rejected_lines,
        failure_code=model.failure_code,
    )


def entry_to_model(entry: LogEntry) -> LogEntryModel:
    return LogEntryModel(
        id=entry.id,
        import_id=str(entry.import_id),
        occurred_at=entry.occurred_at,
        remote_addr=entry.remote_addr,
        method=entry.method,
        request_path=entry.request_path,
        request_protocol=entry.request_protocol,
        status_code=entry.status_code,
        body_bytes_sent=entry.body_bytes_sent,
        referer=entry.referer,
        user_agent=entry.user_agent,
        raw_line=entry.raw_line,
    )


def entry_to_domain(model: LogEntryModel) -> LogEntry:
    from uuid import UUID

    return LogEntry(
        id=model.id,
        import_id=UUID(model.import_id),
        occurred_at=model.occurred_at,
        remote_addr=model.remote_addr,
        method=model.method,
        request_path=model.request_path,
        request_protocol=model.request_protocol,
        status_code=model.status_code,
        body_bytes_sent=model.body_bytes_sent,
        referer=model.referer,
        user_agent=model.user_agent,
        raw_line=model.raw_line,
    )
