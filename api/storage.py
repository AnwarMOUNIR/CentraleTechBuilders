"""Local, bounded catalog retrieval and redacted debug history. Never executes model SQL."""
import json
import os
import re
import sqlite3
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
from api.privacy import redact

conversation_context = ContextVar('conversation_context', default=[])
_seeded = set()

@contextmanager
def connect():
    path = Path(os.getenv('ORDER_DB_PATH', str(Path(__file__).resolve().parents[1] / 'data/catalog.db')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS items_available (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL,
        restaurant_id TEXT NOT NULL, restaurant_name TEXT NOT NULL, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS conversation_events (
        id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL, speaker TEXT NOT NULL,
        text TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE INDEX IF NOT EXISTS conversation_lookup ON conversation_events(conversation_id, id);
      CREATE VIRTUAL TABLE IF NOT EXISTS item_search USING fts5(id UNINDEXED, name);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()

def search_catalog(text, catalog, basket=(), limit=24):
    terms = list(dict.fromkeys(re.findall(r'[a-z0-9]+', text.lower())))[:32]
    aliases = {'bastilla':'pastilla','pastila':'pastilla','pastela':'pastilla','bisteya':'pastilla'}
    terms = [aliases.get(t, t) for t in terms if len(t) > 2]
    terms += [t[:-1] for t in terms if t.endswith('s') and len(t) > 3]
    terms = [t for t in terms if t not in {'the','and','want','please','would','like','give','some','have','order','that','this','with','without'}]
    with connect() as db:
        key = (db.execute('PRAGMA database_list').fetchone()['file'], id(catalog))
        if key not in _seeded:
            db.execute('DELETE FROM items_available')
            db.execute('DELETE FROM item_search')
            db.executemany('INSERT INTO items_available VALUES (?,?,?,?,?,?)', [
                (p['id'],p['name'],p['base_price_mad'],r['id'],r['name'],json.dumps(p))
                for r in catalog for p in r['menu']])
            db.execute('INSERT INTO item_search SELECT id,name FROM items_available')
            db.commit()
            _seeded.add(key)
        clauses = ['lower(name) LIKE ?' for _ in terms]
        parameters = ['%' + t + '%' for t in terms]
        ids = [b['product_id'] for b in basket]
        if ids:
            clauses.append('id IN (' + ','.join('?' for _ in ids) + ')')
            parameters.extend(ids)
        # FTS narrows large catalogs with a bounded, escaped token expression.
        # LIKE remains a fallback for partial names that are not token prefixes.
        if terms:
            expression = ' OR '.join('"' + t + '"*' for t in terms)
            matched = db.execute('SELECT id FROM item_search WHERE item_search MATCH ? ORDER BY rank LIMIT ?',
                                 (expression, limit)).fetchall()
            if matched:
                clauses = ['id IN (' + ','.join('?' for _ in matched) + ')']
                parameters = [r['id'] for r in matched]
        query = 'SELECT * FROM items_available'
        if clauses: query += ' WHERE ' + ' OR '.join(clauses)
        query += ' ORDER BY price, id LIMIT ?'
        rows = db.execute(query, [*parameters, limit]).fetchall()
    selected = {r['id'] for r in rows} | set(ids)
    return [{**r, 'menu':[p for p in r['menu'] if p['id'] in selected]} for r in catalog
            if any(p['id'] in selected for p in r['menu'])]

def log_event(conversation_id, speaker, text, details=None):
    if not conversation_id: return
    with connect() as db:
        db.execute("DELETE FROM conversation_events WHERE created_at < datetime('now','-7 days')")
        db.execute('INSERT INTO conversation_events(conversation_id,speaker,text,details) VALUES (?,?,?,?)',
                   (conversation_id, speaker, redact(text)[:4000], json.dumps(details or {})))

def history(conversation_id, limit=100):
    if not conversation_id: return []
    with connect() as db:
        rows = db.execute('SELECT * FROM conversation_events WHERE conversation_id=? ORDER BY id DESC LIMIT ?',
                          (conversation_id, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]

def conversations():
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT conversation_id, MAX(created_at) AS updated_at, COUNT(*) AS events FROM conversation_events GROUP BY conversation_id ORDER BY updated_at DESC LIMIT 100')]
