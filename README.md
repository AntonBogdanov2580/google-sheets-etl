# Google Sheets → SQLite ETL

ETL-пайплайн на Python: извлекает данные из Google Таблицы через API,
трансформирует и загружает в базу данных. Запуск через CLI.

---

## Как работает приложение

```
Google Sheets API
      │
      │  OAuth 2.0 (авторизация один раз, затем токен кешируется)
      ▼
[1] EXTRACT — etl/google_sheets.py
      Читает все строки с листа "Тест"
      │
      ▼
[2] TRANSFORM — etl/transform.py
      • Добавляет колонку sheet_name = "Тест"
      • Очищает номер договора: "29389196/25 - Яндекс" → "29389196/25"
      • Удаляет колонку "Категория"
      • Добавляет inserted_at = дата и время вставки (UTC)
      │
      ▼
[3] LOAD — etl/database.py
      Загружает данные в базу данных (SQLite по умолчанию)
```

### Два режима загрузки

**Режим 1 — Полная загрузка (без флага `--date`)**

Используется при первом запуске. Все строки из таблицы вставляются в БД.

```
Google Sheets (17 строк) → INSERT все 17 строк → БД
```

**Режим 2 — Перезапись за конкретную дату (`--date YYYY-MM-DD`)**

Используется для обновления данных за определённую дату.
Допустим, данные за 01.03.2026 изменились в Google Таблице —
нужно обновить именно эти строки в БД, не затрагивая остальные.

```
Google Sheets (17 строк)
      │
      ├─ [DELETE] удаляем из БД строки, где дата = 2026-03-01  (3 строки)
      │
      └─ [INSERT] вставляем обратно только строки за 2026-03-01 (3 строки)
                  с новым значением inserted_at

Результат: в БД 17 строк, строки за 01.03.2026 — обновлены.
Остальные даты не тронуты.
```

---

## Структура таблицы в базе данных

| Колонка | Описание |
|---|---|
| `Номер заказа или отгрузки` | Номер заказа из таблицы |
| `Дата создания заказа` | Дата и время создания заказа |
| `Ваш SKU` | Артикул товара |
| `Ваша цена за шт., ₽` | Цена за единицу |
| `Номера договоров на размещение` | **Только номер** договора (без названия маркетплейса) |
| `sheet_name` | Название листа Google Таблицы (добавлено автоматически) |
| `inserted_at` | Дата и время загрузки строки в БД (UTC) |

> Колонка **«Категория»** не загружается в базу данных.

---

## Почему выбрана SQLite

**SQLite** — встроенная база данных Python, не требует установки сервера.

| Критерий | SQLite |
|---|---|
| Установка | Не нужна — входит в стандартную библиотеку Python |
| Сервер | Не нужен |
| Для тестового задания | Полностью достаточна |
| Переключение на другую БД | Одна строка в `--db-url` |

**При росте данных** (многократное увеличение объёма) достаточно сменить
строку подключения — код менять не нужно:

```bash
# PostgreSQL
--db-url "postgresql://user:pass@localhost:5432/mydb"

# ClickHouse
--db-url "clickhouse+native://user:pass@host:9000/default"
```

SQLAlchemy обеспечивает единый интерфейс для всех трёх баз данных.

---

## Требования

- Python >= 3.10
- Файл `credentials.json` (OAuth 2.0, см. раздел ниже)

---

## Установка

```bash
git clone <repository-url>
cd google-sheets-etl

python -m venv venv

# Windows:
venv\Scripts\pip install -r requirements.txt

# Linux/Mac:
source venv/bin/activate && pip install -r requirements.txt
```

---

## Настройка OAuth 2.0

1. Откройте https://console.cloud.google.com/ и создайте проект
2. **APIs & Services → Library** → включите:
   - Google Sheets API
   - Google Drive API
3. **APIs & Services → OAuth consent screen**
   - User Type: External
   - Заполните форму, добавьте свой email в раздел **Test users**
4. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Скачайте JSON → сохраните как `credentials.json` в папку проекта

При первом запуске откроется браузер для авторизации.
Токен сохраняется в `token.json` — повторная авторизация не нужна.

> ⚠️ Никогда не коммитьте `credentials.json` и `token.json` — они в `.gitignore`.

---

## Запуск через CLI

### Шаг 1 — Первоначальная загрузка всех данных

```bash
# Windows
venv\Scripts\python main.py

# Linux/Mac
python main.py
```

Все настройки (ID таблицы, название листа, БД) берутся из `config.py`.

### Шаг 2 — Перезаписать данные только за 01.03.2026

```bash
# Windows
venv\Scripts\python main.py --date 2026-03-01

# Linux/Mac
python main.py --date 2026-03-01
```

Что происходит:
1. Читаются все строки из Google Таблицы
2. Из БД **удаляются** строки, где `Дата создания заказа` = 2026-03-01
3. В БД **вставляются** только строки за 2026-03-01 с новым `inserted_at`
4. Строки за другие даты остаются без изменений

### Все параметры CLI

```
venv\Scripts\python main.py --help
```

| Параметр | Описание | По умолчанию |
|---|---|---|
| `--spreadsheet-id` | ID Google Таблицы | **обязательный** |
| `--sheet` | Название листа | `Тест` |
| `--date` | Дата для перезаписи (YYYY-MM-DD). Без этого флага — полная загрузка | не задана |
| `--db-url` | SQLAlchemy URL базы данных | `sqlite:///data.db` |
| `--table` | Название таблицы в БД | `sheets_data` |
| `--credentials` | Путь к `credentials.json` | `credentials.json` |
| `--token` | Путь к `token.json` | `token.json` |
| `--contract-col` | Колонка с номером договора | авто-определение |
| `--date-col` | Колонка с датой (для перезаписи) | авто-определение |
| `--header-row` | Номер строки с заголовками (0-индекс) | `0` |

### Использование с PostgreSQL

```bash
pip install psycopg2-binary

python main.py \
  --spreadsheet-id 1AXGsVD1Dp4YfuKdaSfT5SY0detbbDmmMBzJXsLG7-30 \
  --db-url "postgresql://user:password@localhost:5432/mydb"
```

### Использование с ClickHouse

```bash
pip install clickhouse-sqlalchemy clickhouse-driver

python main.py \
  --spreadsheet-id 1AXGsVD1Dp4YfuKdaSfT5SY0detbbDmmMBzJXsLG7-30 \
  --db-url "clickhouse+native://user:password@host:9000/default"
```

---

## Просмотр базы данных

```bash
# Через скрипт (терминал)
venv\Scripts\python view_db.py

# Через GUI — DB Browser for SQLite (бесплатно)
# https://sqlitebrowser.org/dl/
# Открыть файл data.db → вкладка "Browse Data" → таблица sheets_data
```

---

## Тесты

```bash
venv\Scripts\python -m pytest tests/ -v
```

---

## Структура проекта

```
google-sheets-etl/
├── etl/
│   ├── __init__.py
│   ├── google_sheets.py   # OAuth 2.0 + чтение из Google Sheets API
│   ├── transform.py       # Трансформация: номер договора, фильтрация колонок
│   └── database.py        # SQLAlchemy: создание таблицы, DELETE + INSERT
├── tests/
│   ├── conftest.py
│   └── test_transform.py  # Unit-тесты трансформации
├── main.py                # CLI (click)
├── view_db.py             # Просмотр содержимого БД в терминале
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Зависимости

```
google-auth-oauthlib   # OAuth 2.0 авторизация
google-api-python-client # Google Sheets API
pandas                 # Обработка данных
click                  # CLI интерфейс
sqlalchemy             # ORM и работа с БД
```
