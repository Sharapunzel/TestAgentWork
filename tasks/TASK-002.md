# TASK-002 — Persistence Foundation

## Статус

```text
READY FOR IMPLEMENTATION
```

## Цель

Добавить независимый от HTTP слой хранения для импортов и нормализованных записей Nginx: доменные типы, repository contract, SQLAlchemy 2 implementation, SQLite engine/session factory и первую Alembic migration. После задачи данные должны создаваться, читаться и удаляться через repository boundary в изолированной тестовой БД.

## Предусловия

- TASK-001 прошла архитектурный review и слита пользователем в `master`.
- Исполнитель находится на чистом актуальном `master`.
- В `master` присутствуют `architecture.md`, `AGENTS.md`, `plan.md` и рабочий каркас TASK-001.

Если working tree не чист, TASK-001 отсутствует или `master` не содержит её merge, остановиться со статусом `BLOCKED`. Не исправлять состояние Git автоматически и не переносить изменения из старой ветки.

## Git

1. Зафиксировать текущий SHA `master` как base commit.
2. Создать от него новую ветку:

```text
task/TASK-002-persistence
```

3. Не создавать commit до `PASS` архитектора.
4. Не выполнять merge/rebase в `master`, force-push и изменение истории.

## Обязательное чтение

```text
architecture.md
AGENTS.md
plan.md
tasks/TASK-002.md
backend/pyproject.toml
backend/app/main.py
backend/tests/
```

При конфликте требований остановиться и вернуть вопрос архитектору.

## Архитектурные решения этой TASK

```text
ORM: SQLAlchemy 2.x, typed declarative mapping
Migration tool: Alembic
MVP database: SQLite
Import identifier: UUID
Log entry identifier: SQLite-compatible auto-increment integer
Time storage: UTC; domain values remain timezone-aware
Transaction owner: future application service / caller, not repository methods
```

Новые версии зависимостей выбирать совместимыми с Python 3.12 и без известных security findings. Версии зафиксировать в `pyproject.toml` и `uv.lock`.

## Слои и зависимости

Соблюсти направление:

```text
domain entities/value types
          ↑
repository protocol / port
          ↑
SQLAlchemy repository + mappers + session factory
```

Требования:

- domain-код не импортирует FastAPI, SQLAlchemy или Alembic;
- SQLAlchemy models не передаются наружу как публичный repository contract;
- repository implementation не выполняет `commit()` самостоятельно;
- API routes и React не обращаются к persistence;
- `app.main` не запускает migration и не создаёт БД при импорте;
- модульный import не создаёт директории и файлы.

## Сделать

### 1. Domain types

Добавить чистые Python-типы для:

#### LogImport

```text
id: UUID
original_filename: str
status: processing | completed | failed
started_at: timezone-aware datetime
completed_at: timezone-aware datetime | None
total_lines: int
accepted_lines: int
rejected_lines: int
failure_code: str | None
```

#### LogEntry

```text
id: int | None before persistence
import_id: UUID
occurred_at: timezone-aware datetime
remote_addr: str
method: str
request_path: str
request_protocol: str
status_code: int
body_bytes_sent: int
referer: str | None
user_agent: str | None
raw_line: str
```

Domain types должны быть независимы от ORM. Минимальная валидация допустима, но не переносить сюда parser Nginx и не строить полноценную validation framework.

### 2. Database schema

Создать таблицы:

```text
log_imports
log_entries
```

Обязательные свойства:

- `log_entries.import_id` — non-null FK на `log_imports.id`;
- удаление `LogImport` физически удаляет его entries через database-level `ON DELETE CASCADE`;
- SQLite foreign keys включаются для каждого connection;
- status ограничен тремя разрешёнными значениями;
- счётчики и `body_bytes_sent` неотрицательны;
- `status_code` ограничен диапазоном `100..599`;
- nullable/non-nullable поля соответствуют domain-модели;
- timestamps сохраняют UTC-семантику, round-trip возвращает aware UTC datetime;
- таблицы имеют индексы:

```text
(import_id, occurred_at)
(import_id, status_code)
(import_id, method)
```

Не добавлять полнотекстовый индекс и индексы «на будущее».

### 3. Alembic

Добавить Alembic configuration и одну initial migration, которая:

- создаёт обе таблицы, constraints, FK и три индекса;
- успешно применяется к чистой SQLite database;
- поддерживает downgrade до пустой схемы;
- не содержит абсолютных локальных путей;
- не создаёт production/runtime DB во время tests;
- является явной проверенной migration, а не runtime `metadata.create_all()`.

`metadata.create_all()` разрешён только для узких unit/integration fixtures, если migration test отдельно доказывает реальную upgrade/downgrade цепочку. Предпочтительно использовать migration и в интеграционной fixture.

### 4. Session factory

Добавить infrastructure/persistence factory, которая:

- принимает database URL явно;
- создаёт SQLAlchemy engine без connection при import time;
- включает SQLite foreign keys на connection;
- предоставляет typed session factory;
- не хранит глобальный mutable `Session`;
- не делает auto-migrate;
- корректно работает с отдельным временным `.sqlite` файлом в tests.

Не добавлять сложный config framework только ради этой задачи.

### 5. Repository contract и implementation

Добавить один компактный repository port с операциями, достаточными для проверки foundation:

```text
add_import(log_import) -> None
get_import(import_id) -> LogImport | None
add_entries(entries) -> None
list_entries(import_id) -> sequence[LogEntry]
delete_import(import_id) -> bool
```

Правила:

- `list_entries` всегда scoped по `import_id` и имеет стабильный порядок, например `occurred_at`, затем `id`;
- `add_entries` не принимает entries другого import молча, если repository/use case уже scoped; выбрать простой однозначный контракт и покрыть его тестом;
- `delete_import` сообщает, найден ли объект;
- repository выполняет `flush()` только при необходимости получить DB-generated ID, но не `commit()`;
- rollback/commit остаются ответственностью caller transaction;
- ORM ↔ domain mapping централизован и покрыт round-trip тестом;
- ошибки БД не маскируются как «объект не найден».

Если названия методов немного отличаются, семантика и coverage должны полностью совпадать.

### 6. Tests

Добавить изолированные backend tests как минимум для:

1. Alembic upgrade на пустом временном SQLite-файле.
2. Alembic downgrade обратно до пустой user schema.
3. Создания и чтения `LogImport` через repository.
4. Round-trip всех значимых `LogEntry` полей, включая Unicode и nullable referer/user-agent.
5. Сохранения timezone-aware значения и возврата в UTC.
6. Изоляции `list_entries` между двумя `import_id`.
7. Стабильного порядка entries.
8. `ON DELETE CASCADE` на уровне БД/repository.
9. Rollback: незакоммиченные изменения не видны после rollback/новой session.
10. DB constraints: недопустимый status или отрицательный счётчик отклоняется.

Каждый test использует уникальную временную DB. Не писать тестовые DB в репозиторий, `backend/`, `runtime/` или ZIP.

### 7. Developer commands and documentation

- Обновить root `Makefile`, только если нужна отдельная migration-check команда.
- Коротко дополнить `README.md` командами migration upgrade/downgrade и способом задать локальный database URL, если это действительно реализовано.
- Документация не должна утверждать, что upload/import UI уже работает.
- Все приведённые команды должны соответствовать фактической конфигурации.

## Не делать

- не реализовывать Nginx parser;
- не реализовывать file upload, import use case и API endpoints данных;
- не подключать БД к health endpoint;
- не запускать migration автоматически при FastAPI startup/import;
- не добавлять PostgreSQL, Redis, async SQLAlchemy или connection pooling abstractions;
- не добавлять authentication/users/ownership;
- не реализовывать search, filters, pagination, aggregates и FTS;
- не добавлять Docker/Compose;
- не менять frontend, кроме отсутствия необходимости вообще;
- не менять `architecture.md`, `AGENTS.md` и `plan.md`;
- не подавлять deprecation/security warnings без объяснения;
- не добавлять unrelated refactor;
- не создавать commit до `PASS`.

## Acceptance criteria

1. Ветка `task/TASK-002-persistence` создана от актуального чистого `master`.
2. Domain-типы не зависят от SQLAlchemy/FastAPI.
3. Одна Alembic migration поднимает чистую SQLite schema и корректно откатывается.
4. Schema содержит заданные constraints, FK с `ON DELETE CASCADE` и только требуемые индексы.
5. Repository сохраняет и возвращает domain objects, не раскрывая ORM models.
6. Repository не вызывает `commit()`.
7. Entries двух imports не смешиваются.
8. Cascade delete подтверждён тестом.
9. UTC-aware timestamps переживают persistence round-trip.
10. Тесты изолированы и не оставляют DB/runtime-файлы.
11. Backend и полный существующий project suite проходят.
12. Dependency audit не содержит известных backend vulnerabilities.
13. В ZIP нет `.db`, `.sqlite*`, caches, environments, dependencies и секретов.

## Обязательные проверки

Команды адаптировать к фактической конфигурации, но реально выполнить эквивалент:

```text
cd backend
uv sync --frozen
uv run alembic upgrade head      # против новой временной DB
uv run alembic downgrade base    # против той же временной DB
uv run pytest -q
uv run ruff check app tests migrations
uv run --with pip-audit pip-audit

cd frontend
npm ci
npm test -- --run
npm run lint
npm run build
```

Если migration command требует переменную/option с URL, использовать только временный путь и привести точную безопасную команду в отчёте. Не создавать DB внутри review ZIP.

Полный suite обязателен, потому что TASK меняет schema/migrations и backend foundation.

## Review artifact

Создать:

```text
TASK-002_CHANGED.zip
```

ZIP содержит только новые и изменённые файлы относительно base commit ветки с сохранением путей. Проверить список содержимого и отсутствие:

```text
.git
.env*
.venv
node_modules
__pycache__
test/runtime DB files
dist/build/coverage
credentials
previous ZIPs
```

## Что вернуть архитектору

```text
TASK: TASK-002
STATUS: DONE / BLOCKED
BRANCH: task/TASK-002-persistence
BASE COMMIT: <sha>

Что сделано:
- ...

Изменённые файлы:
- ...

Схема и repository contract:
- ...

Решения и новые зависимости:
- ...

Проверки (только реально запущенные):
- <команда> → <результат>

Не сделано / риски / найденные соседние проблемы:
- ...

COMMIT: not created — awaiting architect PASS
ZIP: TASK-002_CHANGED.zip
```

Вернуть отчёт и ZIP, затем прекратить работу до review.
