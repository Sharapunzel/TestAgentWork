# TASK-003 — Nginx Combined Log Parser

## Статус

```text
READY FOR IMPLEMENTATION
```

## Цель

Реализовать чистый, детерминированный и ограниченный по ресурсам parser одной строки стандартного Nginx `combined` access log. Валидная строка должна преобразовываться в domain value, готовый для будущего import use case; невалидная строка должна возвращать типизированный reject без исключения наружу.

## Предусловия

- TASK-002 прошла review и слита пользователем в `master`.
- Исполнитель находится на чистом актуальном `master`.
- В `master` присутствуют persistence foundation и `tasks/TASK-003.md`.

Если merge отсутствует или working tree не чист, остановиться со статусом `BLOCKED`. Не переносить изменения из старой ветки автоматически.

## Git

1. Зафиксировать SHA актуального `master` как base commit.
2. Создать ветку:

```text
task/TASK-003-nginx-parser
```

3. Не создавать commit до `PASS` архитектора.
4. Не выполнять merge/rebase в `master`, force-push и изменение истории.

## Обязательное чтение

```text
architecture.md
AGENTS.md
plan.md
tasks/TASK-003.md
backend/app/domain/models.py
backend/app/domain/repositories.py
backend/tests/
```

## Поддерживаемый формат

Только стандартный Nginx `combined`:

```text
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
```

Пример:

```text
192.0.2.10 - - [21/Sep/2026:10:31:45 +0300] "GET /products?page=2 HTTP/1.1" 200 512 "https://example.test/" "Mozilla/5.0"
```

Произвольный `log_format`, JSON, syslog, upstream timing fields и несколько форматов в одном parser не поддерживаются.

## Архитектурные решения

- Parser находится в domain и не импортирует FastAPI, SQLAlchemy, Alembic или filesystem modules.
- Parser принимает одну Python-строку и не читает файл.
- Parser не знает `import_id`, repository и транзакции.
- Успешный результат — отдельный immutable domain value `ParsedLogEntry`, а не persistence `LogEntry` с искусственным ID.
- Ошибка входных данных — значение `ParseReject`, а не exception.
- Reject содержит только безопасный код и при необходимости позицию/краткую техническую деталь; он не дублирует полную исходную строку.
- Время нормализуется в timezone-aware UTC.

## Сделать

### 1. Domain result types

Добавить тип успешного результата со следующими полями:

```text
occurred_at: timezone-aware UTC datetime
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

Добавить типизированный reject и enum кодов как минимум для различения:

```text
empty_line
line_too_long
format_mismatch
invalid_timestamp
invalid_request
invalid_status
invalid_body_bytes
field_too_long
invalid_escape
```

Допустимо объединить коды только при убедительном упрощении, но нельзя свести все ошибки к одному `invalid`.

Публичный контракт parser должен позволять вызывающему коду безопасно различить success/reject через типы, `isinstance`, tagged union или эквивалент — без анализа текста сообщения.

### 2. Parser API

Реализовать одну основную функцию, например:

```python
parse_combined_line(line: str) -> ParsedLogEntry | ParseReject
```

Она должна:

- удалить только один завершающий `\n` и предшествующий ему `\r`, если они есть;
- не применять общий `strip()`, меняющий содержимое полей;
- отклонять пустую строку;
- до сложного разбора отклонять строку длиннее `65_536` символов;
- разобрать ровно combined format без принятия произвольного хвоста;
- не выбрасывать наружу `ValueError`, `IndexError`, regex errors и подобные исключения для любого строкового input;
- не выполнять IO, logging, network calls или database calls;
- работать за линейное время от длины строки; избегать regex с catastrophic backtracking.

### 3. Поля и семантика

#### Timestamp

- Принимать форму Nginx `$time_local`: `21/Sep/2026:10:31:45 +0300`.
- Английские сокращения месяцев разбирать независимо от системной locale.
- Учитывать указанный UTC offset и возвращать UTC-aware datetime.
- Отклонять невозможные даты и некорректные offsets.

#### Request

- Разделить quoted `$request` ровно на method, request target и protocol.
- Request `"-"`, отсутствие одного из трёх компонентов и лишние raw spaces считать `invalid_request`.
- Method не должен содержать whitespace/control characters и ограничен 32 символами.
- Request target сохраняется в `request_path` без URL-decoding и нормализации; query string не удаляется.
- `request_path` ограничен 8192 символами.
- Protocol ограничен 16 символами и должен соответствовать форме `HTTP/<major>.<minor>`.
- Не вводить allowlist HTTP methods: нестандартный, но синтаксически корректный method допустим.

#### Status и bytes

- `status_code` — decimal integer `100..599`.
- `body_bytes_sent` — decimal integer `>= 0`.
- `-` для этих числовых полей отклоняется.

#### Address and quoted fields

- `remote_addr` не валидировать через IP library: сохранить token как строку, ограниченную 64 символами.
- `$remote_user` разобрать для структуры combined format, но не сохранять в MVP domain value.
- Quoted `"-"` для referer/user-agent преобразовать в `None`.
- Пустая quoted строка остаётся пустой строкой, не `None`.
- Referer ограничен 8192 символами, user-agent — 4096.
- Поддержать стандартное Nginx escaping как минимум для `\\"`, `\\\\` и валидного `\\xNN`.
- Некорректный/incomplete escape возвращает `invalid_escape`.
- Нельзя интерпретировать escape sequences как Python/JSON syntax шире Nginx semantics.

#### Raw line

- Сохранить исходную строку без завершающего CR/LF.
- Не логировать и не включать raw line в reject message.

### 4. Security/resource limits

Лимиты должны быть именованными constants рядом с parser и тестироваться на границах:

```text
line: 65_536
remote_addr: 64
method: 32
request_path: 8_192
request_protocol: 16
referer: 8_192
user_agent: 4_096
```

Ограничение применяется к декодированному значению поля; parser также защищён общим line limit. Не добавлять конфиг framework для этих constants в данной TASK.

### 5. Tests

Добавить parameterized unit tests как минимум для:

1. валидной стандартной строки;
2. CRLF и LF без попадания newline в `raw_line`;
3. timezone offset с нормализацией в UTC;
4. locale-independent English month;
5. Unicode в допустимых quoted полях;
6. escaped quote и backslash;
7. валидного `\xNN` escape;
8. `"-"` referer/user-agent → `None`;
9. пустой quoted строки → `""`;
10. нестандартного корректного method;
11. пустой строки;
12. слишком длинной строки;
13. неверной/невозможной даты;
14. request `"-"` и неверного числа request components;
15. status вне диапазона и нечислового status;
16. отрицательных/нечисловых bytes;
17. неверного/incomplete escape;
18. каждого field length boundary: ровно limit принимается, limit+1 отклоняется;
19. лишнего хвоста после combined record;
20. доказательства, что reject не содержит исходную чувствительную строку.

Добавить небольшой adversarial test на длинную строку с большим количеством кавычек/backslashes. Не использовать хрупкий wall-clock threshold; задача теста — завершиться и вернуть reject без recursion/error/hang.

## Не делать

- не читать файл и не определять его encoding;
- не создавать `LogImport`/`LogEntry` в repository;
- не изменять DB schema и migrations;
- не реализовывать upload/API/UI;
- не добавлять auto-detection формата;
- не поддерживать custom Nginx log formats;
- не выполнять URL-decoding, IP geolocation, user-agent parsing или bot detection;
- не логировать исходные строки;
- не добавлять внешнюю parsing dependency без отдельного согласования;
- не менять frontend;
- не менять `architecture.md`, `AGENTS.md` и `plan.md`;
- не создавать commit до `PASS`.

## Acceptance criteria

1. Ветка `task/TASK-003-nginx-parser` создана от актуального чистого `master`.
2. Parser — чистый domain code без FastAPI/SQLAlchemy/IO dependencies.
3. Валидный combined record преобразуется в полный `ParsedLogEntry`.
4. Timestamp детерминированно преобразуется в UTC независимо от locale.
5. Невалидный input возвращает типизированный reject и не выбрасывает exception.
6. Все числовые, структурные и length ограничения соблюдаются.
7. Nginx quoted escapes обрабатываются безопасно и однозначно.
8. Reject не содержит raw line или чувствительные поля.
9. Parser не меняет persistence schema/contracts.
10. Целевые parser tests и regression tests существующего backend проходят.
11. Dependency manifests не меняются без необходимости; новые dependency не ожидаются.
12. ZIP не содержит logs, fixtures с реальными данными, DB, caches или secrets.

## Обязательные проверки

```text
cd backend
uv sync --frozen
uv run pytest tests/test_parser.py -q
uv run pytest tests/test_repository.py tests/test_migrations.py tests/test_health.py -q
uv run ruff check app tests
```

Если имя test-файла отличается, указать фактическую команду. Полный frontend suite не требуется: frontend и общие контракты не затрагиваются.

Если dependency manifests всё же изменены, дополнительно выполнить:

```text
uv run --with pip-audit pip-audit
```

## Review artifact

Создать:

```text
TASK-003_CHANGED.zip
```

ZIP содержит только новые и изменённые файлы относительно base commit ветки. Не включать:

```text
.git
.env*
.venv
__pycache__
.pytest_cache
logs
runtime
uploads
*.db
*.sqlite*
node_modules
dist/build/coverage
credentials
previous ZIPs
```

Проверить список ZIP и отсутствие чувствительных реальных log samples.

## Что вернуть архитектору

```text
TASK: TASK-003
STATUS: DONE / BLOCKED
BRANCH: task/TASK-003-nginx-parser
BASE COMMIT: <sha>

Что сделано:
- ...

Публичный parser contract:
- ...

Reject codes и limits:
- ...

Изменённые файлы:
- ...

Проверки (только реально запущенные):
- <команда> → <результат>

Не сделано / риски:
- ...

COMMIT: not created — awaiting architect PASS
ZIP: TASK-003_CHANGED.zip
```

Вернуть отчёт и ZIP, затем прекратить работу до review.
