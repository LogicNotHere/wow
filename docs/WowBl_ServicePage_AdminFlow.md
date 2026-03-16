# WowBl — Создание описания лота админом (`ServicePage`)

Этот документ описывает только **контентную часть лота**:
- описание услуги
- FAQ
- таблицы
- текстовые блоки

Это **не** правая коммерческая часть лота (`Self-play`, `Piloted`, `runs_count`, `difficulty`, цена и т.д.).

Для понимания:
- `ServiceLot` = сам продукт/услуга
- `ServicePage` = страница описания этого продукта
- `ServicePageBlock` = отдельный блок внутри страницы

---

## 1. Общая идея

У одного лота есть две независимые части:

1. Контентная витрина:
- описание
- FAQ
- таблицы
- инфоблоки

2. Коммерческая конфигурация:
- execution mode
- runs count
- difficulty
- price calculation
- promotions

`ServicePage` отвечает только за **первую часть**.

---

## 2. Начало сценария

Админ заходит в админку и нажимает `Создать лот`.

Сначала он заполняет базовые поля лота:
- `name`
- `category`
- `booster_category`
- `is_active`
- базовые настройки продукта

После этого создаётся `ServiceLot`.

Пример:

```text
ServiceLot
id = 15
name = "Mythic+ Boost"
category_id = 42
booster_category = "mythic_plus"
is_active = false
```

На этом этапе лот уже существует, но его страница описания ещё может быть пустой.

---

## 3. Переход во вкладку "Описание"

После сохранения базовых полей админ открывает вкладку:
- `Основное`
- `Опции`
- `Ценообразование`
- `Описание`

Во вкладке `Описание` система:
- либо находит существующую `ServicePage` для этого `ServiceLot`
- либо создаёт новую `ServicePage` в статусе `draft`

Пример:

```text
ServicePage
id = 90
lot_id = 15
status = "draft"
title = "Mythic+ Boost"
```

Обычно одна `ServicePage` соответствует одному `ServiceLot`.

---

## 4. Пустой конструктор страницы

Если описание ещё не заполнено, админ видит пустой конструктор:
- список блоков
- кнопку `Добавить блок`
- кнопку `Сохранить`
- кнопку `Предпросмотр`
- кнопку `Опубликовать`

Пока блоков нет.

Пример визуально:

```text
[ + Добавить блок ]

Страница пока пустая
```

---

## 5. Добавление блока

Админ нажимает `Добавить блок`.

Система предлагает выбрать тип блока.

Например:
- `text`
- `faq`
- `table`
- `list`

Тип блока нужен для двух вещей:
- backend понимает, как валидировать `payload`
- frontend понимает, как рендерить блок

Если админ выбирает `text`, создаётся новый `ServicePageBlock`.

Пример:

```text
ServicePageBlock
id = 501
page_id = 90
type = "text"
position = 1
payload_json = {}
```

На UI это обычно выглядит как открытая форма редактирования нового блока.

---

## 6. Заполнение блока `text`

Для блока `text` админ видит поля, например:
- `title`
- `body`
- `align`

Пример заполнения:
- `title`: `What is included in this boost`
- `body`: `You will get a professional Mythic+ completion with experienced players.`
- `align`: `left`

Итоговый `payload_json`:

```json
{
  "title": "What is included in this boost",
  "body": "You will get a professional Mythic+ completion with experienced players.",
  "align": "left"
}
```

Смысл:
- `type` хранит тип блока
- `payload_json` хранит его данные

---

## 7. Валидация блока

Перед сохранением backend валидирует `payload_json` в зависимости от `type`.

Например, для `text` проверяется:
- что `title` строка
- что `body` строка
- что `align` входит в допустимый набор значений

Если данные неправильные, блок не сохраняется.

Пример ошибки:

```text
Field "body" is required for block type "text"
```

Это важный принцип: backend не должен принимать произвольный JSON без проверки.

---

## 8. Добавление блока `faq`

Админ снова нажимает `Добавить блок` и выбирает `faq`.

Создаётся новый блок:

```text
ServicePageBlock
id = 502
page_id = 90
type = "faq"
position = 2
payload_json = {}
```

Форма для `faq` отличается от `text`.

Админ вводит список вопросов и ответов.

Пример:

```json
{
  "items": [
    {
      "question": "Is this safe?",
      "answer": "We use manual play only for self-play orders."
    },
    {
      "question": "How long does it take?",
      "answer": "Depends on the key level and current queue."
    }
  ]
}
```

---

## 9. Добавление блока `table`

Теперь админ хочет показать сравнительную таблицу.

Он добавляет блок `table`.

Пример `payload_json`:

```json
{
  "title": "Boost formats",
  "columns": ["Mode", "Description"],
  "rows": [
    ["Self-play", "You play on your character"],
    ["Piloted", "Booster plays on your account"]
  ]
}
```

После этого структура страницы может быть такой:

```text
1. text
2. faq
3. table
```

---

## 10. Изменение порядка блоков

Админ может менять порядок блоков:
- drag-and-drop
- кнопки `вверх/вниз`

Backend при этом просто обновляет `position`.

Было:

```text
1. text
2. faq
3. table
```

Стало:

```text
1. text
2. table
3. faq
```

Frontend всегда сортирует блоки по `position`.

---

## 11. Редактирование и удаление блока

Если блок надо поменять:
- админ открывает форму блока
- меняет `payload_json`
- backend валидирует и сохраняет

Если блок больше не нужен:
- админ нажимает `Удалить блок`
- блок удаляется из `ServicePageBlock`

Пример редактирования `text` блока:

Было:

```json
{
  "title": "What is included in this boost",
  "body": "You will get a professional Mythic+ completion..."
}
```

Стало:

```json
{
  "title": "What is included",
  "body": "You will get a timed or untimed Mythic+ completion depending on selected options."
}
```

---

## 12. Сохранение страницы как draft

Пока страница не готова, она остаётся в статусе:

```text
ServicePage.status = "draft"
```

Это значит:
- админ её видит и редактирует
- пользователь на сайте её не видит

Это позволяет не показывать незавершённый контент.

---

## 13. Предпросмотр

Админ нажимает `Предпросмотр`.

Backend или frontend собирает:
- `ServiceLot`
- `ServicePage`
- `ServicePageBlock[]`, отсортированные по `position`

Пример ответа для preview:

```json
{
  "lot": {
    "id": 15,
    "name": "Mythic+ Boost"
  },
  "page": {
    "id": 90,
    "status": "draft"
  },
  "blocks": [
    {
      "type": "text",
      "position": 1,
      "payload": {
        "title": "What is included",
        "body": "You will get a timed or untimed Mythic+ completion depending on selected options."
      }
    },
    {
      "type": "table",
      "position": 2,
      "payload": {
        "title": "Boost formats",
        "columns": ["Mode", "Description"],
        "rows": [
          ["Self-play", "You play on your character"],
          ["Piloted", "Booster plays on your account"]
        ]
      }
    },
    {
      "type": "faq",
      "position": 3,
      "payload": {
        "items": [
          {
            "question": "Is this safe?",
            "answer": "We use manual play only for self-play orders."
          }
        ]
      }
    }
  ]
}
```

Frontend рендерит блоки по `type`.

---

## 14. Публикация страницы

Когда админ закончил редактирование, он нажимает `Опубликовать`.

Backend:
- валидирует страницу
- валидирует все блоки
- меняет статус страницы

Пример:

```text
ServicePage.status = "published"
published_at = now()
```

После этого страница становится доступной на сайте.

---

## 15. Что видит пользователь

Когда пользователь открывает страницу лота:
- frontend запрашивает публичный endpoint
- backend отдаёт только `published` страницу
- backend отдаёт все блоки, отсортированные по `position`
- frontend рендерит их по `type`

То есть контент страницы формируется динамически без изменений кода фронта.

---

## 16. Что важно помнить

`ServicePage` и `ServicePageBlock` описывают только **левую контентную часть страницы**:
- описание
- FAQ
- таблицы
- инфоблоки

Правая часть страницы, где находятся:
- `Self-play`
- `Piloted`
- `runs_count`
- `difficulty`
- price preview
- кнопка покупки

Это уже другая часть домена:
- `ServiceLot`
- `ServiceOption`
- `PricingRuleSet`
- `Promotion`

---

## 17. Итог

Если упростить до одной фразы:

`ServiceLot` отвечает за то, **что продаётся**,
а `ServicePage` отвечает за то, **как это описано и показано на витрине**.

Если page builder действительно нужен, эта модель оправдана.
Если нет, описание можно упростить до нескольких обычных полей в `ServiceLot`.

