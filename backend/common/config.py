"""
Application configuration management

Module that manages environment variables and settings for the SmartScan backend application.
Security-critical settings are loaded from environment variables without providing defaults to ensure safety.

Main settings:
- DATABASE_URL: Supabase PostgreSQL connection string
- JWT_SECRET_KEY: Secret key for JWT token signing (minimum 32 characters required)
- ALLOWED_ORIGIN: CORS allowed domain
- ENV: Development/production environment distinction

Security policy:
- Critical environment variables have minimum length validation
- Automatic .env file loading support (for local development)
"""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, model_validator


def _require_env_var(var_name: str) -> str:
    """Stop server startup if required environment variable is missing"""
    value = os.getenv(var_name)
    if not value or not value.strip():
        raise ValueError(f"Environment variable {var_name} is not set. No default value provided for security reasons.")
    stripped_value = value.strip()
    if len(stripped_value) < 32:
        raise ValueError(f"Environment variable {var_name} value is too short. Must be at least 32 characters.")
    return stripped_value


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]

        os.environ.setdefault(key, value)


_load_env_file()


class Settings(BaseModel):
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    DB_HOST: str | None = os.getenv("DB_HOST")
    DB_PORT: str | None = os.getenv("DB_PORT")
    DB_USER: str | None = os.getenv("DB_USER")
    DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")
    DB_NAME: str | None = os.getenv("DB_NAME")

    # SMTP
    SMTP_HOST: str | None = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str | None = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_FROM_EMAIL: str | None = os.getenv("SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Smart Scan")
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = int(
        os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "10")
    )
    MONITORING_FOUND_WINDOW_MINUTES: int = int(
        os.getenv("MONITORING_FOUND_WINDOW_MINUTES", "10")
    )

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "smart-scan-dev-secret")  # Must be replaced with environment variable in production
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080")
    )
    PASSWORD_HASH_ITERATIONS: int = int(
        os.getenv("PASSWORD_HASH_ITERATIONS", "100000")
    )

    # Kakao account link (magic link)
    # Separate secret key shared with external services (chatbot Lambda). Isolated from JWT_SECRET_KEY
    # so that if one side is compromised, the other side's tokens are not at risk.
    KAKAO_LINK_JWT_SECRET: str = os.getenv(
        "KAKAO_LINK_JWT_SECRET",
        "smart-scan-dev-kakao-link-secret"
    )
    KAKAO_LINK_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("KAKAO_LINK_TOKEN_EXPIRE_MINUTES", "5")
    )

    # Shared secret between chatbot services. When chatbot Lambda calls /api/chatbot/* endpoints,
    # this value must be passed in X-Chatbot-Key header. Isolated from JWT_SECRET_KEY / KAKAO_LINK_JWT_SECRET.
    CHATBOT_SHARED_KEY: str = os.getenv(
        "CHATBOT_SHARED_KEY",
        "smart-scan-dev-chatbot-key"
    )

    # CORS
    ALLOWED_ORIGIN: str = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")

    # Environment
    ENV: str = os.getenv("ENV", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_prod_secrets(self):
        if self.ENV == "production" and self.JWT_SECRET_KEY == "smart-scan-dev-secret":
            raise ValueError("JWT_SECRET_KEY must be changed from default in production environment")
        if self.ENV == "production" and self.KAKAO_LINK_JWT_SECRET == "smart-scan-dev-kakao-link-secret":
            raise ValueError("KAKAO_LINK_JWT_SECRET must be changed from default in production environment")
        if self.ENV == "production" and self.CHATBOT_SHARED_KEY == "smart-scan-dev-chatbot-key":
            raise ValueError("CHATBOT_SHARED_KEY must be changed from default in production environment")
        return self


settings = Settings()
