import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, model_validator


def _require_env_var(var_name: str) -> str:
    """환경변수가 필수일 때 없으면 서버 시작을 중단"""
    value = os.getenv(var_name)
    if not value or not value.strip():
        raise ValueError(f"환경변수 {var_name}이 설정되지 않았습니다. 보안상 기본값을 제공하지 않습니다.")
    stripped_value = value.strip()
    if len(stripped_value) < 32:
        raise ValueError(f"환경변수 {var_name}의 값이 너무 짧습니다. 최소 32자 이상이어야 합니다.")
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
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "smart-scan-dev-secret")  # 프로덕션에서 반드시 환경변수로 교체
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
    ENV: str = os.getenv("ENV", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_prod_secrets(self):
        if self.ENV == "production" and self.JWT_SECRET_KEY == "smart-scan-dev-secret":
            raise ValueError("JWT_SECRET_KEY must be changed from default in production environment")
        return self


settings = Settings()
