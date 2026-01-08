import sqlite3
import json
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(BASE, 'db.sqlite3')
if not os.path.exists(DB):
    print('No db.sqlite3 found at', DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables in DB:', tables)

# Try common payment table names
candidates = [t for t in tables if 'payment' in t.lower()]
if not candidates:
    print('No payment-like table found.')
    raise SystemExit(0)

table = candidates[0]
print('Using table:', table)

# Try to get last row ordered by created_at if present, else last row by ROWID
cols = [c[1] for c in cur.execute(f"PRAGMA table_info('{table}')").fetchall()]
print('Columns:', cols)

# Prefer created_at or id
order_col = 'created_at' if 'created_at' in cols else 'rowid'
try:
    row = cur.execute(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT 1").fetchone()
except Exception as e:
    print('Query failed:', e)
    row = cur.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()

if not row:
    print('No rows in', table)
    raise SystemExit(0)

# Map columns to values
schema = cur.execute(f"PRAGMA table_info('{table}')").fetchall()
col_names = [c[1] for c in schema]
record = dict(zip(col_names, row[:len(col_names)]))

print('Latest payment record:')
for k,v in record.items():
    if k.lower() in ('paynow_response','response','payload'):
        print(f'{k}:')
        try:
            print(json.dumps(json.loads(v), indent=2, ensure_ascii=False))
        except Exception:
            print(v[:1000])
    else:
        print(f'{k}: {v}')

conn.close()
