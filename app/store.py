import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


def normalize_uid(value):
    """Normaliza un UID de tarjeta a hexadecimal mayúsculo sin separadores."""
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"[\s:\-_]", "", value).upper()
    if not cleaned or not re.fullmatch(r"[0-9A-F]+", cleaned) or len(cleaned) % 2:
        return ""
    return cleaned


def uid_variants(value):
    """Devuelve el UID normalizado y su orden inverso.

    Los lectores contactless entregan el UID en orden inverso (LSB primero) según
    el estándar ISO 14443-3, mientras que las herramientas suelen mostrarlo en
    orden natural. Aceptar ambos evita registrar dos veces la misma tarjeta.
    """
    cleaned = normalize_uid(value)
    if not cleaned:
        return []
    pairs = [cleaned[index:index + 2] for index in range(0, len(cleaned), 2)]
    reversed_uid = "".join(reversed(pairs))
    return [cleaned] if reversed_uid == cleaned else [cleaned, reversed_uid]


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, oidc_sub TEXT UNIQUE)")
            db.execute("CREATE TABLE IF NOT EXISTS events (time TEXT NOT NULL, user TEXT NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS nfc_cards (uid TEXT PRIMARY KEY, username TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS nfc_taps (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, username TEXT NOT NULL, source TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)")

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

    # --- Credenciales NFC (badge de acceso) ---

    def register_card(self, uid, username, label=""):
        normalized = normalize_uid(uid)
        if not normalized:
            raise ValueError("UID de tarjeta inválido")
        username = str(username).strip().lower()
        if "@" not in username:
            raise ValueError("El usuario del badge debe ser un correo")
        with self.connect() as db:
            db.execute(
                "INSERT INTO nfc_cards(uid,username,label,created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(uid) DO UPDATE SET username=excluded.username,label=excluded.label",
                (normalized, username, str(label or ""), utc_now()),
            )
        self.event("nfc:" + normalized, "NFC_CARD_REGISTER", "OK")
        return self.card(normalized)

    def card(self, uid):
        normalized = normalize_uid(uid)
        if not normalized:
            return None
        with self.connect() as db:
            for variant in uid_variants(normalized):
                row = db.execute("SELECT * FROM nfc_cards WHERE uid=?", (variant,)).fetchone()
                if row:
                    return dict(row)
        return None

    def cards(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM nfc_cards ORDER BY created_at, uid")]

    def remove_card(self, uid):
        normalized = normalize_uid(uid)
        if not normalized:
            return False
        with self.connect() as db:
            removed = db.execute("DELETE FROM nfc_cards WHERE uid=?", (normalized,)).rowcount > 0
        if removed:
            self.event("nfc:" + normalized, "NFC_CARD_REMOVE", "OK")
        return removed

    def record_tap(self, uid, username, source=""):
        """Deja un toque pendiente para que el navegador lo consuma al iniciar sesión."""
        with self.connect() as db:
            db.execute(
                "INSERT INTO nfc_taps(uid,username,source,created_at,consumed) VALUES(?,?,?,?,0)",
                (str(uid), str(username), str(source or ""), utc_now()),
            )
        return True

    def clear_taps(self):
        """Descarta los toques pendientes.

        Se usa al cerrar sesion: si no, un toque leido antes del cierre se quedaria
        guardado y la pantalla de acceso lo consumiria al volver a arrancar el polling,
        reabriendo la sesion sin que el usuario vuelva a pasar la tarjeta.
        """
        with self.connect() as db:
            removed = db.execute("DELETE FROM nfc_taps WHERE consumed=0").rowcount
        return removed

    def claim_tap(self, ttl_seconds=15):
        """Reserva el toque más antiguo dentro de la ventana TTL; lo consume una sola vez."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=int(ttl_seconds))).isoformat()
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM nfc_taps WHERE consumed=0 AND created_at>=? ORDER BY id LIMIT 1",
                (cutoff,),
            ).fetchone()
            if row is None:
                return None
            reserved = db.execute("UPDATE nfc_taps SET consumed=1 WHERE id=? AND consumed=0", (row["id"],)).rowcount
            if not reserved:
                return None
            tap = db.execute("SELECT * FROM nfc_taps WHERE id=?", (row["id"],)).fetchone()
            db.execute("DELETE FROM nfc_taps WHERE created_at<?", (cutoff,))
            return dict(tap) if tap else None
