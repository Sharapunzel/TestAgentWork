# ARCHITECTURE — Nginx Log Explorer

## 1. Цель

Локальное однопользовательское веб-приложение для загрузки и анализа Nginx access logs.

Пользователь должен иметь возможность:

- загрузить файл access log;
- увидеть результат импорта и отклонённые строки;
- просматривать записи постранично;
- искать по тексту запроса и фильтровать по структурным полям;
- удалить импортированный набор вместе с его записями.

MVP — учебный проект агентской разработки. Его цель — законченный вертикальный срез с явными границами, тестами и review, а не замена промышленной observability-платформы.

## 2. Scope MVP

### Входит

- Nginx access logs в формате `combined`;
- загрузка одного файла через браузер;
- строгий лимит размера файла из конфигурации;
- построчный импорт без загрузки всего файла в память;
- хранение метаданных импорта и нормализованных записей;
- поиск по `request_path`, `user_agent` и исходной строке;
- фильтры: временной диапазон, HTTP method, status, IP, path;
- сортировка только по allowlist полей;
- пагинация на стороне API;
- локальный запуск через Docker Compose.

### Не входит

- realtime tailing и чтение файлов хоста;
- syslog, JSON Lines и произвольные форматы;
- аккаунты, роли и многопользовательская изоляция;
- алерты, dashboards, LLM-анализ и группировка ошибок;
- изменение конфигурации Nginx;
- архивы и несколько файлов в одном запросе;
- распределённое хранение и production deployment.

## 3. Ограничения и стек

```text
Frontend: React + TypeScript + Vite
Backend: Python 3.12 + FastAPI
Validation: Pydantic v2
Persistence: SQLite + SQLAlchemy 2 + Alembic
Testing: pytest + FastAPI TestClient/httpx; Vitest + React Testing Library
Packaging/runtime: Docker Compose
API prefix: /api/v1
```

Версии зависимостей фиксируются lock-файлами. Замена выбранного стека требует отдельного архитектурного решения.

## 4. Контейнеры и границы

```text
Browser / React
       |
       | HTTP / JSON, multipart upload
       v
FastAPI routes
       v
Application services
       v
Domain parser + query model
       v
Repository interfaces
       v
SQLite / local managed storage
```

Правила зависимостей:

1. React не знает устройство SQLite и не содержит серверную бизнес-логику.
2. API routes выполняют transport validation и вызывают application services.
3. Application services управляют use cases и транзакциями.
4. Парсер Nginx — чистая доменная функция без HTTP и БД.
5. SQLAlchemy-реализации находятся за repository boundary.

## 5. Предлагаемая структура репозитория

```text
backend/
  app/
    api/
    application/
    domain/
    infrastructure/
    persistence/
    main.py
  migrations/
  tests/
frontend/
  src/
    api/
    components/
    features/
    pages/
  tests/
docs/
tasks/
docker-compose.yml
architecture.md
AGENTS.md
plan.md
```

## 6. Модель данных

### LogImport

- `id`: UUID;
- `original_filename`: очищенное отображаемое имя, не путь;
- `status`: `processing | completed | failed`;
- `started_at`, `completed_at`;
- `total_lines`, `accepted_lines`, `rejected_lines`;
- `failure_code`: безопасный код ошибки или `null`.

### LogEntry

- `id`: integer/UUID;
- `import_id`: FK → LogImport с cascade delete;
- `occurred_at`: timezone-aware UTC;
- `remote_addr`;
- `method`;
- `request_path`;
- `request_protocol`;
- `status_code`;
- `body_bytes_sent`;
- `referer`;
- `user_agent`;
- `raw_line`: ограниченная по длине исходная строка для диагностики.

Индексы MVP: `(import_id, occurred_at)`, `(import_id, status_code)`, `(import_id, method)`. Любой дополнительный индекс добавляется по измеренной необходимости.

## 7. Формат и семантика импорта

- Поддерживается документированный Nginx `combined` format.
- Файл обрабатывается потоково, строка за строкой.
- Пустая или неразбираемая строка считается rejected и не создаёт `LogEntry`.
- Импорт не падает из-за единичной неверной строки.
- Фатальная ошибка БД/IO переводит импорт в `failed`; частичные записи не должны выглядеть как успешно завершённый импорт.
- API возвращает счётчики accepted/rejected, но не эхо полного содержимого ошибочных строк.
- Временная зона из строки учитывается и нормализуется в UTC.
- Повторная загрузка того же файла в MVP создаёт новый независимый `LogImport`.

## 8. API-контракты MVP

```text
POST   /api/v1/imports
GET    /api/v1/imports
GET    /api/v1/imports/{import_id}
DELETE /api/v1/imports/{import_id}
GET    /api/v1/imports/{import_id}/entries
GET    /api/v1/health
```

`GET .../entries` принимает только описанные параметры фильтрации, `limit` с верхней границей и непрозрачный cursor либо согласованную page-пагинацию. Клиент не передаёт SQL, regex или имя произвольного поля сортировки.

Ошибки имеют стабильную форму:

```json
{
  "error": {
    "code": "IMPORT_NOT_FOUND",
    "message": "Import was not found",
    "request_id": "..."
  }
}
```

## 9. Frontend MVP

Один рабочий поток:

1. список импортов;
2. загрузка файла и прогресс состояния запроса;
3. экран импорта со счётчиками;
4. таблица записей;
5. панель поиска и фильтров;
6. состояния loading, empty и error;
7. подтверждение удаления.

Фильтры сериализуются в URL query parameters, чтобы состояние страницы можно было воспроизвести после обновления.

## 10. Безопасность

Хотя MVP однопользовательский, входные лог-файлы считаются недоверенными.

- Upload имеет конфигурируемый лимит байтов и отклоняется до неограниченного накопления данных.
- Не доверять filename и MIME type; не использовать filename как путь.
- Загруженный файл не исполняется и не публикуется как статический ресурс.
- Строки лога отображаются как текст; запрещён небезопасный HTML rendering.
- Все SQL-запросы параметризованы; сортировка и фильтры используют allowlist.
- Ограничены длина строки, длины строковых полей, `limit` и диапазон параметров.
- Backend не принимает произвольный filesystem path от клиента.
- CORS ограничен адресом локального frontend из конфигурации.
- В ошибках и логах нет полного содержимого upload, cookies, Authorization headers и stack trace.
- Логи могут содержать персональные данные (IP, URL, user-agent); наружу приложение их не отправляет.
- Для локального deployment не заявляется защита от других пользователей/процессов той же машины.

## 11. Наблюдаемость приложения

Backend пишет структурированные события:

- request ID, method, route template, status, duration;
- import ID, длительность и итоговые счётчики;
- безопасный error code.

Не логируются query string исходного запроса Nginx, raw line, IP и user-agent. Health endpoint не раскрывает конфигурацию и пути файловой системы.

## 12. Тестовая стратегия

- parser unit tests: валидные и повреждённые строки, timezone, escaping, границы;
- application tests: частично неверный файл, фатальный rollback/status, удаление;
- repository integration tests: фильтры, сортировка, пагинация, cascade;
- API tests: лимит upload, validation, not found, стабильная ошибка;
- frontend component tests: фильтры, loading/error/empty, escaping;
- один smoke test вертикального сценария перед release gate.

Полный suite запускается при изменении общих контрактов, миграций, security primitives и перед релизом. В остальных TASK — только целевые проверки.

## 13. Архитектурные инварианты

1. Только backend читает и хранит загруженные данные.
2. Парсер не зависит от FastAPI, SQLAlchemy и React.
3. UI не обращается к storage напрямую.
4. Невалидная строка не маскируется как валидная запись.
5. Фатально незавершённый импорт не показывается как `completed`.
6. Никакой пользовательский ввод не становится SQL, HTML или filesystem path.
7. Ресурсы запроса ограничены конфигурацией.
8. Публичный API меняется только отдельной TASK с review.

## 14. Отложенные решения

После MVP отдельно рассматриваются: несколько форматов Nginx, streaming/tailing, полнотекстовый индекс, агрегаты, retention, аутентификация, PostgreSQL, OpenTelemetry и LLM-анализ. Они не должны появляться «заранее» в текущих TASK.
