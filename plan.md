# PLAN — Nginx Log Explorer

## Цель roadmap

Построить проверяемый MVP небольшими вертикально или инфраструктурно законченными задачами. Одновременно выполняется только одна TASK. Детальный файл очередной TASK создаёт архитектор после `PASS` и merge предыдущей.

## Цикл задачи

```text
актуальный master
      ↓
новая task/TASK-XXX-* ветка
      ↓
реализация одной TASK
      ↓
целевые тесты + отчёт + changed-files ZIP
      ↓
архитектурный/security review
      ├── FAIL → FIX-TASK → повторный review
      └── PASS → commit исполнителем
                         ↓
                    merge пользователем
```

## Definition of Ready

TASK готова к исполнению, когда в ней есть:

- один проверяемый результат;
- явные `Сделать` и `Не делать`;
- acceptance criteria;
- тестовый scope;
- список документов для чтения;
- известные security-ограничения.

## Definition of Done

- scope TASK выполнен без побочных функций;
- acceptance criteria подтверждены;
- целевые тесты пройдены;
- отчёт перечисляет реальные команды и риски;
- ZIP содержит только changed files;
- архитектор выдал `PASS`;
- после `PASS` создан один commit;
- пользователь самостоятельно выполнил merge.

## Roadmap

### TASK-001 — Repository foundation

**Цель:** создать запускаемый monorepo-каркас backend/frontend и единые команды разработки.

**Результат:** FastAPI health endpoint и минимальная React-страница запускаются; тестовые раннеры обоих приложений работают.

**Не входит:** БД, импорт файлов, Nginx parser, таблица логов.

**Проверки:** bootstrap/smoke, backend health test, frontend render test.

---

### TASK-002 — Persistence foundation

**Цель:** добавить SQLite, SQLAlchemy, Alembic и модели `LogImport`/`LogEntry` за repository boundary.

**Результат:** миграция поднимает чистую БД; repository contract создаёт, читает и удаляет scoped данные.

**Не входит:** HTTP upload и parser.

**Проверки:** migration upgrade на чистой БД, repository integration tests, cascade delete.

---

### TASK-003 — Nginx combined parser

**Цель:** реализовать чистый parser одной строки формата Nginx `combined`.

**Результат:** валидная строка преобразуется в domain value; невалидная возвращает типизированный reject без исключения наружу.

**Не входит:** FastAPI, filesystem/upload и persistence orchestration.

**Проверки:** unit matrix для escaping, timezone, методов, URL, пустых/длинных/повреждённых строк.

---

### TASK-004 — Import use case

**Цель:** потоково обработать файл через parser и сохранить согласованный результат.

**Результат:** корректные строки сохраняются, rejects считаются, фатальный сбой оставляет честный статус импорта.

**Не входит:** multipart endpoint и UI.

**Проверки:** application tests для mixed file, empty file, fatal persistence error и resource limits.

---

### TASK-005 — Upload API

**Цель:** открыть безопасный `POST /api/v1/imports` и read/delete endpoints импортов.

**Результат:** локальный клиент может загрузить допустимый файл, получить счётчики, список/детали и удалить импорт.

**Не входит:** entries query endpoint и frontend.

**Проверки:** API tests для happy path, size limit, malformed multipart, not found, deletion и sanitized errors.

---

### TASK-006 — Entries query API

**Цель:** реализовать постраничное чтение, поиск и структурные фильтры внутри одного `import_id`.

**Результат:** поддержаны согласованные фильтры, стабильная сортировка и ограниченная pagination.

**Не входит:** агрегаты, regex и произвольный SQL/search DSL.

**Проверки:** repository/API matrix, комбинации фильтров, границы limit, invalid sort/filter, изоляция между imports.

---

### TASK-007 — Frontend import flow

**Цель:** дать пользователю список импортов, загрузку, итоговые счётчики и удаление.

**Результат:** основной use case доступен из браузера с loading/empty/error states.

**Не входит:** таблица entries и filters.

**Проверки:** component/API adapter tests, upload error, delete confirmation.

---

### TASK-008 — Frontend log explorer

**Цель:** добавить таблицу записей, поиск, фильтры и pagination.

**Результат:** параметры синхронизированы с URL; данные безопасно выводятся как текст; ошибки API видимы.

**Не входит:** charts, dashboards и сохранённые запросы.

**Проверки:** filter serialization, pagination, empty/error states, XSS-shaped content rendering.

---

### TASK-009 — Deployment hardening

**Цель:** обеспечить воспроизводимый локальный запуск и безопасные значения конфигурации по умолчанию.

**Результат:** Docker Compose поднимает frontend/backend с persistent managed volume; CORS и limits конфигурируются; документация запуска проверена.

**Проверки:** compose config/build, startup smoke, fresh-volume migration, no-secrets check.

---

### TASK-010 — Release gate

**Цель:** провести полный функциональный, архитектурный и security review MVP.

**Проверки:** полный backend/frontend suite, production builds, migration from empty DB, end-to-end smoke, dependency audit, upload abuse cases, XSS/SQL/path traversal review.

**Acceptance:** нет blocker/high проблем; ограничения MVP и известные риски отражены в README/release report.

## Правило изменения roadmap

Roadmap фиксирует направление, но не является разрешением реализовывать задачи заранее. Новая возможность добавляется только отдельным решением архитектора и отдельной TASK. После каждого merge архитектор сверяет актуальный `master` и только затем выпускает следующий детальный TASK.
