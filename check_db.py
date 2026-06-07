# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data.db')

cols = [r[1] for r in conn.execute('PRAGMA table_info(sheets_data)').fetchall()]
print('COLUMNS:')
for c in cols:
    print(f'  - {c}')

print()
print('DATA (contract col + date col + sheet_name):')
rows = conn.execute('SELECT * FROM sheets_data').fetchall()
print(f'Total: {len(rows)} rows')
print()
for r in rows:
    print(dict(zip(cols, r)))

conn.close()
