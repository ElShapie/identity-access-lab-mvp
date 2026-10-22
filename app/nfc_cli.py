"""Registra o retira tarjetas NFC de la lista blanca local del laboratorio.

Uso desde el contenedor de la app:

    docker compose exec app python -m app.nfc_cli --uid 0FC728C9 --user admin@example.test --label "Tarjeta del administrador"
    docker compose exec app python -m app.nfc_cli --uid 0FC728C9 --remove
"""
import argparse
import os
import sys

from app.store import Store

parser = argparse.ArgumentParser(description="Registrar o retirar una tarjeta NFC de acceso")
parser.add_argument("--uid", required=True, help="UID de la tarjeta en hexadecimal, con o sin separadores")
parser.add_argument("--user", default="admin@example.test", help="Correo del usuario local al que se asigna la tarjeta")
parser.add_argument("--label", default="", help="Etiqueta descriptiva de la tarjeta")
parser.add_argument("--remove", action="store_true", help="Retira la tarjeta en lugar de registrarla")
args = parser.parse_args()

store = Store(os.environ.get("APP_DB", "/srv/data/lab.sqlite"))

if args.remove:
    removed = store.remove_card(args.uid)
    print("Tarjeta retirada" if removed else "La tarjeta no estaba registrada")
    sys.exit(0 if removed else 1)

try:
    card = store.register_card(args.uid, args.user, args.label)
except ValueError as error:
    sys.exit(str(error))

print(f"Tarjeta registrada: {card['uid']} -> {card['username']} ({card['label'] or 'sin etiqueta'})")
print("Ahora pasa la tarjeta por el lector: la app abrirá sesión con ese usuario.")
