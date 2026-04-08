import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict


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

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")

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
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "smart-scan-dev-secret")
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

    # CORS
    ALLOWED_ORIGIN: str = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")

    # Environment
    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = ConfigDict(frozen=True)


settings = Settings()
