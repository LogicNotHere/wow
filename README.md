# WowShop

Черновик backend/domain модели для WoW boosting marketplace.

Основа берётся из [WowBl.md](/Users/vitalii/Projects/WowShop/docs/WowBl.md): один заказ = один лот, backend считает цену, оплата на MVP подтверждается вручную админом, бустер получает заказ только после `Paid`.

## Текущие решения

- `User` — базовая учетная запись.
- Любой зарегистрированный `User` может быть customer без отдельной роли.
- Backoffice-доступ хранится в `User.staff_role`.
- Бустер определяется не ролью, а наличием `BoosterProfile`.
- `BoosterProfile.user_id` — одновременно `PK` и `FK -> users.id`, то есть это расширение `User` в связи `1:0..1`.
- Каталог иерархический: `Game -> ServiceCategory (tree) -> ServiceLot`.
- Прайс на MVP считается от `ServiceLot.base_price_eur` и выбранных `ServiceOption`.
- `PricingRuleSet` пока не активирован в текущем ORM, оставлен как future-вариант в доменной документации.

## Pricing MVP

Сейчас pricing устроен так:

- у лота есть базовая цена `base_price_eur`
- у опций есть конфиг и ценовой эффект в `config_json`
- итоговая цена заказа считается на backend
- результат расчета фиксируется в `Order.price_snapshot_json`

Упрощенная формула:

```text
final_price = service_lot.base_price_eur + sum(selected option price deltas)
```

Примеры того, что может лежать в `ServiceOption.config_json`:

```json
{
  "choices": [
    { "value": "self_play", "label": "Self Play", "price_delta": 0 },
    { "value": "piloted", "label": "Piloted", "price_delta": 15 }
  ]
}
```

```json
{
  "type": "boolean",
  "true_price_delta": 8,
  "false_price_delta": 0
}
```

## Полная модель

`Promotion` использует полиморфную связку `scope_type + scope_id`, поэтому на диаграмме показывается без прямого FK на категорию или лот.

```mermaid
erDiagram
    USER ||--o| BOOSTER_PROFILE : has
    USER ||--o{ ADMIN_NOTE : authors
    USER ||--o{ ORDER : creates
    USER ||--o{ ORDER : executes
    USER ||--o{ ORDER : marks_paid
    USER ||--o{ ORDER_CLAIM : claims
    USER ||--o{ ORDER_CLAIM : decides
    USER ||--o{ CHECKPOINT : writes
    USER ||--o{ PAYMENT : confirms
    USER ||--o{ REFUND : decides
    USER ||--o{ CHAT_PARTICIPANT : joins
    USER ||--o{ CHAT_MESSAGE : writes

    GAME ||--o{ SERVICE_CATEGORY : contains
    SERVICE_CATEGORY ||--o{ SERVICE_CATEGORY : parent_of
    SERVICE_CATEGORY ||--o{ SERVICE_LOT : contains
    SERVICE_LOT ||--o{ SERVICE_OPTION : has
    SERVICE_LOT ||--o| SERVICE_PAGE : has
    SERVICE_PAGE ||--o{ SERVICE_PAGE_BLOCK : contains
    SERVICE_LOT ||--o{ ORDER : ordered_as

    GUEST_CONTACT ||--o{ ORDER : guest_order
    ORDER ||--o| MAGIC_LINK : read_only_link
    ORDER ||--o{ ORDER_CLAIM : has
    ORDER ||--o{ CHECKPOINT : tracks
    ORDER ||--o{ PAYMENT : payment_records
    ORDER ||--o{ REFUND : refund_records
    ORDER ||--o| CHAT_THREAD : has
    CHAT_THREAD ||--o{ CHAT_PARTICIPANT : has
    CHAT_THREAD ||--o{ CHAT_MESSAGE : has

    USER {
        int id PK
        string email
        string password_hash
        enum status
        enum staff_role
        datetime created_at
    }

    BOOSTER_PROFILE {
        int user_id PK, FK
        enum approval_status
        enum tier
        string discord_url
        datetime created_at
        datetime updated_at
    }

    ADMIN_NOTE {
        int id PK
        int target_user_id FK
        int author_admin_id FK
        text note
        datetime created_at
    }

    GAME {
        int id PK
        string name
        string slug
        bool is_active
        int sort_order
    }

    SERVICE_CATEGORY {
        int id PK
        int game_id FK
        string name
        string slug
        int parent_id FK
        bool is_active
        int sort_order
    }

    SERVICE_LOT {
        int id PK
        int category_id FK
        string name
        string slug
        text description
        bool is_active
        float base_price_eur
        datetime created_at
        datetime updated_at
    }

    SERVICE_OPTION {
        int id PK
        int lot_id FK
        string code
        string value_type
        json config_json
        bool is_required
        int sort_order
    }

    SERVICE_PAGE {
        int id PK
        int lot_id FK
        enum status
        string title
        json meta_json
        datetime published_at
    }

    SERVICE_PAGE_BLOCK {
        int id PK
        int page_id FK
        int position
        string type
        json payload_json
    }

    PROMOTION {
        int id PK
        enum scope_type
        int scope_id
        enum promo_type
        float value
        string tag
        datetime starts_at
        datetime ends_at
        bool is_enabled
    }

    GUEST_CONTACT {
        int id PK
        string channel
        string value
        datetime created_at
    }

    MAGIC_LINK {
        int id PK
        int order_id FK
        string token_hash
        string scope
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }

    ORDER {
        int id PK
        string public_number
        enum status
        enum execution_mode
        int customer_user_id FK
        int guest_contact_id FK
        int booster_user_id FK
        int service_lot_id FK
        json selected_options_json
        json price_snapshot_json
        text internal_note
        datetime paid_at
        int paid_by_admin_id FK
        datetime accepted_at
        datetime in_progress_at
        datetime done_at
        datetime closed_at
    }

    ORDER_CLAIM {
        int id PK
        int order_id FK
        int booster_user_id FK
        enum status
        int decided_by_admin_id FK
        datetime created_at
        datetime decided_at
    }

    CHECKPOINT {
        int id PK
        int order_id FK
        int created_by_user_id FK
        text message
        string attachment_url
        datetime created_at
    }

    PAYMENT {
        int id PK
        int order_id FK
        enum status
        datetime confirmed_at
        int confirmed_by_admin_id FK
        datetime created_at
    }

    REFUND {
        int id PK
        int order_id FK
        enum type
        float amount_eur
        text reason
        int decided_by_admin_id FK
        datetime created_at
    }

    CHAT_THREAD {
        int id PK
        int order_id FK
        datetime created_at
    }

    CHAT_PARTICIPANT {
        int id PK
        int thread_id FK
        int user_id FK
        string role_in_thread
        datetime joined_at
    }

    CHAT_MESSAGE {
        int id PK
        int thread_id FK
        int author_user_id FK
        text body
        string attachment_url
        datetime created_at
    }
```

## Разбиение по доменам

### Users and Access

```mermaid
erDiagram
    USER ||--o| BOOSTER_PROFILE : has
    USER ||--o{ ADMIN_NOTE : authors

    USER {
        int id PK
        string email
        string password_hash
        enum status
        enum staff_role
        datetime created_at
    }

    BOOSTER_PROFILE {
        int user_id PK, FK
        enum approval_status
        enum tier
        string discord_url
        datetime created_at
        datetime updated_at
    }

    ADMIN_NOTE {
        int id PK
        int target_user_id FK
        int author_admin_id FK
        text note
        datetime created_at
    }
```

### Catalog and Content

```mermaid
erDiagram
    GAME ||--o{ SERVICE_CATEGORY : contains
    SERVICE_CATEGORY ||--o{ SERVICE_CATEGORY : parent_of
    SERVICE_CATEGORY ||--o{ SERVICE_LOT : contains
    SERVICE_LOT ||--o{ SERVICE_OPTION : has
    SERVICE_LOT ||--o| SERVICE_PAGE : has
    SERVICE_PAGE ||--o{ SERVICE_PAGE_BLOCK : contains

    GAME {
        int id PK
        string name
        string slug
        bool is_active
        int sort_order
    }

    SERVICE_CATEGORY {
        int id PK
        int game_id FK
        string name
        string slug
        int parent_id FK
        bool is_active
        int sort_order
    }

    SERVICE_LOT {
        int id PK
        int category_id FK
        string name
        string slug
        text description
        bool is_active
        float base_price_eur
        datetime created_at
        datetime updated_at
    }

    SERVICE_OPTION {
        int id PK
        int lot_id FK
        string code
        string value_type
        json config_json
        bool is_required
        int sort_order
    }

    SERVICE_PAGE {
        int id PK
        int lot_id FK
        enum status
        string title
        json meta_json
        datetime published_at
    }

    SERVICE_PAGE_BLOCK {
        int id PK
        int page_id FK
        int position
        string type
        json payload_json
    }
```

### Orders and Fulfillment

```mermaid
erDiagram
    USER ||--o{ ORDER : creates
    USER ||--o{ ORDER : executes
    USER ||--o{ ORDER : marks_paid
    USER ||--o{ ORDER_CLAIM : claims
    USER ||--o{ ORDER_CLAIM : decides
    USER ||--o{ CHECKPOINT : writes
    USER ||--o{ PAYMENT : confirms
    USER ||--o{ REFUND : decides
    SERVICE_LOT ||--o{ ORDER : ordered_as
    GUEST_CONTACT ||--o{ ORDER : guest_order
    ORDER ||--o| MAGIC_LINK : read_only_link
    ORDER ||--o{ ORDER_CLAIM : has
    ORDER ||--o{ CHECKPOINT : tracks
    ORDER ||--o{ PAYMENT : payment_records
    ORDER ||--o{ REFUND : refund_records

    GUEST_CONTACT {
        int id PK
        string channel
        string value
        datetime created_at
    }

    MAGIC_LINK {
        int id PK
        int order_id FK
        string token_hash
        string scope
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }

    ORDER {
        int id PK
        string public_number
        enum status
        enum execution_mode
        int customer_user_id FK
        int guest_contact_id FK
        int booster_user_id FK
        int service_lot_id FK
        json selected_options_json
        json price_snapshot_json
        text internal_note
        datetime paid_at
        int paid_by_admin_id FK
        datetime accepted_at
        datetime in_progress_at
        datetime done_at
        datetime closed_at
    }

    ORDER_CLAIM {
        int id PK
        int order_id FK
        int booster_user_id FK
        enum status
        int decided_by_admin_id FK
        datetime created_at
        datetime decided_at
    }

    CHECKPOINT {
        int id PK
        int order_id FK
        int created_by_user_id FK
        text message
        string attachment_url
        datetime created_at
    }

    PAYMENT {
        int id PK
        int order_id FK
        enum status
        datetime confirmed_at
        int confirmed_by_admin_id FK
        datetime created_at
    }

    REFUND {
        int id PK
        int order_id FK
        enum type
        float amount_eur
        text reason
        int decided_by_admin_id FK
        datetime created_at
    }
```

### Chat and Messaging

```mermaid
erDiagram
    ORDER ||--o| CHAT_THREAD : has
    CHAT_THREAD ||--o{ CHAT_PARTICIPANT : has
    CHAT_THREAD ||--o{ CHAT_MESSAGE : has
    USER ||--o{ CHAT_PARTICIPANT : joins
    USER ||--o{ CHAT_MESSAGE : writes

    CHAT_THREAD {
        int id PK
        int order_id FK
        datetime created_at
    }

    CHAT_PARTICIPANT {
        int id PK
        int thread_id FK
        int user_id FK
        string role_in_thread
        datetime joined_at
    }

    CHAT_MESSAGE {
        int id PK
        int thread_id FK
        int author_user_id FK
        text body
        string attachment_url
        datetime created_at
    }
```

### Promotions

```mermaid
erDiagram
    PROMOTION {
        int id PK
        enum scope_type
        int scope_id
        enum promo_type
        float value
        string tag
        datetime starts_at
        datetime ends_at
        bool is_enabled
    }
```

## Что не активно сейчас

- `PricingRuleSet` — пока не активирован в текущем ORM (future-вариант)
- `PageBlockTypeSchema` — отключён
- `Dispute`, `OrderTimelineEvent`, notification-модели — пока не активированы в `models.py`
