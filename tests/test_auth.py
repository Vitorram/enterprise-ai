import os
import unittest

import jwt
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Supply an isolated test key before importing the application settings.
os.environ["SECRET_KEY"] = "unit-test-secret-key-not-for-production-000000000000"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "5"

from backend.app.api.auth import login
from backend.app.api.users import create_user
from backend.app.core.config import Settings, validate_jwt_settings
from backend.app.core.database import Base
from backend.app.core.security import decode_access_token, verify_password
from backend.app.models.user import User
from backend.app.schemas.user import LoginRequest, UserCreate, UserResponse


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.session_factory()

    def tearDown(self):
        self.db.close()

    def test_registration_and_login_issue_token_without_exposing_hash(self):
        created_user = create_user(
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="SecurePassword123",
            ),
            self.db,
        )
        response_body = UserResponse.model_validate(created_user).model_dump()
        self.assertEqual(set(response_body), {"id", "name", "email"})

        stored_user = self.db.query(User).filter_by(email="test@example.com").one()
        self.assertNotEqual(stored_user.password_hash, "SecurePassword123")
        self.assertTrue(verify_password("SecurePassword123", stored_user.password_hash))

        token_response = login(
            LoginRequest(email="test@example.com", password="SecurePassword123"),
            self.db,
        )
        self.assertEqual(token_response["token_type"], "bearer")
        payload = decode_access_token(token_response["access_token"])
        self.assertEqual(payload["sub"], str(created_user.id))
        self.assertEqual(
            jwt.get_unverified_header(token_response["access_token"])["alg"],
            Settings.JWT_ALGORITHM,
        )

    def test_invalid_login_credentials_have_same_401_response(self):
        create_user(
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="SecurePassword123",
            ),
            self.db,
        )

        failures = []
        for email, password in (
            ("missing@example.com", "SecurePassword123"),
            ("test@example.com", "WrongPassword123"),
        ):
            with self.subTest(email=email):
                with self.assertRaises(HTTPException) as raised:
                    login(LoginRequest(email=email, password=password), self.db)
                failures.append((raised.exception.status_code, raised.exception.detail))

        self.assertEqual(failures, [(401, "Invalid email or password.")] * 2)

    def test_duplicate_registration_returns_conflict(self):
        user_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="SecurePassword123",
        )
        create_user(user_data, self.db)

        with self.assertRaises(HTTPException) as raised:
            create_user(user_data, self.db)
        self.assertEqual(raised.exception.status_code, 409)

    def test_jwt_settings_reject_missing_weak_or_invalid_configuration(self):
        validate_jwt_settings("a" * 32, 30, "HS256")
        invalid_settings = (
            (None, 30, "HS256"),
            ("short", 30, "HS256"),
            ("a" * 32, 0, "HS256"),
            ("a" * 32, 30, "none"),
        )
        for secret, expiration, algorithm in invalid_settings:
            with self.subTest(expiration=expiration, algorithm=algorithm):
                with self.assertRaises(ValueError):
                    validate_jwt_settings(secret, expiration, algorithm)


if __name__ == "__main__":
    unittest.main()
