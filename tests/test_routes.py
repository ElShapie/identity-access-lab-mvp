import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TEST_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("APP_SECRET", "unit-test-secret-that-is-long-enough-123456")
os.environ.setdefault("SCIM_TOKEN", "unit-test-scim-token-that-is-long-enough-123456")
os.environ.setdefault("APP_BASE_URL", "http://localhost:8000")
os.environ.setdefault("OIDC_CLIENT_ID", "identity-access-app")
os.environ.setdefault("OIDC_CLIENT_SECRET", "unit-test-oidc-client-secret")
os.environ.setdefault("OIDC_METADATA_URL", "http://127.0.0.1:8000/oidc/metadata")
os.environ.setdefault("APP_DB", str(TEST_ROOT / ".import-test.sqlite"))

from app.store import Store
from app.wsgi import create_app

BRIDGE_TOKEN = "unit-test-nfc-bridge-token-long-enough-1234"


def fake_response(payload, ok=True):
    response = MagicMock()
    response.ok = ok
    response.status_code = 200 if ok else 401
    response.json.return_value = payload
    return response


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.db_path = str(Path(self.temp.name) / "app.sqlite")
        self.previous_db = os.environ.get("APP_DB")
        os.environ["APP_DB"] = self.db_path
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.store = Store(self.db_path)
        self.user = self.store.save({"userName": "ingeniero@example.test", "title": "mantenimiento"})

    def tearDown(self):
        if self.previous_db is None:
            os.environ.pop("APP_DB", None)
        else:
            os.environ["APP_DB"] = self.previous_db
        self.temp.cleanup()

    def test_health_is_available(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_scim_requires_bearer_token(self):
        self.assertEqual(self.client.get("/scim/v2/Users").status_code, 401)

    def test_scim_list_and_patch_update_local_access(self):
        headers = {"Authorization": "Bearer " + os.environ["SCIM_TOKEN"]}
        listed = self.client.get("/scim/v2/Users", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json["totalResults"], 1)
        response = self.client.patch(
            "/scim/v2/Users/" + self.user["id"],
            headers=headers,
            json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.store.permitted(self.user["id"], "consulta"))

    def test_protected_page_redirects_when_anonymous(self):
        response = self.client.get("/consulta")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")


class NfcRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.db_path = str(Path(self.temp.name) / "app.sqlite")
        self.previous_db = os.environ.get("APP_DB")
        self.previous_env = {key: os.environ.get(key) for key in ("NFC_ENABLED", "NFC_BRIDGE_TOKEN", "NFC_LOGIN_USERNAME", "NFC_LOGIN_PASSWORD")}
        os.environ["APP_DB"] = self.db_path
        os.environ["NFC_ENABLED"] = "true"
        os.environ["NFC_BRIDGE_TOKEN"] = BRIDGE_TOKEN
        os.environ["NFC_LOGIN_USERNAME"] = "admin@example.test"
        os.environ["NFC_LOGIN_PASSWORD"] = "unit-test-badge-password"
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.store = Store(self.db_path)
        self.admin = self.store.save({"userName": "admin@example.test", "title": "admin"})
        self.headers = {"Authorization": "Bearer " + BRIDGE_TOKEN}

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if self.previous_db is None:
            os.environ.pop("APP_DB", None)
        else:
            os.environ["APP_DB"] = self.previous_db
        self.temp.cleanup()

    def test_tap_requires_the_bridge_token(self):
        response = self.client.post("/nfc/tap", json={"uid": "0FC728C9"})
        self.assertEqual(response.status_code, 401)

    def test_unregistered_card_is_rejected(self):
        response = self.client.post("/nfc/tap", headers=self.headers, json={"uid": "AABBCCDD"})
        self.assertEqual(response.status_code, 403)

    def test_inactive_user_card_is_rejected(self):
        self.store.save({"active": False}, self.admin["id"])
        self.store.register_card("0FC728C9", "admin@example.test")
        response = self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        self.assertEqual(response.status_code, 403)

    def test_registered_card_leaves_a_pending_tap(self):
        self.store.register_card("0FC728C9", "admin@example.test", "Tarjeta admin")
        response = self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["accepted"])
        tap = self.store.claim_tap(15)
        self.assertEqual(tap["username"], "admin@example.test")

    def test_poll_without_csrf_is_rejected(self):
        response = self.client.post("/nfc/poll", json={"csrf": "inventado"})
        self.assertEqual(response.status_code, 400)

    def test_poll_without_tap_does_not_log_in(self):
        with self.client.session_transaction() as session:
            session["csrf"] = "csrf-de-prueba"
        response = self.client.post("/nfc/poll", json={"csrf": "csrf-de-prueba"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["login"])

    def test_poll_opens_session_with_the_stored_badge_credentials(self):
        self.store.register_card("0FC728C9", "admin@example.test", "Tarjeta admin")
        self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        with self.client.session_transaction() as session:
            session["csrf"] = "csrf-de-prueba"
        metadata = fake_response({"token_endpoint": "http://keycloak/token", "userinfo_endpoint": "http://keycloak/userinfo"})
        token = fake_response({"access_token": "token-de-prueba"})
        identity = fake_response({"sub": "sub-admin", "email": "admin@example.test"})
        with patch("app.wsgi.requests.get", side_effect=[metadata, identity]), patch("app.wsgi.requests.post", return_value=token) as posted:
            response = self.client.post("/nfc/poll", json={"csrf": "csrf-de-prueba"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["login"])
        self.assertEqual(posted.call_args.kwargs["data"]["grant_type"], "password")
        self.assertEqual(posted.call_args.kwargs["data"]["username"], "admin@example.test")
        with self.client.session_transaction() as session:
            self.assertEqual(session["uid"], self.admin["id"])

    def test_poll_is_denied_when_the_idp_refuses_the_badge(self):
        self.store.register_card("0FC728C9", "admin@example.test")
        self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        with self.client.session_transaction() as session:
            session["csrf"] = "csrf-de-prueba"
        metadata = fake_response({"token_endpoint": "http://keycloak/token"})
        denied = fake_response({"error": "invalid_grant"}, ok=False)
        with patch("app.wsgi.requests.get", return_value=metadata), patch("app.wsgi.requests.post", return_value=denied):
            response = self.client.post("/nfc/poll", json={"csrf": "csrf-de-prueba"})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json["login"])

    def test_nfc_is_disabled_when_the_flag_is_off(self):
        os.environ["NFC_ENABLED"] = "false"
        app = create_app()
        client = app.test_client()
        response = client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        self.assertEqual(response.status_code, 404)

    def test_badge_page_requires_an_admin_session(self):
        response = self.client.get("/nfc")
        self.assertEqual(response.status_code, 302)

    def test_admin_can_open_the_badge_page_and_register_a_card(self):
        with self.client.session_transaction() as session:
            session["uid"] = self.admin["id"]
            session["csrf"] = "csrf-de-prueba"
        page = self.client.get("/nfc")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Badge NFC", page.get_data(as_text=True))
        created = self.client.post(
            "/nfc/tarjetas",
            data={"csrf": "csrf-de-prueba", "uid": "0F:C7:28:C9", "username": "admin@example.test", "label": "Tarjeta del admin"},
        )
        self.assertEqual(created.status_code, 302)
        card = self.store.card("0FC728C9")
        self.assertIsNotNone(card)
        self.assertEqual(card["username"], "admin@example.test")

    def test_admin_form_rejects_an_invalid_uid(self):
        with self.client.session_transaction() as session:
            session["uid"] = self.admin["id"]
            session["csrf"] = "csrf-de-prueba"
        response = self.client.post(
            "/nfc/tarjetas",
            data={"csrf": "csrf-de-prueba", "uid": "no-es-hex", "username": "admin@example.test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=", response.headers["Location"])
        self.assertEqual(self.store.cards(), [])

    def test_poll_with_an_open_session_discards_the_tap_instead_of_saving_it(self):
        self.store.register_card("0FC728C9", "admin@example.test", "Tarjeta admin")
        self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        with self.client.session_transaction() as session:
            session["uid"] = self.admin["id"]
            session["csrf"] = "csrf-de-prueba"
        with patch("app.wsgi.requests.post") as posted:
            response = self.client.post("/nfc/poll", json={"csrf": "csrf-de-prueba"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["login"])
        posted.assert_not_called()
        self.assertIsNone(self.store.claim_tap(15))

    def test_logout_discards_the_pending_taps(self):
        self.store.register_card("0FC728C9", "admin@example.test", "Tarjeta admin")
        self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        with self.client.session_transaction() as session:
            session["uid"] = self.admin["id"]
            session["csrf"] = "csrf-de-prueba"
        response = self.client.post("/logout", data={"csrf": "csrf-de-prueba"})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.store.claim_tap(15))

    def test_a_tap_read_before_logout_does_not_reopen_the_session(self):
        """Regresion: al cerrar sesion la tarjeta no debe volver a entrar sola."""
        self.store.register_card("0FC728C9", "admin@example.test", "Tarjeta admin")
        self.client.post("/nfc/tap", headers=self.headers, json={"uid": "0FC728C9"})
        with self.client.session_transaction() as session:
            session["uid"] = self.admin["id"]
            session["csrf"] = "csrf-de-prueba"
        self.client.post("/logout", data={"csrf": "csrf-de-prueba"})
        access = self.client.get("/")
        self.assertIn("Acceso al laboratorio", access.get_data(as_text=True))
        with self.client.session_transaction() as session:
            csrf = session["csrf"]
        with patch("app.wsgi.requests.post") as posted:
            response = self.client.post("/nfc/poll", json={"csrf": csrf})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["login"])
        posted.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertNotIn("uid", session)

    def test_shift_change_page_and_api(self):
        """Verifica que la vista de cambio de turno y su API de auditoria funcionen."""
        response = self.client.get("/turno")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hub de Seguridad", response.get_data(as_text=True))

        api_response = self.client.post("/api/turno", json={
            "operator": "Guardia Carlos M.",
            "shift": "tarde",
            "status": "success",
            "cams": ["Cámara 1", "Cámara 2"]
        })
        self.assertEqual(api_response.status_code, 200)
        self.assertTrue(api_response.json["ok"])
        events = self.store.events()
        self.assertTrue(any("TURNO_TARDE" in e["action"] for e in events))


if __name__ == "__main__":
    unittest.main()
