import tempfile
import unittest
from pathlib import Path

from app.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.store = Store(Path(self.temp.name) / "lab.sqlite")
        self.user = self.store.save({"userName": "ingeniero@example.test", "title": "mantenimiento"})

    def tearDown(self):
        self.temp.cleanup()

    def test_role_permissions_are_least_privilege(self):
        self.assertTrue(self.store.permitted(self.user["id"], "mantenimiento"))
        self.assertFalse(self.store.permitted(self.user["id"], "admin"))

    def test_role_change_applies_to_existing_session_id(self):
        self.store.save({"title": "auditor"}, self.user["id"])
        self.assertFalse(self.store.permitted(self.user["id"], "mantenimiento"))
        self.assertTrue(self.store.permitted(self.user["id"], "registros"))

    def test_deactivation_blocks_existing_session_id(self):
        self.store.save({"active": False}, self.user["id"])
        self.assertFalse(self.store.permitted(self.user["id"], "consulta"))

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save({"title": "superuser"}, self.user["id"])

    def test_identity_cannot_be_rebound(self):
        self.assertTrue(self.store.bind_identity(self.user["id"], "subject-a"))
        self.assertFalse(self.store.bind_identity(self.user["id"], "subject-b"))

    def test_delete_deactivates_instead_of_erasing_audit_identity(self):
        self.assertTrue(self.store.deactivate(self.user["id"]))
        self.assertFalse(self.store.permitted(self.user["id"], "consulta"))
        self.assertEqual(self.store.get(self.user["id"])["active"], False)


if __name__ == "__main__":
    unittest.main()
