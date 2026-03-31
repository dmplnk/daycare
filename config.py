import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "password": os.getenv("DB_PASSWORD"),
    # без таймаута connect() может висеть минутами при недоступном сервере
    "connect_timeout": _int_env("DB_CONNECT_TIMEOUT", 10),
}
# при крашах/глюках C-расширения на Windows: MYSQL_CONNECTOR_PURE=1
if _bool_env("MYSQL_CONNECTOR_PURE"):
    DB_CONFIG["use_pure"] = True