# FIX-TASK-002-1 — Isolate Migration Tests From Environment Database

## Основание

Архитектурный review TASK-002: `FAIL`.

`backend/migrations/env.py:get_database_url()` отдаёт приоритет переменной `NLE_DATABASE_URL` перед URL, явно переданным через Alembic `Config.set_main_option()`.

Из-за этого migration tests, которые создают временную БД через programmatic Alembic config, при наличии `NLE_DATABASE_URL` в shell применяют `upgrade`/`downgrade` к базе из окружения. Воспроизведено командой с безопасной тестовой переменной: test мигрировал файл из environment и не создал ожидаемую временную schema.

Это риск непреднамеренного изменения или очистки пользовательской БД во время тестов.

## Git

- Продолжить работу в существующей ветке `task/TASK-002-persistence`.
- Не создавать новую feature branch.
- Не создавать commit до повторного `PASS` архитектора.
- Base commit для ZIP остаётся `71c018123a2684838b2e21c124b91ce6ccfc27ac`.

## Сделать

1. Исправить разрешение database URL:
   - URL, явно переданный через Alembic config для конкретного вызова, должен иметь приоритет;
   - `NLE_DATABASE_URL` используется CLI-вызовом только если explicit config URL отсутствует;
   - если отсутствуют оба источника, migration завершается понятной ошибкой.
2. Не добавлять реальный/default filesystem path в `alembic.ini`.
3. Добавить regression test:
   - установить `NLE_DATABASE_URL` на отдельную sentinel SQLite database;
   - создать в sentinel DB таблицу/маркер, позволяющий доказать неизменность;
   - программно передать другой временный URL через Alembic Config;
   - выполнить upgrade и downgrade только временной DB;
   - подтвердить, что sentinel DB не получила Alembic/schema changes и её маркер сохранился.
4. Сохранить отдельную проверку, что CLI/environment fallback действительно работает, когда explicit URL отсутствует.
5. Пересоздать `TASK-002_CHANGED.zip` относительно исходного base commit.

## Не делать

- не очищать `NLE_DATABASE_URL` в общей fixture и не маскировать проблему только через `monkeypatch.delenv`;
- не использовать production/runtime database в tests;
- не добавлять default DB URL;
- не менять schema, repository contract или domain models;
- не добавлять parser/upload/API;
- не создавать commit.

## Acceptance

1. Programmatic Alembic URL всегда изолирован от случайной environment variable.
2. Sentinel regression test доказывает, что посторонняя DB не изменяется.
3. `NLE_DATABASE_URL` продолжает работать для документированного CLI workflow.
4. Migration upgrade/downgrade и полный backend suite проходят.
5. Frontend regression suite остаётся зелёным.
6. `pip-audit` не находит известных уязвимостей.
7. ZIP содержит полный diff TASK-002 и FIX относительно исходного base commit, без DB/runtime/caches.

## Проверки

```text
cd backend
uv sync --frozen
uv run pytest -q
uv run ruff check app tests migrations
uv run --with pip-audit pip-audit

# Отдельно повторить regression test при заранее заданной NLE_DATABASE_URL.
# Он должен пройти и доказать неизменность sentinel DB.

cd frontend
npm ci
npm test -- --run
npm run lint
npm run build
```

## Что вернуть

- отчёт по формату `AGENTS.md`;
- краткое описание нового порядка разрешения URL;
- результат sentinel regression test;
- результаты всех проверок;
- обновлённый `TASK-002_CHANGED.zip`;
- `COMMIT: not created — awaiting architect PASS`.
