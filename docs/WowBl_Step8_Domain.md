# WowBl — Шаг 8: доменные сущности и модели данных (концептуально)

Фокус шага: описать **доменные сущности**, их ответственность, связи и инварианты. Пока без конкретных таблиц/ORM и без API.

Для “приближённого к БД” представления (pseudo‑ERD) см. `WowBl_Step8_DataModel.md`.

## 8.0 Контекст (важные принципы из бизнес-логики)
- Цена считается на backend, валюта MVP: **EUR**, цена фиксируется snapshot’ом при создании заказа.
- Оплата подтверждается **вручную Admin** (`PaymentPending → Paid`).
- Guest-сценарий: после оплаты Admin может создать заказ сразу в `Paid` и выдать гостю **magic link** на просмотр статуса/деталей (на MVP без чата).
- Бустеры **видят только оплаченные** заказы; в UI можно маскировать статус как `Created`.
- Бустер может “взять заказ”: обычный бустер требует апрув Admin (`NeedsAdminReview`), SuperBooster может `Paid → Accepted` без апрува.
- Один чат заказа: `customer↔admin`, booster добавляется **при `Accepted`**.
- Возвраты: после `Paid` и до `Accepted` — 100%, дальше manual (на усмотрение Admin).
- Скидки не суммируются; если лот “со скидкой”, промокоды/прочие скидки не применяются. `HIT/HOT` — витринные теги.
- Персонаж для выполнения на MVP: **ручной ввод** (интеграции raider.io не планируется).
- Выплаты бустерам на MVP: вручную вне системы; в кабинете бустера “заработок/пэйаут” не отображаем.
- Нотификации (MVP):
  - `order_in_progress`, `order_done` → Admin в **Discord**
  - `service_lot_published` → Admin **in-app** (в админке)
- Рассылки:
  - **Системные**: по событиям заказа (в т.ч. для Admin; post‑MVP — напоминания бустерам по рейдам).
  - **Маркетинговые**: только на email (детали opt‑in/unsubscribe — TBD).
- Post‑MVP: дополнительный режим выполнения **AnyDesk** (по логике как piloted), обязательный стрим для `Piloted` (ссылка в чат, опциональный Twitch embed), календарь/слоты рейдов от `RaidLeader`.

---

## 8.1 Пользователи и роли

### `User`
Единая сущность аккаунта.
- Атрибуты: email/логин, пароль/SSO, статус (active/banned), created_at.
- `staff_role` (nullable): `admin`, `manager`, `operator`, `content_manager`.
- `customer` не требует отдельной роли: любой зарегистрированный `User` может покупать.
- `booster` определяется наличием `BoosterProfile`, а не ролью.

### `OperatorPermissions` (концептуально)
Если роль `operator` нужна “как у админа, но безопасно”, фиксируем границу доступа:
- можно: CRUD каталога (`ServiceCategory/ServiceLot/ServiceOption`), промо/скидки/теги (`Promotion`), контент страниц лота (`ServicePage/PageBlock`, post‑MVP)
- нельзя: подтверждать оплаты, делать возвраты, банить пользователей, финально решать споры

### `BoosterProfile`
Профиль и допуски бустера.
- Связь: `User (1) → BoosterProfile (0..1)`.
- Атрибуты:
  - `approval_status` (draft/pending/approved/declined) — стадия рассмотрения профиля до допуска к booster-сценариям
  - `tier`/уровень (например `booster`, `super_booster`)
  - набор навыков/категорий (MVP: `mythic_plus`, `raid`, `pvp`, `professions`), рейтинг/статистика
  - `is_banned` (или через `User.status`)
  - `can_manage_calendar` (роль/допуск `RaidLeader`, post‑MVP для календаря рейдов)
- Персонаж для выполнения на MVP: хранится как **текст в заказе** (без отдельной сущности/списка персонажей).

### `RoleGrantRequest` (опционально)
Если нужно фиксировать “профиль заполнен → Admin рассмотрел” как отдельный объект.
- Связь: `User (1) → RoleGrantRequest (0..N)`
- Поля: requested_role=`booster`, status=pending/approved/declined, decided_by, decided_at.

### `CustomerProfile` (опционально на уровне домена)
Если нужен отдельный профиль (статистика/лояльность/пометки).
- Связь: `User (1) → CustomerProfile (0..1)`.
- Атрибуты: статистика заказов, флаги риска, internal tags.

### `AdminNote`
Внутренние заметки админа.
- Связь: `AdminNote → User (customer)` + `author_admin`.
- Назначение: пометки/статистика/риски (не видны клиенту).

---

## 8.2 Каталог услуг и ценообразование

### `ServiceCategory`
Категория услуг (Raid/M+/PvP/Leveling/Coaching/…).
- Атрибуты: название, slug, порядок, активность.
- Иерархия: `parent` (nullable) → категории образуют **дерево**.
- Инварианты:
  - без циклов (нельзя сделать категорию потомком самой себя)
  - лоты прикрепляются только к **leaf**-категориям (конечным узлам)
  - slug уникален **в пределах parent** (full path собирается из цепочки)
  - перемещения веток (смена `parent`) на MVP **не делаем**
  - деактивация родителя **скрывает всё поддерево** (на витрине)

### `ServiceLot` (или `Service`)
“Лот/услуга” внутри категории (то, что выбирает клиент).
- Атрибуты: название, описание, активность, `base_price_eur`, правила доступности.
- Связь: `ServiceCategory (1) → ServiceLot (N)`.
- Matching: `booster_category` (MVP fixed set: `mythic_plus`, `raid`, `pvp`, `professions`) — чтобы понимать, каким бустерам показывать заказ (независимо от витринного дерева).

### `ServiceOption`
Опции лота (difficulty, runs_count, piloted/self-play, etc.).
- Типы значений:
  - enum/choice
  - integer range (например количество ранов)
  - boolean (например “стрим”)
- В `config_json` храним не только UI-конфиг, но и ценовой эффект опции (`price_delta`/`multiplier`).
- Связь: `ServiceLot (1) → ServiceOption (N)`.

### `PricingRuleSet` (post‑MVP, отключено)
Сложный rules engine для pricing оставлен как future-вариант и в текущей модели закомментирован.
MVP-подход: цена считается от `ServiceLot.base_price_eur` + ценовые эффекты выбранных `ServiceOption`.

### `Promotion`
Промо/скидки/витринные теги.
- Скоуп: `category` или `lot`.
- Тип:
  - price discount (percent/fixed)
  - tag only (`HIT/HOT/SALE/NEW`)
- Период действия + enabled.
- Правила:
  - скидки не суммируются
  - если лот “со скидкой”, промокод/персональная скидка не применяются
Правило для дерева категорий: промо на категории действует на **поддерево**, если лот не имеет более приоритетного промо.

### `PromoCode` (если вводим)
Промокод как отдельная сущность (backlog, но лучше предусмотреть в домене).
- Атрибуты: code, discount, период, лимиты, правила совместимости.

---

## 8.3 Заказ и выполнение

### `Order`
Главная сущность заказа.
- Связи:
  - `Order.customer_user_id` (nullable для гостя)
  - `Order.guest_contact_id` (nullable, если есть `customer_user_id`)
  - `Order.magic_link_id` (nullable; на MVP — read-only доступ гостя)
  - `Order.booster_user_id` (nullable до `Assigned/Accepted`)
  - `Order.service_lot_id` (для навигации) + **snapshot** состава и цены
- Ключевые поля:
  - `public_number` (короткий номер/ID заказа для общения/саппорта)
  - `status` (Created/PaymentPending/Paid/NeedsAdminReview/Assigned/Accepted/RequirementsPending/InProgress/Done/Closed + ветки)
  - `execution_mode` (self_play / piloted / anydesk[post‑MVP])
  - `booster_character_text` (manual, optional)
  - `customer_contact` (например Discord/Telegram/email — если guest; можно держать в `GuestContact`)
  - `stream_url` (post‑MVP для piloted; ссылка в чат, опционально дублируем в заказ)
  - `price_snapshot` (см. ниже)
  - `in_progress_at` / `done_at` (для аналитики длительности без отдельного статуса `Scheduled`)

### `GuestContact`
Контакт гостя (если заказ без аккаунта).
- Поля: channel (email/discord/telegram/other), value, created_at.

### `MagicLink`
Токенизированный доступ для гостя.
- Поля: token_hash, expires_at (опционально), revoked_at (опционально), scope (MVP: read-only).
- Связь: `MagicLink (1) → Order (1)`
- Post‑MVP: может появиться `MagicLinkChatAccess` (разрешение писать в чат по токену).

### `OrderPriceSnapshot`
Неподвижный снимок того, что клиент купил и сколько это стоит.
- Содержит:
  - base + breakdown (primary driver, modifiers, discounts)
  - currency EUR
  - применённые promo ids / причины / запреты суммирования
  - версию прайс-правил

### `OrderClaim` (запрос бустера “взять заказ”)
Нужна для ветки `Paid → NeedsAdminReview`.
- Связь: `Order (1) → OrderClaim (0..N)` + `booster_user_id`.
- Статус: pending/approved/declined + author_admin.
- Инвариант: обычный бустер не может привести к `Accepted` без approved claim.

### `OrderTimelineEvent`
История событий/аудит (что/когда/кто).
- События: смена статуса, назначение, апрув/деклайн claim, добавление бустера в чат, чекпоинты, спор, возвраты.
- Нужна для прозрачности и разборов.

### `Checkpoint`
Чекпоинты выполнения (опционально с фото).
- Связь: `Order (1) → Checkpoint (0..N)`
- Атрибуты: текст, прогресс-метрика, вложения (если будут), created_by (booster/admin).

---

## 8.4 Оплата (manual)

### `Payment`
Факт оплаты (подтверждение Admin).
- Связь: `Order (1) → Payment (0..N)`
- Статус: pending/confirmed/failed/canceled (MVP можно проще: confirmed_at + confirmed_by).
- MVP: достаточно `confirmed_at` + `confirmed_by` (без хранения “доказательств оплаты”).

---

## 8.5 Споры и возвраты

### `Dispute`
Сущность спора.
- Связь: `Order (1) → Dispute (0..1)`
- Статус: open/under_review/resolved.
- Решение: refund partial/full / reject.

### `Refund`
Возврат (manual).
- Связь: `Order (1) → Refund (0..N)`
- Amount/currency, reason, decided_by.

---

## 8.6 Чат

### `ChatThread`
Один тред на заказ.
- Связь: `Order (1) → ChatThread (1)`

### `ChatParticipant`
Участники чата.
- На MVP:
  - customer + admin всегда
  - booster добавляется при `Accepted`
  - guest по magic link в чат **не** добавляется (post‑MVP)

### `ChatMessage`
Сообщения.
- Атрибуты: author, body, attachments (опционально), timestamps.

---

## 8.7 Инварианты (правила, которые должны соблюдаться в данных)
- `Paid` обязателен до `Accepted`/`InProgress` (но заказ в guest-сценарии может быть создан уже в `Paid`, без долгого `PaymentPending`).
- Booster не видит заказы до `Paid` (даже если в UI это маскируется как `Created`).
- Обычный booster не может перевести заказ в `Accepted` без апрува Admin (claim approved) или ручного `Assigned`.
- Promo stacking запрещён: если лот discounted, promo code/персональная скидка не применяется.
- Публичный отзыв возможен только после `Closed`.

---

## 8.8 Уведомления и рассылки (концептуально)

### Системные уведомления
Цель: доставлять сообщения по событиям заказа (и позже — по календарю).
- `NotificationEndpoint`: связь `User → endpoints` (email, telegram_id, discord_id, …).
- `SystemNotification`: событие + шаблон + список получателей + статус доставки (queued/sent/failed).
- (опционально) `InAppNotification` (колокольчик на сайте): отдельный канал/проекция тех же системных событий.
- Retention (MVP): `InAppNotification` храним **30 дней** (TTL/авто-очистка).
 - Статусы (MVP): `read/unread`.
Минимальные события по текущей бизнес-логике:
- `order_in_progress` (получатель: Admin, канал: in_app)
- `order_done` (получатель: Admin, канал: in_app)
- `service_lot_published` (получатель: Admin, канал: in_app)

Примечание по MVP: realtime-доставка в админку делается через **socket** (на MVP допустима “заглушка”), а интеграции Discord/Telegram/email оформляются как post‑MVP адаптеры доставки.

### Маркетинговые рассылки (post‑MVP, email)
Цель: промо/ретеншн, отдельно от системных писем.
- `MarketingSubscription`: `User`, status (opted_in/opted_out), источники согласия.
- `MarketingCampaign` (если делаем ручные/плановые кампании): аудит отправок + лимиты частоты.

---

## 8.9 Post‑MVP расширения (чтобы не потерять требования)

### AnyDesk / удалённый assist
Если добавляем `execution_mode=anydesk`, удобно вынести “секретные данные/инструкции” в отдельный объект:
- `OrderAccessPayload`: тип (anydesk/piloted), payload (encrypted), created_by, expires_at, revoked_at.

### Стрим для piloted
- MVP: можно жить только сообщением в `ChatMessage`.
- Post‑MVP: если нужно “закреплённое поле” — `Order.stream_url` (уже предусмотрено) + аудит обновлений в `OrderTimelineEvent`.

### Календарь рейдов (очень поздно)
Скелет домена, если дойдём:
- `RaidLeaderProfile` (расширение `BoosterProfile`): флаг `can_manage_calendar`.
- `RaidSchedule`: владелец (raid leader), timezone, период активности.
- `RaidSlot`: start_at/end_at, lot_scope (какой лот/сложность), доступные опции (например “только cloth/leather”), capacity/лимиты.
- `RaidBooking`: ссылка на `Order`, выбранный `RaidSlot`, статус booked/canceled/rescheduled.

### Бот-напоминания
- `NotificationJob`: тип (raid_reminder_30m), target_user_id, planned_at, sent_at, channel (discord/telegram/email), payload.

### Чат по magic link
- `MagicLinkChatAccess`: magic_link_id, expires_at, revoked_at, rate_limits.

### Страница лота (ServicePage) и контент-блоки (PageBlock)
Если хотим управляемое описание лота без правок кода (page builder).
- `ServicePage`: привязана к одному `ServiceLot`, имеет `status` (draft/published), метаданные, аудит изменений.
- `PageBlock`: принадлежит `ServicePage`, имеет `type`, `position`, `payload` (JSON).
- `PageBlockType` (registry): поддерживаемый набор типов блоков (text/list/table/faq/...), схема валидации payload по типу.
Инварианты:
- `ServicePage` всегда привязана к одному `ServiceLot`.
- Блоков может быть 0..N, порядок задаёт `position`.
- `type` должен принадлежать поддерживаемому набору.
- `payload` валидируется по схеме типа при сохранении.
- Только `published` отображается пользователям.

Вопросы (когда дойдём до реализации):
1) Нужна ли **мультиязычность** для `ServicePage` (EN/RU) или один язык на старте?
2) Какие типы блоков фиксируем в MVP-2 (минимум): `text`, `list`, `table`, `faq` — достаточно?
3) Нужен ли **preview** (draft виден только Admin/Operator) и версионирование изменений?

## Зафиксировано (по твоим ответам)
- Заказ всегда = **1 лот** (без `OrderItem`/корзины).
- Навыки бустера: достаточно **категорий** (без детальных капов M+ N / рейд-ролей и т.п. на старте).
- Роли/допуски бустеров: `SuperBooster` (авто-accept) + `RaidLeader` (post‑MVP календарь рейдов, `can_manage_calendar=true`).
- Оплата: достаточно `Paid` (confirmed_at/by), без хранения доказательств.
- Guest (MVP): без аккаунта можно только смотреть лоты и оставить контакт; заказ в системе создаёт Admin (после оплаты) + magic link на read‑only.
- Маркетинг: позже.
