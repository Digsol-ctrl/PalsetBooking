import sqlite3
import json
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(BASE, 'db.sqlite3')
if not os.path.exists(DB):
    print('No db.sqlite3 found at', DB)
    sys.exit(1)

ref = None
if len(sys.argv) > 1:
    ref = sys.argv[1]
else:
    ref = input('Enter paynow reference to find: ').strip()

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Find candidate tables that look like a Payment table
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables in DB:', tables)

candidates = [t for t in tables if 'payment' in t.lower()]
if not candidates:
    print('No payment-like table found.')
    sys.exit(0)

for table in candidates:
    print('\nSearching table:', table)
    # Look for explicit paynow_reference column
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info('{table}')").fetchall()]
    print('Columns:', cols)
    rows = cur.execute(f"SELECT * FROM {table}").fetchall()
    for row in rows:
        rowd = dict(zip(cols, row[:len(cols)]))
        pr = None
        if 'paynow_reference' in rowd:
            pr = rowd.get('paynow_reference')
        elif 'paynowreference' in rowd:
            pr = rowd.get('paynowreference')
        if pr and str(pr) == ref:
            print('MATCH by paynow_reference:')
            print(json.dumps(rowd, indent=2, default=str))
        # check paynow_response JSON
        for k in ('paynow_response', 'response', 'payload'):
            if k in rowd and rowd[k]:
                try:
                    d = json.loads(rowd[k]) if isinstance(rowd[k], str) else rowd[k]
                    # search within json for reference
                    def search(obj):
                        if isinstance(obj, dict):
                            for v in obj.values():
                                if isinstance(v, (dict, list, tuple)):
                                    if search(v):
                                        return True
                                else:
                                    if str(v) == ref:
                                        return True
                            return False
                        elif isinstance(obj, (list, tuple)):
                            for v in obj:
                                if search(v):
                                    return True
                            return False
                        else:
                            return str(obj) == ref
                    if search(d):
                        print('MATCH inside', k)
                        print(json.dumps(d, indent=2, default=str))
                except Exception:
                    # not json
                    if isinstance(rowd[k], str) and ref in rowd[k]:
                        print('MATCH substring inside', k)
                        print(rowd[k][:1000])

conn.close()
print('\nDone')