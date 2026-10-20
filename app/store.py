import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PERMISSIONS = {
    "admin": {"consulta", "mantenimiento", "admin", "registros"},
    "mantenimiento": {"consulta", "mantenimiento"},
    "auditor": {"consulta", "registros"},
    "consulta": {"consulta"},
    "sin_acceso": set(),
}
ROLES = set(PERMISSIONS)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, oidc_sub TEXT UNIQUE)")
            db.execute("CREATE TABLE IF NOT EXISTS events (time TEXT NOT NULL, user TEXT NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL)")

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
    def resource(row):
        return json.loads(row["payload"]) if row else None

    def get(self, user_id):
        with self.connect() as db:
            return self.resource(db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def by_name(self, username):
        with self.connect() as db:
            return self.resource(db.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone())

    def all(self):
        with self.connect() as db:
            return [self.resource(row) for row in db.execute("SELECT * FROM users ORDER BY username")]

    def save(self, payload, user_id=None):
        if not isinstance(payload, dict):
            raise ValueError("El recurso debe ser un objeto JSON")
        previous = self.get(user_id) if user_id else None
        data = dict(previous or {})
        data.update(payload)
        username = str(data.get("userName", "")).strip().lower()
        if "@" not in username or username.startswith("@") or username.endswith("@"):
            raise ValueError("userName debe ser un correo")
        role = str(data.get("title", "sin_acceso"))
        if role not in ROLES:
            raise ValueError("title debe ser un rol conocido")
        active = data.get("active", True)
        if isinstance(active, str) and active.lower() in ("true", "false"):
            active = active.lower() == "true"
        if not isinstance(active, bool):
            raise ValueError("active debe ser true o false")
        data.update({"userName": username, "title": role, "active": active, "id": user_id or str(uuid.uuid4())})
        data.setdefault("schemas", ["urn:ietf:params:scim:schemas:core:2.0:User"])
        data["meta"] = {"resourceType": "User", "lastModified": utc_now()}
        with self.connect() as db:
            if previous:
                db.execute("UPDATE users SET username=?,payload=? WHERE id=?", (username, json.dumps(data), user_id))
            else:
                db.execute("INSERT INTO users(id,username,payload) VALUES(?,?,?)", (data["id"], username, json.dumps(data)))
        self.event(data["id"], "SCIM_CREATE" if previous is None else "SCIM_UPDATE", "OK")
        return data

    def deactivate(self, user_id):
        previous = self.get(user_id)
        if not previous:
            return False
        self.save({"active": False}, user_id)
        self.event(user_id, "SCIM_DEACTIVATE", "OK")
        return True

    def bind_identity(self, user_id, subject):
        with self.connect() as db:
            row = db.execute("SELECT oidc_sub FROM users WHERE id=?", (user_id,)).fetchone()
            if row is None or (row["oidc_sub"] and row["oidc_sub"] != subject):
                return False
            try:
                db.execute("UPDATE users SET oidc_sub=? WHERE id=?", (subject, user_id))
            except sqlite3.IntegrityError:
                return False
        return True

    def permitted(self, user_id, action):
        user = self.get(user_id)
        return bool(user and user.get("active") is True and action in PERMISSIONS.get(user.get("title"), set()))

    def event(self, user, action, result):
        with self.connect() as db:
            db.execute("INSERT INTO events VALUES(?,?,?,?)", (utc_now(), user, action, result))
            db.execute("DELETE FROM events WHERE rowid NOT IN (SELECT rowid FROM events ORDER BY rowid DESC LIMIT 500)")

    def events(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY rowid DESC LIMIT 100")]
