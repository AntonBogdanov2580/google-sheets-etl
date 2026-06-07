"""Просмотр содержимого базы данных data.db в виде таблицы."""
import sqlite3
import pandas as pd

conn = sqlite3.connect('data.db')
df = pd.read_sql("SELECT * FROM sheets_data", conn)
conn.close()

print(f"\n{'='*60}")
print(f"  БД: data.db  |  Таблица: sheets_data  |  Строк: {len(df)}")
print(f"{'='*60}\n")

# Настройки отображения pandas
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 30)

print(df.to_string(index=True))

print(f"\n{'─'*60}")
print("СТАТИСТИКА ПО ДАТАМ:")
stats = (
    df["Дата создания заказа"]
    .str[:10]
    .fillna("(пусто)")
    .replace("", "(пусто)")
    .value_counts()
    .sort_index()
)
for date, count in stats.items():
    marker = " ← перезапись" if date == "2026-03-01" else ""
    print(f"  {date:<15}  {count} строк{marker}")
print(f"{'='*60}\n")
