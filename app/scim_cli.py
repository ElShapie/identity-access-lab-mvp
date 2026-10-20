"""Cliente interno para repetir tareas de prueba sin exponer SCIM_TOKEN en la terminal."""
import argparse
import os
import sys

import requests

parser = argparse.ArgumentParser(description="Cambiar rol o estado de una identidad de demostración vía SCIM")
parser.add_argument("email")
parser.add_argument("--role", choices=("admin", "mantenimiento", "auditor", "consulta", "sin_acceso"))
parser.add_argument("--active", choices=("true", "false"))
args = parser.parse_args()
if args.role is None and args.active is None:
    parser.error("indica --role o --active")

base = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
headers = {"Authorization": "Bearer " + os.environ["SCIM_TOKEN"], "Content-Type": "application/scim+json"}
response = requests.get(base + "/scim/v2/Users", params={"filter": f'userName eq "{args.email}"'}, headers=headers, timeout=10)
response.raise_for_status()
resources = response.json().get("Resources", [])
if not resources:
    sys.exit("No se encontró el usuario; revisa el correo y que la app esté arriba.")
user_id = resources[0]["id"]
operations = []
if args.role is not None:
    operations.append({"op": "replace", "path": "title", "value": args.role})
if args.active is not None:
    operations.append({"op": "replace", "path": "active", "value": args.active == "true"})
response = requests.patch(base + "/scim/v2/Users/" + user_id, json={"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": operations}, headers=headers, timeout=10)
if not response.ok:
    sys.exit(f"SCIM devolvió HTTP {response.status_code}: {response.text}")
updated = response.json()
print(f"Actualizado: {updated['userName']} | rol={updated['title']} | active={updated['active']}")
