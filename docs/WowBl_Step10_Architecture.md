# WowBl — Шаг 10: архитектура backend (FastAPI, MVP)

Контекст: отдельный изолированный проект (не интегрируемся с текущим репо/модулями). Стек: **FastAPI (async)** + **Postgres** + **Redis**. Архитектурный стиль: **Modular Monolith + Vertical Slices + Layered внутри каждого слайса**.

Цель документа: зафиксировать “как будем собирать приложение”, чтобы затем без перескоков перейти к **моделям БД (Шаг 11)** и **реализации API (Шаг 12)**.

Связанные документы:
- Бизнес-логика: `WowBl.md`
- Доменные сущности: `WowBl_Step8_Domain.md`
- Концептуальная модель данных: `WowBl_Step8_DataModel.md`
- Черновик API: `WowBl_Step9_API.md`

---

## 1) Что строим (MVP)

**Одна backend-апка** (монолит), но внутри — набор независимых “модулей/слайсов”:
- `catalog` (дерево категорий, лоты, опции, прайс-правила, промо)
- `pricing` (preview и формирование snapshot)
- `orders` (state machine, claims, assignment, timeline, checkpoints)
- `payments` (manual mark-paid)
- `chat` (account orders)
- `notifications` (in-app + socket заглушка; TTL 30 дней; read/unread)
- `auth` (сессии/пользователи/роли)
- `admin` (RBAC/операции)

MVP не тянет интеграции Discord/Telegram/email для уведомлений: оставляем как post‑MVP “adapters”.

---

## 2) Принципы архитектуры

### 2.1 Modular monolith
- Код разделён на **слайсы**, каждый слайс минимально знает о других.
- Общие вещи (DB/Config/Auth/RBAC) — в `core/` и `shared/`.
- Зависимости между слайсами — через **явные интерфейсы** (например, `pricing` используется в `orders` как сервис).

### 2.2 Vertical slices
Каждый use-case/фича живёт “вертикально” внутри своего слайса: от роутера до репозитория и доменных правил.

### 2.3 Layered внутри слайса
Минимальный набор слоёв (без overengineering):
- `api/` — FastAPI routers + request/response schemas
- `app/` — use-cases (команды/запросы), orchestration, транзакции
- `domain/` — правила, инварианты, value objects, enums
- `infra/` — ORM-модели, репозитории, реализации интерфейсов, Redis

---

## 3) Технические решения (MVP)

### 3.1 DB
- Postgres — источник истины (orders, catalog, notifications, chat, disputes).
- Миграции: Alembic.
- ORM: SQLAlchemy 2.x async (`AsyncSession`) + `asyncpg`.

### 3.2 Redis
- Используем под:
  - rate limiting (если понадобится)
  - кэш (опционально)
  - (позже) pub/sub для websocket/уведомлений
- MVP: можно ограничиться “socket заглушкой” без Redis pub/sub.

### 3.3 Realtime (socket)
- MVP: WebSocket endpoint(ы) для админки (`admin.notifications`, `order.updated`), допускается заглушка.
- Источник данных: таблица `in_app_notifications` (TTL 30 дней), статусы `read/unread`.

---

## 4) Структура проекта (рекомендация)

Пример структуры (workspace-level):
```
src/
  main.py
  core/
    config.py
    db.py
    security.py
    errors.py
  shared/
    enums.py
    pagination.py
    time.py
  slices/
    catalog/
      api/
      app/
      domain/
      infra/
    pricing/
      api/
      app/
      domain/
      infra/
    orders/
      api/
      app/
      domain/
      infra/
    notifications/
      api/
      app/
      domain/
      infra/
    chat/
      api/
      app/
      domain/
      infra/
    auth/
      api/
      app/
      domain/
      infra/
```

Правило: любой слайс может иметь свою “мини-архитектуру”, но без утечек деталей в другие слайсы.

---

## 5) Транзакции и репозитории

- Use-case в `app/` управляет транзакцией (unit-of-work) и вызывает репозитории `infra/`.
- В `orders` при любых изменениях статуса:
  - пишем `order_timeline_event`
  - создаём/обновляем `in_app_notification` (если событие должно алертить Admin)

---

## 6) RBAC и права

RBAC на уровне:
- роутов (FastAPI dependencies)
- “опасных” use-case (доп. проверки в `app/`)

`User.staff_role`: `admin`, `manager`, `operator`, `content_manager`.

`customer` не нужен как RBAC-роль: любой зарегистрированный `User` может покупать.
`booster` не нужен как RBAC-роль: он определяется через `BoosterProfile`.

Отдельно: “бустер категории” (`mythic_plus/raid/pvp/professions`) — это **matching**, а не витринная структура.

---

## 7) Каталог: дерево категорий

Поддерживаем дерево `ServiceCategory` с правилами:
- `slug` уникален **в пределах parent**
- перемещения веток (смена `parent_id`) на MVP **нет**
- деактивация родителя скрывает всё поддерево
- лоты прикрепляются только к **leaf**-категориям

---

## 8) Следующие шаги (что делаем дальше)

### Шаг 11 — Модели БД
1) Поднять `core/db.py` (async engine/session) + Alembic.
2) Реализовать таблицы из `WowBl_Step8_DataModel.md` (MVP subset).
3) Прописать индексы/уникальности (`unique(parent_id, slug)`, `public_number`, TTL для `in_app_notifications` через `expires_at` + job).

### Шаг 12 — Реализация API
1) Поднять роутеры по `WowBl_Step9_API.md`.
2) Реализовать use-cases по слайсам.
3) Добавить минимальные интеграционные тесты (API + DB).

---

## 9) Открытые вопросы (архитектурные, но не блокируют старт)

1) Как генерируем `public_number`: префикс (`ORD-`) + base32/ulid, или просто короткий random?
2) TTL cleanup `in_app_notifications`: cron/worker (post‑MVP) или периодическая задача внутри приложения?
3) Auth: email+password или SSO? (влияет на модели и роуты `auth`).
