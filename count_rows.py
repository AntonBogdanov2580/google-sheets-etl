import sqlite3
conn = sqlite3.connect('data.db')
total = conn.execute("SELECT COUNT(*) FROM sheets_data").fetchone()[0]
rows_march1 = conn.execute("SELECT COUNT(*) FROM sheets_data WHERE [Дата создания заказа] LIKE '2026-03-01%'").fetchone()[0]
print(f"Total rows in DB: {total}")
print(f"Rows for 2026-03-01: {rows_march1}")
conn.close()
