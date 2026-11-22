"""Prototip kayıtları yalnız bu bilgisayardaki SQLite dosyasında saklanır."""
from pathlib import Path
from contextlib import contextmanager
import json
import sqlite3
import time

class LocalStore:
    def __init__(self, path, upgrade=None):
        self.path = Path(path)
        self.upgrade = upgrade
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS learners (id TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL)')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create(self, state):
        with self.connect() as connection:
            connection.execute('INSERT INTO learners VALUES (?, ?, ?)',
                               (state['id'], json.dumps(state, ensure_ascii=False), time.time()))

    def get(self, learner_id):
        if self.upgrade:
            return self.change(learner_id, lambda state: None)
        with self.connect() as connection:
            row = connection.execute('SELECT state FROM learners WHERE id=?', (learner_id,)).fetchone()
        if not row:
            raise KeyError('Öğrenci kaydı bulunamadı.')
        return json.loads(row[0])

    def change(self, learner_id, action):
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT state FROM learners WHERE id=?', (learner_id,)).fetchone()
            if not row:
                raise KeyError('Öğrenci kaydı bulunamadı.')
            state = json.loads(row[0])
            if self.upgrade:
                self.upgrade(state)
            action(state)
            serialized = json.dumps(state, ensure_ascii=False)
            if serialized != row[0]:
                connection.execute('UPDATE learners SET state=?, updated=? WHERE id=?',
                                   (serialized, time.time(), learner_id))
        return state

    def listing(self):
        with self.connect() as connection:
            rows = connection.execute('SELECT state FROM learners ORDER BY updated DESC LIMIT 30').fetchall()
        states = [json.loads(row[0]) for row in rows]
        return [{'id': s['id'], 'name': s['name'], 'answers': len(s['attempts'])} for s in states]
