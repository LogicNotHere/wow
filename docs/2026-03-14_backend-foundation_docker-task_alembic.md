# 2026-03-14 — Backend Foundation, Docker, Task и Alembic

Дата: **14 марта 2026**

Этот документ фиксирует, что было реализовано за день в проекте `WowShop`:
- базовый каркас backend под `Modular Monolith + Vertical Slices`
- контейнеризация (`Dockerfile`, `docker-compose`)
- task-обвязка (`Taskfile`)
- база под единый DB foundation
- разнос ORM-моделей по модулям
- подключение и проверка Alembic с первой миграцией

---

## 1. Архитектурный курс, который зафиксировали

Были подтверждены и приняты как обязательные правила:
- это **монолитное приложение**, не микросервисная схема
- один runtime app (`api`)
- одна PostgreSQL база
- модули разделены логически внутри одного приложения
- модели лежат в модулях-владельцах
- у всех моделей общий SQLAlchemy `Base`
- Alembic работает через одну общую `metadata`
- один общий поток миграций для всего проекта

---

## 2. Каркас проекта

### Что сделали сначала

Сначала был создан минимальный каркас слоёв:
- `core`
- `shared`
- `modules/*/(api, application, domain, infrastructure)`
- `migrations`
- `tests`

### Что изменили позже

Изначально каркас был в `src`, но затем перешли на пакет `wow_shop` как единственный рабочий namespace.

Итог:
- рабочий пакет: `wow_shop/`
- legacy-папка `src/` удалена, чтобы не было дублирующей структуры

Точка входа приложения:
- `wow_shop/app.py`

---

## 3. Docker и compose

### Реализованные файлы

- `Dockerfile`
- `docker-compose.yml`
- `.env`
- `.env.example`
- `.dockerignore`

### Принятый runtime

- сервис `api` (FastAPI/uvicorn)
- сервис `postgres` (PostgreSQL 16)
- без Redis на первом этапе

### Важные параметры запуска

- запуск app: `uvicorn wow_shop.app:app --host ${APP_HOST} --port ${APP_PORT} --reload`
- в compose подключен bind mount `.:/app`
- hot-reload работает без постоянного rebuild при изменениях Python-кода

---

## 4. Taskfile как обёртка над docker compose

### Реализованный файл

- `Taskfile.yaml`

### Что настроено

- дефолтный task ведёт на `server`
- `server` поднимает `api + postgres`
- добавлены управляющие команды для dev-цикла

Базовые команды:
- `task` / `task server`
- `task build`
- `task down`
- `task restart`
- `task ps`
- `task shell`

---

## 5. Линтеры, mypy, isort и pre-commit

### Реализованные файлы и настройки

- `.flake8`
- `mypy.ini`
- `.pre-commit-config.yaml`
- обновлён `pyproject.toml` (`dev` зависимости)

Добавлено:
- `flake8`
- `mypy`
- `isort`
- `pre-commit`

Также добавлена task-цепочка:
- `pre-commit` -> `isort` -> `flake8` -> `mypy`

---

## 6. Документация вынесена в docs

Файлы `WowBl*.md` перенесены из корня в `docs/`:
- `docs/WowBl.md`
- `docs/WowBl_ForClient_Clean.md`
- `docs/WowBl_ServicePage_AdminFlow.md`
- `docs/WowBl_Step8_DataModel.md`
- `docs/WowBl_Step8_Domain.md`
- `docs/WowBl_Step9_API.md`
- `docs/WowBl_Step10_Architecture.md`

Обновлена ссылка в `README.md` на новый путь `docs/WowBl.md`.

---

## 7. DB foundation под Modular Monolith

### Общая инфраструктура базы

Создана единая DB-инфраструктура:
- `wow_shop/infrastructure/db/base.py`
- `wow_shop/infrastructure/db/session.py`
- `wow_shop/infrastructure/db/models.py` (агрегатор импортов моделей)

### Что важно в `base.py`

Реализованы:
- единый `MetaData`
- единый `Base`
- `naming_convention` для:
  - `pk`
  - `fk`
  - `uq`
  - `ix`
  - `ck`

Это нужно для одинакового и предсказуемого именования constraint/index в миграциях.

### Что важно в `models.py` (агрегатор)

Агрегатор импортирует model-модули всех фич:
- auth
- catalog
- pricing
- orders
- payments
- chat
- notifications

Цель:
- зарегистрировать все таблицы в одном `Base.metadata`
- дать Alembic единую точку `target_metadata`

---

## 8. Разнос ORM-моделей по модулям

Модели вынесены из единого `models.py` в модульные файлы:

- `wow_shop/modules/auth/infrastructure/db/models.py`
- `wow_shop/modules/catalog/infrastructure/db/models.py`
- `wow_shop/modules/pricing/infrastructure/db/models.py`
- `wow_shop/modules/orders/infrastructure/db/models.py`
- `wow_shop/modules/payments/infrastructure/db/models.py`
- `wow_shop/modules/chat/infrastructure/db/models.py`
- `wow_shop/modules/notifications/infrastructure/db/models.py`

Удалён legacy giant-файл:
- `models.py`

### Ownership, который соблюдён

- `auth`: `User`, `BoosterProfile`, `AdminNote`
- `catalog`: `ServiceCategory`, `ServiceLot`, `ServiceOption`, `ServicePage`, `ServicePageBlock`
- `pricing`: `Promotion`
- `orders`: `GuestContact`, `MagicLink`, `Order`, `OrderClaim`, `Checkpoint`
- `payments`: `Payment`, `Refund`
- `chat`: `ChatThread`, `ChatParticipant`, `ChatMessage`
- `notifications`: `NotificationEndpoint`, `SystemNotification`, `InAppNotification`

### По межмодульным связям

- межмодульные FK оставлены (это допустимо в монолите)
- ownership таблиц не нарушен
- избегали превращения моделей в чрезмерно связанный giant ORM graph

---

## 9. Alembic: полноценное подключение

### Создана структура Alembic

В существующей папке `migrations/` созданы:
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/`

Добавлен:
- `alembic.ini`

`.gitkeep` в `migrations` удалён как устаревший.

### Логика `env.py`

Сделано:
- загрузка `DATABASE_URL` из окружения
- fallback чтение `.env` (если запуск с хоста)
- преобразование async DSN в sync DSN:
  - `postgresql+asyncpg://...` -> `postgresql+psycopg://...`
- импорт `target_metadata` из:
  - `wow_shop.infrastructure.db.models`

Это даёт:
- один источник правды для URL
- один поток миграций
- совместимость с async-приложением и sync-Alembic

---

## 10. Первая миграция (init schema)

### Что выполнено

Сгенерирована первая миграция автогенерацией:
- `migrations/versions/ba9390fe80ac_init_schema.py`

Проверка пройдена:
- `alembic upgrade head` выполнен успешно
- `alembic current -v` показал `ba9390fe80ac (head)`
- `alembic history` показал цепочку `<base> -> ba9390fe80ac`

### Нюанс, который исправили

В `catalog_service_pages` был двойной unique по `lot_id` (`unique=True` + `UniqueConstraint`).
Исправлено:
- убран дублирующий `unique=True` в ORM-модели
- миграция приведена к одному unique constraint

---

## 11. Task-команды для миграций (реальные, не заглушки)

Обновлены задачи в `Taskfile.yaml`:
- `migrate` -> `alembic upgrade head`
- `makemigrations` -> `alembic revision --autogenerate -m "${MSG:-migration}"`
- `downgrade` -> `alembic downgrade -1`
- `current` -> `alembic current`
- `history` -> `alembic history`

Основной workflow миграций — через Docker (`docker compose exec api ...`).

---

## 12. Почему итоговое решение корректно именно для modular monolith

Потому что:
- один app runtime
- одна БД
- одна metadata
- один Alembic flow
- модели разделены по модулям по ownership
- при этом нет микросервисного дробления на отдельные базы/миграции/контейнеры

Это сохраняет архитектурные границы в коде и упрощает эксплуатацию схемы данных.

---

## 13. Текущее практическое состояние

На конец дня в проекте есть:
- рабочая базовая backend-структура
- docker runtime для локальной разработки
- task-обёртка для ежедневных команд
- подключённые линтеры и pre-commit
- модульно разложенные ORM-модели
- подключённый и проверенный Alembic
- первая применённая миграция `init schema`

Это уже полноценная техническая база, на которой можно начинать реализацию прикладных use-case и API по слайсам.
