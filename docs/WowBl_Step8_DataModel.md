# WowBl — Шаг 8: концептуальная модель данных (pseudo‑ERD)

Цель: описать **сущности/поля/связи** на уровне, достаточном для проектирования БД и API. Это всё ещё **без** конкретного ORM/миграций.

Документ дополняет `WowBl_Step8_Domain.md`: там — доменные смыслы, здесь — “как это выглядит в данных”.

---

## 0) Ключевые решения (зафиксировано)

- Guest (MVP): гость **не** создаёт заказ; может только смотреть лоты и оставить контакт. Заказ создаёт **Admin** после оплаты + выдаёт **magic link** (read‑only).
- Заказ всегда = **1 лот** (без корзины/`OrderItem`).
- Оплата (MVP): достаточно флага/таймстемпа `paid_at` + `paid_by_admin_id`, без хранения доказательств.
- `Scheduled` как статус **не используем**; аналитику делаем по `in_progress_at`/`done_at`.
- Системные уведомления Admin (MVP): **in-app** + realtime через **socket** (может быть заглушкой). Discord/Telegram/email как адаптеры доставки — post‑MVP.
- `InAppNotification` retention (MVP): **30 дней**.
- Booster skills: уровень **категорий** (для балансировки/фильтрации).

---

## 1) Справочники (enums / reference data)

### 1.1 `UserRole`
- `admin`
- `manager`
- `operator`
- `content_manager`

### 1.2 `UserStatus`
- `active`
- `banned`

### 1.3 `BoosterTier`
- `booster`
- `super_booster` (может переводить `Paid → Accepted` без апрува Admin)

### 1.4 `BoosterCategory` (matching/skills)
- `mythic_plus`
- `raid`
- `pvp`
- `professions`

### 1.5 `OrderStatus`
- `created`
- `payment_pending`
- `paid`
- `needs_admin_review`
- `assigned`
- `accepted`
- `requirements_pending`
- `in_progress`
- `done`
- `closed`
- ветки: `canceled`, `disputed`, `refunded`, `partial_refund`

### 1.6 `ExecutionMode`
- `self_play`
- `piloted`
- post‑MVP: `anydesk`

---

## 2) Пользователи и доступы

### 2.1 `users`
**PK:** `id`
- `email` (unique, nullable если будет иной логин)
- `password_hash` (или SSO)
- `status` (`UserStatus`)
- `staff_role` (`UserRole`, nullable)
- `created_at`

`customer` не хранится как роль: это базовый сценарий любого зарегистрированного `User`.
`booster` не хранится как роль: eligibility определяется через `booster_profiles`.

### 2.2 `booster_profiles`
**PK:** `user_id` (FK → `users.id`)
- `approval_status` (`draft` / `pending` / `approved` / `declined`)
- `tier` (`BoosterTier`)
- `categories` (массив `BoosterCategory` или отдельная таблица `booster_categories`)
- `can_manage_calendar` (bool, post‑MVP `RaidLeader`)
- `discord_url` (или `contact_value`)
- `created_at`, `updated_at`

### 2.3 `admin_notes`
**PK:** `id`
- `target_user_id` → `users.id`
- `author_admin_id` → `users.id`
- `note` (text)
- `created_at`

---

## 3) Каталог, опции и прайсинг

### 3.1 `service_categories`
**PK:** `id`
- `name`
- `slug`
- `parent_id` → `service_categories.id` (nullable)
- `is_active`
- `sort_order`

Рекомендованные правила:
- уникальность `slug` в рамках parent: `unique(parent_id, slug)` (а “полный путь” собирается по цепочке)
- запрет циклов (валидируется на backend)
- лоты можно прикреплять только к leaf-узлам
- перемещения веток (смена `parent_id`) на MVP не делаем: `parent_id` считается immutable после создания
- деактивация родителя скрывает всё поддерево (публичные API фильтруют по активным предкам)

### 3.2 `service_lots`
**PK:** `id`
- `category_id` → `service_categories.id`
- `name`
- `description` (text)
- `is_active`
- `base_price_eur` (float, MVP базовая цена лота)
- `booster_category` (`BoosterCategory`) (для matching/пула бустеров, независимо от витринного дерева)
- `execution_modes_allowed` (массив `ExecutionMode` либо флаги)
- `tags` (витринные: `HIT/HOT/SALE/NEW`, без влияния на цену)
- `created_at`, `updated_at`

### 3.2.1 `service_pages` (post‑MVP)
Витринная страница лота (page builder), из блоков.

**PK:** `id`
- `lot_id` → `service_lots.id` (unique, 0..1 page per lot)
- `status` (`draft`/`published`)
- `title` (nullable)
- `meta_json` (nullable: SEO/OG и прочие метаданные страницы, а не контент блоков)
- `created_by_user_id` → `users.id`
- `updated_by_user_id` → `users.id`
- `published_at` (nullable, когда страница стала публичной)
- `created_at`, `updated_at`

Инвариант: только `published` отдаём на витрину.

### 3.2.2 `service_page_blocks` (post‑MVP)
Блоки страницы, порядок по `position`.

**PK:** `id`
- `page_id` → `service_pages.id`
- `position` (int, порядок блока на странице)
- `type` (enum/string: `text`/`list`/`table`/`faq`/…)
- `payload_json` (структурированные данные блока; состав зависит от `type`)
- `created_at`, `updated_at`

Инварианты:
- `(page_id, position)` уникальны.
- `type` ∈ поддерживаемым типам.
- `payload_json` валидируется по схеме типа на backend.

### 3.2.3 `page_block_type_schemas` (опционально, post‑MVP)
Если хотим управлять/версировать схемы через данные, а не код.

**PK:** `id`
- `type` (unique)
- `schema_json` (JSON Schema или аналог)
- `version`
- `is_active`

### 3.3 `service_options`
Опции лота (то, что выбирает customer при создании заказа).

**PK:** `id`
- `lot_id` → `service_lots.id`
- `code` (например `difficulty`, `runs_count`, `armor_stack`)
- `value_type` (`enum` / `int_range` / `bool` / `text`)
- `config_json` (доп. настройки опции + ценовой эффект: `price_delta`/`multiplier`)
- `is_required`
- `sort_order`

### 3.4 `pricing_rule_sets` (post‑MVP, отключено в текущей модели)
**PK:** `id`
- `scope_type` (`category`/`lot`)
- `scope_id` (FK на `service_categories.id` или `service_lots.id`)
- `currency` (MVP: `EUR`)
- `rules_json` (формулы/коэффициенты/округление, из которых backend считает цену)
- `version` (int)
- `is_active`
- `created_at`

MVP сейчас работает без этой таблицы: цена считается от `service_lots.base_price_eur` и выбранных `service_options`.

### 3.5 `promotions`
**PK:** `id`
- `scope_type` (`category`/`lot`)
- `scope_id` (id категории или лота, в зависимости от `scope_type`)
- `promo_type` (`discount_percent` / `discount_fixed` / `tag_only`)
- `value` (numeric, nullable для `tag_only`; размер скидки)
- `tag` (например `HIT/HOT`, nullable; только витринная метка)
- `starts_at`, `ends_at` (nullable)
- `is_enabled`

Правило: скидки **не суммируются**, “лот уже со скидкой” → промокоды/прочие скидки не применяем.

---

## 4) Guest lead + magic link

### 4.1 `guest_contacts`
**PK:** `id`
- `channel` (`email`/`discord`/`telegram`/`other`)
- `value` (строка контакта в выбранном канале)
- `created_at`

### 4.2 `magic_links`
**PK:** `id`
- `order_id` → `orders.id`
- `token_hash` (никогда не храним raw token)
- `scope` (MVP: `read_only`)
- `expires_at` (nullable, если хотим ограничить срок жизни ссылки)
- `revoked_at` (nullable, если ссылку нужно отключить вручную)
- `created_at`

---

## 5) Заказ и выполнение

### 5.1 `orders`
**PK:** `id`
- `public_number` (внешний номер заказа для клиента/саппорта, не равен внутреннему `id`)
- `status` (`OrderStatus`)
- `execution_mode` (`ExecutionMode`)

**Стороны:**
- `customer_user_id` → `users.id` (nullable для guest)
- `guest_contact_id` → `guest_contacts.id` (nullable для account orders)
- `booster_user_id` → `users.id` (nullable до `assigned/accepted`)

**Каталог:**
- `service_lot_id` → `service_lots.id`
- `selected_options_json` (snapshot выбранных значений опций на момент создания заказа)

**Цена:**
- `price_snapshot_json` (snapshot расчёта цены на момент создания заказа)

**Тайминги/аналитика:**
- `paid_at` (nullable)
- `paid_by_admin_id` → `users.id` (nullable, какой Admin подтвердил оплату вручную)
- `accepted_at` (nullable)
- `in_progress_at` (nullable)
- `done_at` (nullable)
- `closed_at` (nullable)

**Прочее:**
- `internal_note` (nullable, admin-only заметка по заказу)
- `booster_character_text` (nullable, manual) — если нужно указать персонажа для выполнения
- `created_at`, `updated_at`

Инварианты:
- `paid_at` обязателен до `accepted/in_progress`.
- заказ для guest может создаваться сразу в `paid`.

### 5.2 `order_claims` (для `needs_admin_review`)
**PK:** `id`
- `order_id` → `orders.id`
- `booster_user_id` → `users.id`
- `status` (`pending`/`approved`/`declined`)
- `decided_by_admin_id` → `users.id` (nullable, кто из Admin принял решение)
- `created_at`, `decided_at`

### 5.3 `order_timeline_events`
**PK:** `id`
- `order_id` → `orders.id`
- `event_type` (string/enum; тип события для таймлайна)
- `actor_user_id` → `users.id` (nullable для system)
- `payload_json` (доп. данные события, если нужны)
- `created_at`

### 5.4 `checkpoints`
**PK:** `id`
- `order_id` → `orders.id`
- `created_by_user_id` → `users.id`
- `message` (text)
- `attachment_url` (nullable, если будет)
- `created_at`

### 5.5 `order_price_snapshots` (опционально, если не хотим JSON в `orders`)
Если захотим нормализовать, можно вынести в отдельную таблицу.
- иначе используем `orders.price_snapshot_json`.

Рекомендуемый состав snapshot:
- `currency=EUR`
- `base_price`
- `breakdown` (driver/modifiers)
- `discount` (если применён)
- `pricing_rule_set_version`
- `promotion_id` (nullable)

---

## 6) Оплата (manual)

### 6.1 `payments` (опционально на MVP)
Можно начать без таблицы и хранить только `paid_at/paid_by_admin_id` в `orders`.
Если нужна история/аудит:

**PK:** `id`
- `order_id` → `orders.id`
- `status` (`confirmed`/`canceled`)
- `confirmed_at`
- `confirmed_by_admin_id` → `users.id`
- `created_at`

---

## 7) Споры и возвраты (manual)

### 7.1 `disputes`
**PK:** `id`
- `order_id` → `orders.id` (unique, 0..1)
- `status` (`open`/`under_review`/`resolved`)
- `reason` (text)
- `opened_by_user_id` → `users.id`
- `resolved_by_admin_id` → `users.id` (nullable)
- `resolution_json` (refund/reject/notes)
- `created_at`, `resolved_at`

### 7.2 `refunds`
**PK:** `id`
- `order_id` → `orders.id`
- `type` (`full`/`partial`)
- `amount_eur` (numeric)
- `reason` (text)
- `decided_by_admin_id` → `users.id`
- `created_at`

---

## 8) Чат (только для авторизованных заказов в MVP)

### 8.1 `chat_threads`
**PK:** `id`
- `order_id` → `orders.id` (unique)
- `created_at`

### 8.2 `chat_participants`
**PK (composite):** `thread_id`, `user_id`
- `thread_id` → `chat_threads.id`
- `user_id` → `users.id`
- `role_in_thread` (`customer`/`admin`/`booster`)
- `joined_at`

Правило: booster добавляется при `accepted`.

### 8.3 `chat_messages`
**PK:** `id`
- `thread_id` → `chat_threads.id`
- `author_user_id` → `users.id`
- `body` (text)
- `attachment_url` (nullable)
- `created_at`

---

## 9) Уведомления (in-app + socket)

### 9.1 `notification_endpoints` (post‑MVP)
Если/когда добавим доставку в Discord/Telegram/email.

**PK:** `id`
- `user_id` → `users.id`
- `channel` (`discord`/`telegram`/`email`)
- `endpoint_value` (например discord_user_id, telegram_chat_id, email)
- `is_enabled`

### 9.2 `system_notifications`
Аудит того, что “сгенерировали” и куда отправляли (важно для retry).

**PK:** `id`
- `event_type` (`order_in_progress`, `order_done`, `service_lot_published`, …)
- `target_user_id` → `users.id`
- `channel` (`in_app`, post‑MVP: `discord/telegram/email`)
- `payload_json`
- `status` (`queued`/`sent`/`failed`)
- `created_at`, `sent_at`

### 9.3 `in_app_notifications`
Материализованная проекция для админки (“колокольчик”).

**PK:** `id`
- `user_id` → `users.id`
- `title`
- `body` (text)
- `payload_json` (ссылка на order/lot и т.п.)
- `is_read` (bool)
- `created_at`
- `expires_at` (TTL = `created_at + 30 days`)

Socket (MVP): отправляем событие “new notification / updated order” как realtime слой поверх `in_app_notifications`.

---

## 10) Operator (контент-роль)

### 10.1 Граница прав (MVP)
- может: CRUD `service_categories/service_lots/service_options/promotions` (+ post‑MVP `pricing_rule_sets/service_pages/service_page_blocks`)
- нельзя: `orders` статусы/назначения, оплаты, возвраты/споры, баны пользователей
