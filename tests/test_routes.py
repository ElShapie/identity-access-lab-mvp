import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
