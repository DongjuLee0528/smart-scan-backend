"""
Backend unit test common configuration

Forces environment variables to development mode to allow testing
pure service logic without JWT authentication or actual DB connections.
"""
import os

# Environment variables must be set before importing Settings/db.py to bypass various guards
os.environ["ENV"] = "development"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32c")
os.environ.setdefault("KAKAO_LINK_JWT_SECRET", "test-kakao-link-secret-for-unit-tests!!")
# DB connection won't actually occur but URL validation must pass when loading db.py module
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
