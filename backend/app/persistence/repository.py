from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import LogEntry, LogImport
from app.persistence.mappers import (
    entry_to_domain,
    entry_to_model,
    import_to_domain,
    import_to_model,
)
from app.persistence.models import LogEntryModel, LogImportModel


class SqlAlchemyLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_import(self, log_import: LogImport) -> None:
        self._session.add(import_to_model(log_import))

    def get_import(self, import_id: UUID) -> LogImport | None:
        model = self._session.get(LogImportModel, str(import_id))
        return None if model is None else import_to_domain(model)

    def add_entries(self, entries: Sequence[LogEntry]) -> None:
        if not entries:
            return
        import_ids = {entry.import_id for entry in entries}
        if len(import_ids) != 1:
            raise ValueError("all entries in a batch must have the same import_id")

        pending_imports = {
            model.id: model
            for model in self._session.new
            if isinstance(model, LogImportModel)
        }
        pairs = [(entry, entry_to_model(entry)) for entry in entries]
        for _, model in pairs:
            pending_import = pending_imports.get(model.import_id)
            if pending_import is not None:
                model.log_import = pending_import
        self._session.add_all(model for _, model in pairs)
        self._session.flush()
        for entry, model in pairs:
            entry.id = model.id

    def list_entries(self, import_id: UUID) -> Sequence[LogEntry]:
        statement = (
            select(LogEntryModel)
            .where(LogEntryModel.import_id == str(import_id))
            .order_by(LogEntryModel.occurred_at, LogEntryModel.id)
        )
        return [entry_to_domain(model) for model in self._session.scalars(statement)]

    def delete_import(self, import_id: UUID) -> bool:
        model = self._session.get(LogImportModel, str(import_id))
        if model is None:
            return False
        self._session.delete(model)
        return True
