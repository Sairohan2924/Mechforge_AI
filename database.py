from __future__ import annotations
import hashlib, hmac, os, secrets, sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv('MECHFORGE_DB', 'mechforge.db'))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS projects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 component TEXT DEFAULT '',
 material TEXT DEFAULT 'Aluminium 6061',
 process TEXT DEFAULT 'AUTO SELECT',
 quantity INTEGER DEFAULT 1,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id, name), FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS analyses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 project_id INTEGER,
 name TEXT NOT NULL,
 payload TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(project_id) REFERENCES projects(id)
);
CREATE TABLE IF NOT EXISTS suppliers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 location TEXT DEFAULT '',
 processes TEXT DEFAULT '',
 machine_rate REAL DEFAULT 900,
 setup_cost REAL DEFAULT 1500,
 material_factor REAL DEFAULT 1.0,
 lead_days INTEGER DEFAULT 7,
 email TEXT DEFAULT '',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id, name), FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS quotes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 project_id INTEGER,
 supplier_id INTEGER,
 quantity INTEGER NOT NULL,
 unit_cost REAL NOT NULL,
 total_cost REAL NOT NULL,
 lead_days INTEGER NOT NULL,
 notes TEXT DEFAULT '',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);
CREATE TABLE IF NOT EXISTS chat_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 project_id INTEGER,
 role TEXT NOT NULL,
 content TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(project_id) REFERENCES projects(id)
);
'''

def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210_000)
    return f'pbkdf2_sha256$210000${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = stored.split('$')
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def create_user(name: str, email: str, password: str):
    with _connect() as conn:
        try:
            cur = conn.execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)', (name.strip(), email.strip().lower(), _hash_password(password)))
            conn.commit()
            return cur.lastrowid, None
        except sqlite3.IntegrityError:
            return None, 'An account with this email already exists.'


def authenticate(email: str, password: str):
    with _connect() as conn:
        row = conn.execute('SELECT * FROM users WHERE email=?', (email.strip().lower(),)).fetchone()
    if row and verify_password(password, row['password_hash']):
        return dict(row)
    return None


def ensure_demo_user():
    user = authenticate('demo@mechforge.ai', 'demo123')
    if user:
        return user
    uid, _ = create_user('MechForge Demo', 'demo@mechforge.ai', 'demo123')
    return authenticate('demo@mechforge.ai', 'demo123') if uid else None


def list_projects(user_id):
    with _connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC', (user_id,))]


def get_project(user_id, project_id):
    with _connect() as conn:
        r = conn.execute('SELECT * FROM projects WHERE user_id=? AND id=?', (user_id, project_id)).fetchone()
        return dict(r) if r else None


def upsert_project(user_id, name, component, material, process, quantity, project_id=None):
    with _connect() as conn:
        if project_id:
            conn.execute('UPDATE projects SET name=?,component=?,material=?,process=?,quantity=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?', (name,component,material,process,quantity,project_id,user_id))
            pid = project_id
        else:
            try:
                cur = conn.execute('INSERT INTO projects(user_id,name,component,material,process,quantity) VALUES(?,?,?,?,?,?)', (user_id,name,component,material,process,quantity))
                pid = cur.lastrowid
            except sqlite3.IntegrityError:
                r = conn.execute('SELECT id FROM projects WHERE user_id=? AND name=?', (user_id,name)).fetchone()
                pid = r['id'] if r else None
        conn.commit()
        return pid


def delete_project(user_id, project_id):
    with _connect() as conn:
        conn.execute('DELETE FROM analyses WHERE user_id=? AND project_id=?', (user_id, project_id))
        conn.execute('DELETE FROM quotes WHERE user_id=? AND project_id=?', (user_id, project_id))
        conn.execute('DELETE FROM chat_messages WHERE user_id=? AND project_id=?', (user_id, project_id))
        conn.execute('DELETE FROM projects WHERE user_id=? AND id=?', (user_id, project_id))
        conn.commit()


def save_analysis(user_id, project_id, name, payload):
    import json
    with _connect() as conn:
        cur = conn.execute('INSERT INTO analyses(user_id,project_id,name,payload) VALUES(?,?,?,?)', (user_id,project_id,name,json.dumps(payload, default=str)))
        conn.commit()
        return cur.lastrowid


def list_analyses(user_id, project_id=None):
    with _connect() as conn:
        q='SELECT * FROM analyses WHERE user_id=?'
        args=[user_id]
        if project_id:
            q+=' AND project_id=?'; args.append(project_id)
        q+=' ORDER BY created_at DESC'
        rows=[]
        import json
        for r in conn.execute(q,args):
            d=dict(r); d['payload']=json.loads(d['payload']); rows.append(d)
        return rows


def add_chat(user_id, project_id, role, content):
    with _connect() as conn:
        conn.execute('INSERT INTO chat_messages(user_id,project_id,role,content) VALUES(?,?,?,?)', (user_id,project_id,role,content))
        conn.commit()


def get_chat(user_id, project_id, limit=30):
    with _connect() as conn:
        rows=conn.execute('SELECT role,content,created_at FROM chat_messages WHERE user_id=? AND project_id=? ORDER BY id DESC LIMIT ?', (user_id,project_id,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]


def list_suppliers(user_id):
    with _connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM suppliers WHERE user_id=? ORDER BY name', (user_id,))]


def upsert_supplier(user_id, data, supplier_id=None):
    fields=(data['name'],data.get('location',''),data.get('processes',''),float(data.get('machine_rate',900)),float(data.get('setup_cost',1500)),float(data.get('material_factor',1.0)),int(data.get('lead_days',7)),data.get('email',''))
    with _connect() as conn:
        if supplier_id:
            conn.execute('UPDATE suppliers SET name=?,location=?,processes=?,machine_rate=?,setup_cost=?,material_factor=?,lead_days=?,email=? WHERE id=? AND user_id=?', (*fields,supplier_id,user_id))
            sid=supplier_id
        else:
            try:
                cur=conn.execute('INSERT INTO suppliers(user_id,name,location,processes,machine_rate,setup_cost,material_factor,lead_days,email) VALUES(?,?,?,?,?,?,?,?,?)', (user_id,*fields)); sid=cur.lastrowid
            except sqlite3.IntegrityError:
                r=conn.execute('SELECT id FROM suppliers WHERE user_id=? AND name=?',(user_id,data['name'])).fetchone(); sid=r['id'] if r else None
        conn.commit(); return sid


def save_quote(user_id, project_id, supplier_id, quantity, unit_cost, total_cost, lead_days, notes=''):
    with _connect() as conn:
        cur=conn.execute('INSERT INTO quotes(user_id,project_id,supplier_id,quantity,unit_cost,total_cost,lead_days,notes) VALUES(?,?,?,?,?,?,?,?)',(user_id,project_id,supplier_id,quantity,unit_cost,total_cost,lead_days,notes)); conn.commit(); return cur.lastrowid


def list_quotes(user_id, project_id=None):
    with _connect() as conn:
        q='''SELECT q.*, s.name supplier_name, p.name project_name FROM quotes q LEFT JOIN suppliers s ON q.supplier_id=s.id LEFT JOIN projects p ON q.project_id=p.id WHERE q.user_id=?'''; args=[user_id]
        if project_id: q+=' AND q.project_id=?'; args.append(project_id)
        q+=' ORDER BY q.created_at DESC'
        return [dict(r) for r in conn.execute(q,args)]
