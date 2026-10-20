"""Crea usuarios locales de demostración si la base está vacía."""
import os
from app.store import Store

store = Store(os.environ.get("APP_DB", "/srv/data/lab.sqlite"))
for email, role in (
    ("ingeniero@example.test", "mantenimiento"),
    ("auditor@example.test", "auditor"),
    ("admin@example.test", "admin"),
):
    if not store.by_name(email):
        store.save({"userName": email, "title": role, "active": True})
