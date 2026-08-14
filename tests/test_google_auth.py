import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GOOGLE_CLIENT_ID"] = "test-client.apps.googleusercontent.com"

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models.schema import User, UserIdentity


class GoogleAuthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        app.dependency_overrides.clear()

    @staticmethod
    def google_claims(**overrides):
        claims = {
            "sub": "google-user-123",
            "email": "owner@example.com",
            "email_verified": True,
            "name": "Business Owner",
        }
        claims.update(overrides)
        return claims

    @patch("app.api.auth_router.verify_google_id_token")
    def test_existing_user_receives_application_token(self, verify_token):
        verify_token.return_value = self.google_claims()
        identity = SimpleNamespace(user_id="user-123")
        user = SimpleNamespace(
            id="user-123",
            email="owner@example.com",
            is_active=True,
        )

        def query(model):
            result = MagicMock()
            result.filter.return_value.first.return_value = identity if model is UserIdentity else user
            return result

        self.db.query.side_effect = query

        response = self.client.post(
            "/api/auth/google",
            json={"credential": "valid-google-id-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "owner@example.com")
        self.assertFalse(response.json()["isNewUser"])
        self.assertTrue(response.json()["accessToken"])
        self.db.add.assert_not_called()

    @patch("app.api.auth_router.verify_google_id_token")
    def test_first_google_sign_in_creates_user(self, verify_token):
        verify_token.return_value = self.google_claims()

        def query(model):
            result = MagicMock()
            result.filter.return_value.first.return_value = None
            return result

        self.db.query.side_effect = query
        self.db.flush.side_effect = lambda: setattr(
            self.db.add.call_args_list[0].args[0],
            "id",
            "new-user-123",
        )

        response = self.client.post(
            "/api/auth/google",
            json={"credential": "valid-google-id-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["isNewUser"])
        created_user = self.db.add.call_args_list[0].args[0]
        created_identity = self.db.add.call_args_list[1].args[0]
        self.assertEqual(created_user.email, "owner@example.com")
        self.assertTrue(created_user.password_hash.startswith("$argon2"))
        self.assertEqual(created_identity.provider, "google")
        self.assertEqual(created_identity.provider_subject, "google-user-123")
        self.db.commit.assert_called_once()

    @patch("app.api.auth_router.verify_google_id_token")
    def test_invalid_google_token_is_rejected(self, verify_token):
        verify_token.side_effect = ValueError("invalid token")

        response = self.client.post(
            "/api/auth/google",
            json={"credential": "invalid-google-id-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid Google credential")

    @patch("app.api.auth_router.verify_google_id_token")
    def test_unverified_google_email_is_rejected(self, verify_token):
        verify_token.return_value = self.google_claims(email_verified=False)

        response = self.client.post(
            "/api/auth/google",
            json={"credential": "valid-google-id-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Google email is not verified")


if __name__ == "__main__":
    unittest.main()
