"""Crea usuarios locales de demostración si faltan y actualiza su perfil de área."""
import os
from app.store import Store

store = Store(os.environ.get("APP_DB", "/srv/data/lab.sqlite"))
DEMO_USERS = (
    ("ingeniero@example.test", "mantenimiento", "Ingeniero de laboratorio", "TI"),
    ("auditor@example.test", "auditor", "Auditor de laboratorio", "SOC / Auditoría"),
    ("admin@example.test", "admin", "Administrador de laboratorio", "IAM"),
    ("rrhh@example.test", "consulta", "Encargado de RRHH", "RRHH"),
    ("ti@example.test", "mantenimiento", "Encargado de TI", "TI"),
    ("iam@example.test", "admin", "Encargado de IAM", "IAM"),
    ("soc-auditoria@example.test", "auditor", "Encargado de SOC / Auditoría", "SOC / Auditoría"),
    ("seguridad-fisica@example.test", "consulta", "Encargado de Seguridad Física", "Seguridad Física"),
)

for email, role, display_name, department in DEMO_USERS:
    profile = {
        "userName": email,
        "title": role,
        "active": True,
        "displayName": display_name,
        "department": department,
    }
    current = store.by_name(email)
    if current is None:
        store.save(profile)
    elif any(current.get(key) != value for key, value in profile.items() if key != "userName"):
        store.save(profile, current["id"])
