# TASK-001 — Repository Foundation

## Статус

```text
READY FOR IMPLEMENTATION
```

## Цель

Создать минимальный воспроизводимый monorepo-каркас Nginx Log Explorer: FastAPI backend с health endpoint и React/TypeScript frontend с одной стартовой страницей. После задачи оба приложения и их целевые тесты должны запускаться локально, но бизнес-функции анализа логов ещё не реализуются.

## Предусловие

Пользователь заранее разместил в корне репозитория и зафиксировал в `master`:

```text
architecture.md
AGENTS.md
plan.md
tasks/TASK-001.md
```

Working tree актуального `master` должен быть чистым. Если Git-репозиторий, baseline commit или обязательные документы отсутствуют, не создавать их молча и не продолжать реализацию: вернуть `BLOCKED` с точной причиной.

## Git

Перед изменениями:

1. Прочитать правила из `AGENTS.md`.
2. Зафиксировать SHA актуального `master` как base commit.
3. Создать от него ветку:

```text
task/TASK-001-foundation
```

4. Не создавать commit до `PASS` архитектора.
5. Не выполнять merge/rebase в `master` и не изменять историю.

## Обязательное чтение

```text
architecture.md
AGENTS.md
plan.md
tasks/TASK-001.md
```

Если TASK конфликтует с этими документами, остановиться и задать вопрос.

## Технологические решения этой TASK

```text
Backend runtime: Python 3.12
Backend framework: FastAPI
Python project/dependency manager: uv
Backend tests: pytest + FastAPI TestClient
Backend lint/format check: Ruff

Frontend runtime: Node.js 22+
Frontend framework: React + TypeScript + Vite
Frontend package manager: npm with package-lock.json
Frontend tests: Vitest + React Testing Library + jsdom
Frontend lint: ESLint

Root command entrypoint: Makefile
```

Lock-файлы обязательны. Не заменять выбранные инструменты аналогами без согласования.

## Сделать

### 1. Backend foundation

Создать backend-проект со структурой не менее:

```text
backend/
  app/
    __init__.py
    api/
      __init__.py
      health.py
    main.py
  tests/
    test_health.py
  pyproject.toml
  uv.lock
```

Требования:

- экспортировать FastAPI application из `backend/app/main.py` как `app`;
- подключить health router через `/api/v1`;
- реализовать `GET /api/v1/health`;
- успешный ответ: HTTP `200` и точное тело `{"status":"ok"}`;
- endpoint не обращается к БД, filesystem, сети и environment secrets;
- endpoint не возвращает версии, пути, hostname или конфигурацию;
- приложение импортируется без побочных IO-операций;
- добавить тест точного status code и JSON-контракта;
- настроить Ruff без массового набора нестандартных правил.

### 2. Frontend foundation

Создать frontend-проект со структурой Vite React + TypeScript. Минимально требуются:

```text
frontend/
  src/
    App.tsx
    main.tsx
    ...
  tests/ или src/*.test.tsx
  package.json
  package-lock.json
  tsconfig*.json
  vite.config.*
```

Требования:

- стартовая страница содержит видимый заголовок `Nginx Log Explorer`;
- страница может содержать короткую подпись о будущем импорте логов;
- не выполнять запрос к backend в этой TASK;
- не добавлять routing, state-management library, component framework или CSS framework;
- использовать обычный React rendering, без `dangerouslySetInnerHTML`;
- добавить component test, проверяющий отображение заголовка;
- настроить `test`, `lint` и `build` scripts;
- Vite dev server должен слушать только локальный интерфейс по умолчанию, без `--host 0.0.0.0`.

### 3. Root developer commands

Добавить корневой `Makefile` с понятными командами:

```text
make test-backend
make test-frontend
make test
make lint
```

Допустимы дополнительные локальные команды `dev-backend` и `dev-frontend`, если они просты и документированы. Команды не должны автоматически изменять файлы, устанавливать глобальные пакеты или запускать production-like services.

### 4. Repository hygiene

Добавить или дополнить корневой `.gitignore` для исключения как минимум:

```text
.env*
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
node_modules/
coverage/
dist/
build/
runtime/
uploads/
*.db
*.sqlite*
TASK-*_CHANGED.zip
```

Разрешить коммит безопасного файла `.env.example`, но не создавать его без реальной необходимости в этой TASK.

Добавить короткий корневой `README.md` только с:

- назначением проекта;
- prerequisites;
- командами установки зависимостей;
- запуском backend/frontend в development;
- целевыми test/lint командами;
- явным указанием, что анализ логов ещё не реализован.

Команды README должны быть реально проверены в доступной среде либо отмечены в отчёте как непроверенные с причиной.

## Не делать

- не добавлять SQLAlchemy, Alembic, SQLite schema или repositories;
- не реализовывать upload, Nginx parser, импорт или поиск;
- не добавлять Dockerfile и Docker Compose — это отдельная последующая задача;
- не добавлять CORS, authentication, authorization и user model;
- не создавать API client во frontend;
- не добавлять reverse proxy;
- не добавлять CI/CD;
- не добавлять telemetry, analytics, error tracking или внешние сервисы;
- не добавлять UI kit, router, state manager и CSS framework;
- не менять `architecture.md`, `AGENTS.md` и `plan.md`;
- не выполнять unrelated refactor;
- не создавать финальный commit до `PASS`.

## Acceptance criteria

1. Ветка называется `task/TASK-001-foundation` и основана на зафиксированном SHA актуального `master`.
2. FastAPI application импортируется и запускается локально.
3. `GET /api/v1/health` возвращает только HTTP `200` и `{"status":"ok"}`.
4. Backend health test проходит.
5. React/TypeScript application запускается и отображает `Nginx Log Explorer`.
6. Frontend component test проходит.
7. Frontend production build проходит.
8. Backend и frontend lint проходят.
9. Lock-файлы `uv.lock` и `package-lock.json` присутствуют.
10. В репозитории нет секретов, `.env`, runtime-файлов, database-файлов и dependency directories.
11. БД, импорт и анализ логов отсутствуют.
12. README содержит только проверяемые команды актуального каркаса.

## Обязательные проверки

Исполнитель должен адаптировать рабочие директории к структуре проекта, но фактически запустить эквивалент следующих проверок:

```text
cd backend && uv sync --frozen
cd backend && uv run pytest tests/test_health.py -q
cd backend && uv run ruff check app tests

cd frontend && npm ci
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run build
```

Дополнительно выполнить короткий smoke check HTTP endpoint на локально запущенном приложении либо явно объяснить, почему TestClient-проверки достаточно в доступной среде.

Полный test suite не требуется: TASK создаёт только foundation, а перечисленные проверки покрывают весь созданный executable scope.

## Review artifact

Создать в корне:

```text
TASK-001_CHANGED.zip
```

ZIP должен содержать только файлы, новые или изменённые относительно base commit этой ветки, с сохранением относительных путей. Сам ZIP не включать внутрь ZIP.

Перед возвратом:

1. вывести список файлов внутри архива;
2. сравнить его со списком changed files относительно base commit;
3. убедиться, что исключены зависимости, caches, `.env`, credentials, runtime и database-файлы;
4. не добавлять ZIP и изменения задачи в commit до `PASS`.

## Что вернуть архитектору

```text
TASK: TASK-001
STATUS: DONE / BLOCKED
BRANCH: task/TASK-001-foundation
BASE COMMIT: <sha>

Что сделано:
- ...

Изменённые файлы:
- ...

Решения и новые зависимости:
- ...

Проверки (только реально запущенные):
- <команда> → <результат>

Не сделано / риски / найденные соседние проблемы:
- ...

COMMIT: not created — awaiting architect PASS
ZIP: TASK-001_CHANGED.zip
```

Вернуть отчёт и `TASK-001_CHANGED.zip`. После этого прекратить работу и ждать review.
