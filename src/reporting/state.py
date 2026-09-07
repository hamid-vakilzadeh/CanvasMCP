"""Account-isolated, private SQLite state. Created only by opt-in local workflows."""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from reporting.common import digest, now


def state_root() -> Path:
    configured = os.getenv("CANVAS_MCP_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "CanvasMCP"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/CanvasMCP"
    return Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "canvas-mcp"


class StateConflict(ValueError):
    """A second client changed a record; inspect before retrying."""


class Store:
    def __init__(self, canvas_url: str, user_id: str, root: Path | None = None):
        self.account = digest([canvas_url.rstrip("/"), str(user_id)])
        root = (root or state_root()).resolve()
        if any((parent / '.git').exists() for parent in (root, *root.parents)):
            raise ValueError('Private Canvas state must be outside a Git repository')
        self.directory = root / self.account
        if self.directory.is_symlink():
            raise ValueError('Private account state must not be a symbolic link')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        self.path = self.directory / "state.sqlite3"
        if self.path.is_symlink():
            raise ValueError("Private state must not be a symbolic link")
        # Reserve the file with private permissions before SQLite opens it.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(kind, id)
                );
                CREATE INDEX IF NOT EXISTS records_kind ON records(kind, created_at, id);
                CREATE TABLE IF NOT EXISTS leases (
                    name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA secure_delete=ON")
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def unpack(row) -> dict[str, Any]:
        return {**json.loads(row["payload"]), "id": row["id"], "revision": row["revision"],
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def create(self, kind: str, payload: dict, *, key: str | None = None) -> dict:
        key, timestamp = key or secrets.token_hex(16), now()
        with self.connect() as db:
            try:
                db.execute("INSERT INTO records(id,kind,payload,created_at,updated_at) VALUES(?,?,?,?,?)",
                           (key, kind, json.dumps(payload, ensure_ascii=False), timestamp, timestamp))
            except sqlite3.IntegrityError as exc:
                raise StateConflict("This local record already exists; reload it") from exc
        return self.get(kind, key)

    def get(self, kind: str, key: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is None:
            raise ValueError("Local record not found for this Canvas account")
        return self.unpack(row)

    def update(self, kind: str, key: str, changes: dict, *, revision: int | None = None) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
            if row is None:
                db.rollback()
                raise ValueError("Local record not found for this Canvas account")
            if revision is not None and revision != row["revision"]:
                db.rollback()
                raise StateConflict("Local record changed; reload it before saving")
            payload = {**json.loads(row["payload"]), **changes}
            db.execute("UPDATE records SET payload=?,revision=revision+1,updated_at=? WHERE kind=? AND id=?",
                       (json.dumps(payload, ensure_ascii=False), now(), kind, key))
            db.commit()
        return self.get(kind, key)

    def delete(self, kind: str, key: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, key))

    def all(self, kind: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM records WHERE kind=? ORDER BY created_at,id", (kind,)).fetchall()
        return [self.unpack(row) for row in rows]

    def page(self, kind: str, *, status: str | None = None, cursor: str | None = None,
             limit: int = 25, match: dict | None = None) -> dict:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            offset = int(cursor or "0")
            if offset < 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Invalid local pagination cursor") from exc
        rows = [r for r in self.all(kind) if (status is None or r.get("status") == status)
                and all(r.get(k) == v for k, v in (match or {}).items())]
        return {"items": rows[offset:offset + limit], "total": len(rows),
                "next_cursor": str(offset + limit) if offset + limit < len(rows) else None}

    def acquire(self, name: str, owner: str, *, seconds: float = 90) -> bool:
        timestamp = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM leases WHERE name=?", (name,)).fetchone()
            if row and row["expires"] > timestamp and row["owner"] != owner:
                db.rollback()
                return False
            db.execute("INSERT OR REPLACE INTO leases VALUES(?,?,?)", (name, owner, timestamp + seconds))
            db.commit()
        return True

    def release(self, name: str, owner: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM leases WHERE name=? AND owner=?", (name, owner))

    def lease_status(self, name: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT expires FROM leases WHERE name=?", (name,)).fetchone()
        return {"running": bool(row and row["expires"] > time.time()),
                "lease_expires_at": row["expires"] if row else None}

    def delete_job(self, job_id: str) -> None:
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Invalid report identifier')
        self.get("report", job_id)
        for kind in ("evidence", "analysis"):
            for record in self.all(kind):
                if record.get("job_id") == job_id:
                    self.delete(kind, record["id"])
        self.delete("report", job_id)
        for suffix in (".html", ".json"):
            (self.directory / f"report-{job_id}{suffix}").unlink(missing_ok=True)

    def prune(self, *, days: int = 30) -> dict:
        from datetime import datetime
        cutoff = time.time() - days * 86400
        removed = 0
        for item in self.all("activity"):
            if item.get("status") in {"posted", "ignored", "dismissed"} and datetime.fromisoformat(item["updated_at"]).timestamp() < cutoff:
                if item.get("message") or item.get("draft_reply"):
                    self.update("activity", item["id"], {"message": None, "draft_reply": None, "reason": None, "text_purged": True})
        expired_jobs: set[str] = set()
        for item in self.all("evidence"):
            if datetime.fromisoformat(item["created_at"]).timestamp() < cutoff:
                expired_jobs.add(item["job_id"])
                self.delete("evidence", item["id"])
                removed += 1
        for job_id in expired_jobs:
            job = self.get("report", job_id)
            self.update("report", job_id, {"evidence_expired": True,
                        "status": job["status"] if job["status"] in {"completed", "completed_with_gaps", "incomplete"} else "needs_refresh",
                        "snapshot": None})
        return {"expired_evidence": removed}
