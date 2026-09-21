# FIX-TASK-001-1 — Remove Known Dependency Vulnerabilities

## Основание

Архитектурный review TASK-001: `FAIL`.

Функциональная реализация и исходные тесты проходят, но dependency audits обнаружили известные уязвимости:

```text
frontend: 1 critical, 1 high, 3 moderate, 2 low
backend: known vulnerabilities in pytest 8.3.4 and Starlette 0.41.3
```

Среди frontend findings присутствуют уязвимости локальных dev-серверов с риском чтения файлов и выполнения кода. Их нельзя принять только на основании отсутствия production dependencies.

## Git

- Продолжить работу в существующей ветке `task/TASK-001-foundation`.
- Не создавать новую feature branch.
- Не создавать commit до повторного `PASS` архитектора.
- Base commit для changed-files ZIP остаётся `b38e528a8ddadec045dd4224a396643a4971042d`.

## Сделать

1. Обновить backend dependency constraints до совместимого набора, в котором:
   - FastAPI использует исправленную версию Starlette;
   - pytest не содержит найденную уязвимость;
   - сохраняется Python 3.12;
   - health API contract не меняется.
2. Перегенерировать `backend/uv.lock` через `uv`, не редактировать lock-файл вручную.
3. Обновить frontend dev dependencies до совместимых исправленных версий, включая как минимум Vite, Vitest и ESLint dependency chain.
4. Перегенерировать `frontend/package-lock.json` через npm, не редактировать lock-файл вручную.
5. При несовместимости обновлённых инструментов внести только минимальные изменения в их конфигурацию.
6. Повторно создать `TASK-001_CHANGED.zip` со всеми изменениями TASK-001 относительно исходного base commit.

## Не делать

- не использовать `overrides` для принудительной подмены несовместимой транзитивной зависимости без доказанной совместимости;
- не подавлять audit findings через ignore/allowlist;
- не использовать `npm audit fix --force` без разбора итогового dependency tree;
- не менять React application, health endpoint и тестовые ожидания без необходимости совместимости;
- не добавлять БД, импорт, CORS, API client или функции следующих TASK;
- не менять `architecture.md`, `AGENTS.md` и `plan.md`;
- не создавать commit.

## Acceptance

1. Все acceptance criteria TASK-001 остаются выполнены.
2. `uv sync --frozen`, backend test и Ruff проходят.
3. `npm ci`, frontend test, lint и build проходят.
4. `npm audit --audit-level=high` завершается успешно: `0 critical`, `0 high`.
5. `npm audit --omit=dev` завершается успешно.
6. `pip-audit` не находит известных уязвимостей в установленном backend environment.
7. Обновление не включает unrelated refactor.
8. Новый ZIP безопасен и содержит полный changed-files набор TASK-001 относительно исходного base commit.

Low/moderate frontend findings допустимы только если для них объективно отсутствует совместимая исправленная версия; каждое такое исключение должно быть перечислено с advisory ID, affected package, причиной и компенсирующей мерой. Critical/high исключения не допускаются.

## Проверки

```text
cd backend
uv sync --frozen
uv run pytest tests/test_health.py -q
uv run ruff check app tests
uv run --with pip-audit pip-audit

cd frontend
npm ci
npm test -- --run
npm run lint
npm run build
npm audit --audit-level=high
npm audit --omit=dev
```

Также повторить HTTP smoke-check точного контракта:

```text
200 {"status":"ok"}
```

## Что вернуть

- короткий отчёт по формату `AGENTS.md`;
- старые и новые версии прямых зависимостей;
- результаты всех команд выше;
- список оставшихся audit findings, если есть;
- обновлённый `TASK-001_CHANGED.zip`;
- `COMMIT: not created — awaiting architect PASS`.
