import os
from dotenv import load_dotenv

load_dotenv()


def validate_jwt_settings(
    secret_key: str | None,
    expiration_minutes: int,
    algorithm: str,
) -> None:
    if secret_key is None or not secret_key.strip():
        raise ValueError("SECRET_KEY must be configured.")
    if len(secret_key.encode("utf-8")) < 32:
        raise ValueError("SECRET_KEY must be at least 32 bytes long.")
    if algorithm != "HS256":
        raise ValueError("JWT algorithm must be HS256.")
    if expiration_minutes <= 0:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero.")


class Settings:
    APP_NAME = "EnterpriseAI"
    APP_VERSION = "0.1.0"
    APP_DESCRIPTION = "Plataforma de Inteligência Empresarial"

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_ALGORITHM = "HS256"

    try:
        ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
    except ValueError:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer.") from None


try:
    validate_jwt_settings(
        Settings.SECRET_KEY,
        Settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        Settings.JWT_ALGORITHM,
    )
except ValueError as error:
    raise RuntimeError(str(error)) from error
