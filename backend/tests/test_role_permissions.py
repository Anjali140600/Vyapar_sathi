from types import SimpleNamespace
import unittest

from fastapi import HTTPException

from backend.app.core.security import ensure_role, require_roles


class RolePermissionTests(unittest.TestCase):
    def test_owner_can_use_owner_action(self):
        user = SimpleNamespace(role="owner")
        self.assertIs(ensure_role(user, {"owner"}), user)

    def test_accountant_can_use_finance_action(self):
        user = SimpleNamespace(role="accountant")
        self.assertIs(ensure_role(user, {"owner", "accountant"}), user)

    def test_staff_is_blocked_from_finance_action(self):
        with self.assertRaises(HTTPException) as caught:
            ensure_role(SimpleNamespace(role="staff"), {"owner", "accountant"})
        self.assertEqual(caught.exception.status_code, 403)

    def test_unknown_role_is_blocked(self):
        with self.assertRaises(HTTPException) as caught:
            ensure_role(SimpleNamespace(role="user"), {"owner", "staff", "accountant"})
        self.assertEqual(caught.exception.status_code, 403)

    def test_invalid_dependency_configuration_fails_fast(self):
        with self.assertRaises(ValueError):
            require_roles("administrator")


if __name__ == "__main__":
    unittest.main()
