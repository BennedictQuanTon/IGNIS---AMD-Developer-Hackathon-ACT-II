"""SQLite persistence for local workflow state; rows are JSON and mutations are revision guarded."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Conflict(RuntimeError):
    pass


class NotFound(KeyError):
    pass


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, revision INTEGER NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS packs(id TEXT PRIMARY KEY, run_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, run_id TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        return {"run_id": row["id"], "revision": row["version"], "status": row["status"], **json.loads(row["data"])}

    def create(self, run_id, data):
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?,0,'created',?)", (run_id, json.dumps(data)))
            db.execute("INSERT INTO events(run_id,revision,kind,data) VALUES (?,0,'created',?)", (run_id, json.dumps(data)))
        return self.get(run_id)

    def get(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        value = self.decode(row)
        if value is None:
            raise NotFound(run_id)
        return value

    def list(self):
        with self.connect() as db:
            return [self.decode(row) for row in db.execute("SELECT * FROM runs ORDER BY rowid DESC")]

    def mutate(self, run_id, expected_revision, kind, changes, status=None, before_commit=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            current = self.decode(row)
            if current is None:
                raise NotFound(run_id)
            if current["revision"] != expected_revision:
                raise Conflict(f"expected revision {expected_revision}; current revision is {current['revision']}")
            new_data = {k: v for k, v in current.items() if k not in {"run_id", "revision", "status"}}
            new_data.update(changes)
            next_status = status or current["status"]
            revision = expected_revision + 1
            if before_commit:
                before_commit(db, revision)
            db.execute("UPDATE runs SET version=?,status=?,data=? WHERE id=?", (revision, next_status, json.dumps(new_data), run_id))
            db.execute("INSERT INTO events(run_id,revision,kind,data) VALUES (?,?,?,?)", (run_id, revision, kind, json.dumps(changes)))
        return self.get(run_id)

    def history(self, run_id):
        self.get(run_id)
        with self.connect() as db:
            return [dict(row, data=json.loads(row["data"])) for row in db.execute("SELECT * FROM events WHERE run_id=? ORDER BY revision", (run_id,))]

    def report(self, report_id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM reports WHERE id=?", (report_id,)).fetchone()
        return json.loads(row["data"]) if row else None
