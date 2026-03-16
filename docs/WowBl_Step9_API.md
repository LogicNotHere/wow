# WowBl — Шаг 9: API (черновик контрактов, MVP)

Цель: описать **минимальный** набор API для MVP, строго по зафиксированной бизнес-логике и концептуальной модели данных.

Источник: `WowBl.md`, `WowBl_Step8_Domain.md`, `WowBl_Step8_DataModel.md`.

---

## 0) Общие принципы

- Все цены считаются на backend. Клиент **не** передаёт цену.
- Заказ всегда = **1 лот**.
- Guest (MVP): гость не оформляет заказ сам — только оставляет контакт; заказ создаёт Admin после оплаты + выдаёт magic link (read‑only).
- Платёж подтверждает Admin вручную.
- Системные уведомления Admin (MVP): in-app + realtime через socket (допустима заглушка); TTL 30 дней; `read/unread`.

---

## 1) Аутентификация и роли

### 1.1 Сессии
- MVP: обычная auth-сессия (cookie/JWT) для `customer/booster/admin/operator`.
- Guest: только magic link token (read‑only).

### 1.2 Роли (RBAC)
- `customer`: создаёт/смотрит свои заказы, пишет в чат своих заказов.
- `booster`: видит пул оплаченных заказов, может claim/accept/обновлять прогресс/чекпоинты, пишет в чат.
- `admin`: всё по заказам/оплатам/назначениям/спорам/уведомлениям + каталог.
- `operator`: каталог/опции/прайсы/промо (и post‑MVP ServicePage), но **без** оплат/споров/банов.

---

## 2) Каталог и витрина

### 2.1 Категории/лоты (public)
- `GET /api/public/service-categories/tree`
  - resp: дерево категорий (nested), для навигации на витрине
  - правило: скрываем категории, у которых есть неактивный предок; деактивация родителя скрывает всё поддерево
- `GET /api/public/service-lots?category_id=...`
- `GET /api/public/service-lots/{lot_id}`
  - включает: описание, опции, разрешённые execution modes, витринные теги (HIT/HOT и т.п.)

### 2.2 Preview цены (public)
- `POST /api/public/pricing/preview`
  - body: `{ lot_id, execution_mode, selected_options }`
  - resp: `{ currency: "EUR", total, breakdown, applied_promotion? }`

### 2.3 Guest lead (public)
- `POST /api/public/guest-contacts`
  - body: `{ channel, value }`
  - resp: `{ guest_contact_id }`

---

## 3) Orders — Customer (account)

### 3.1 Создать заказ (account only)
- `POST /api/customer/orders`
  - body: `{ lot_id, execution_mode, selected_options, guest_contact_id?: null }`
  - поведение:
    - backend пересчитывает цену
    - сохраняет `selected_options_json` и `price_snapshot_json`
    - создаёт заказ в `created`
  - resp: `{ order_id, public_number, status }`

### 3.2 Мои заказы
- `GET /api/customer/orders`
- `GET /api/customer/orders/{order_id}`
  - resp: `{ public_number, status, lot_snapshot, selected_options, price_snapshot, timeline, participants }`

### 3.3 Спор/отмена (минимум)
- `POST /api/customer/orders/{order_id}/cancel-request`
- `POST /api/customer/orders/{order_id}/dispute`

MVP: фактический outcome определяется Admin manual (статусы + refund).

---

## 4) Orders — Booster

### 4.1 Пул заказов (только оплаченные)
- `GET /api/booster/orders/available`
  - фильтры: `category` (mythic_plus/raid/pvp/professions), `execution_mode`, поиск
  - правило: backend отдаёт только `paid` (в UI можно маскировать как `created`)

### 4.2 Детали заказа (если доступен)
- `GET /api/booster/orders/{order_id}`

### 4.3 Claim (обычный бустер)
- `POST /api/booster/orders/{order_id}/claim`
  - поведение:
    - если booster tier = `super_booster`: переводит в `accepted` (без claim)
    - иначе: создаёт `order_claim` и переводит заказ в `needs_admin_review`

### 4.4 Принять назначенный заказ
- `POST /api/booster/orders/{order_id}/accept`
  - применимо если `assigned` и booster = назначенный
  - переводит в `accepted`

### 4.5 Старт и завершение
- `POST /api/booster/orders/{order_id}/start` → `in_progress`
- `POST /api/booster/orders/{order_id}/done` → `done`

### 4.6 Чекпоинты
- `POST /api/booster/orders/{order_id}/checkpoints`
  - body: `{ message, attachment_url? }`
- `GET /api/booster/orders/{order_id}/checkpoints`

---

## 5) Orders — Admin

### 5.1 Создать заказ по guest-сценарию (после оплаты)
- `POST /api/admin/orders/guest`
  - body: `{ guest_contact_id, lot_id, execution_mode, selected_options }`
  - поведение:
    - backend считает цену и сохраняет snapshot
    - создаёт заказ сразу `paid` (MVP) + генерирует `magic_link`
  - resp: `{ order_id, public_number, magic_link_url }`

### 5.2 Подтвердить оплату (manual)
- `POST /api/admin/orders/{order_id}/mark-paid`
  - body: `{ paid_at?, note? }`
  - перевод: `payment_pending → paid`

### 5.3 Назначение/апрув
- `POST /api/admin/orders/{order_id}/assign`
  - body: `{ booster_user_id }`
  - перевод: `paid → assigned`
- `POST /api/admin/orders/{order_id}/claims/{claim_id}/approve` → `accepted`
- `POST /api/admin/orders/{order_id}/claims/{claim_id}/decline` → `paid`

### 5.4 Управление статусами (manual)
- `POST /api/admin/orders/{order_id}/set-status`
  - body: `{ status, reason? }`
  - MVP: админ может закрывать `closed`, открывать `disputed`, ставить `canceled`, фиксировать `refunded/partial_refund`.

### 5.5 Refunds/Disputes (manual)
- `POST /api/admin/orders/{order_id}/refund`
  - body: `{ type: "full"|"partial", amount_eur?, reason }`
- `POST /api/admin/orders/{order_id}/disputes/{dispute_id}/resolve`

---

## 6) Чат (account orders, MVP)

### 6.1 Тред и сообщения
- `GET /api/orders/{order_id}/chat` (участники: customer/admin; booster после `accepted`)
- `POST /api/orders/{order_id}/chat/messages`
  - body: `{ body, attachment_url? }`

Guest по magic link в MVP в чат не допускается.

---

## 7) Уведомления (in-app + socket)

### 7.1 In-app список и отметка прочитанного
- `GET /api/admin/notifications`
  - фильтры: `unread_only`
- `POST /api/admin/notifications/{notification_id}/mark-read`
- `POST /api/admin/notifications/mark-all-read`

### 7.2 Socket (MVP: заглушка допустима)
- Канал: `admin.notifications`
- События:
  - `notification.created`
  - `order.updated`

---

## 8) Каталог — Admin/Operator

### 8.1 CRUD (минимум)
- `POST /api/admin/service-categories` / `PATCH` / `DELETE`
- Перемещение веток (смена `parent_id`) на MVP не делаем (только создание с нужным `parent_id`).
- `POST /api/admin/service-lots` / `PATCH` / `DELETE`
- `POST /api/admin/service-options` / `PATCH` / `DELETE`
- `POST /api/admin/pricing-rule-sets` / `PATCH`
- `POST /api/admin/promotions` / `PATCH` / `DELETE`

Право: `admin` и `operator` (кроме финансовых/заказных эндпоинтов).

При публикации лота: генерируется `service_lot_published` → in-app уведомление Admin.

---

## 9) Post‑MVP (не реализуем сейчас, но фиксируем интерфейс)

### 9.1 ServicePage (page builder)
`ServicePage` и `PageBlock` управляются из админки (Admin/Operator).
- `GET /api/public/service-lots/{lot_id}/page` (только `published`)
- `GET /api/admin/service-lots/{lot_id}/page`
- `PUT /api/admin/service-lots/{lot_id}/page` (upsert draft)
- `POST /api/admin/service-lots/{lot_id}/page/publish`
- `POST /api/admin/service-lots/{lot_id}/page/blocks`
- `PATCH /api/admin/service-lots/{lot_id}/page/blocks/{block_id}`
- `POST /api/admin/service-lots/{lot_id}/page/blocks/{block_id}/move` (изменить `position`)
- `DELETE /api/admin/service-lots/{lot_id}/page/blocks/{block_id}`

Валидация: backend валидирует `payload_json` по схеме типа блока.
