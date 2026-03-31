import logging

from mysql.connector import connect
from config import DB_CONFIG

logger = logging.getLogger(__name__)


def _connect_kwargs():
    """Только не-None поля: иначе коннектор может кидать ValueError/TypeError, не наследники mysql.Error."""
    return {k: v for k, v in DB_CONFIG.items() if v is not None}


class Connect_base:
    def __init__(self):
        self.con = None

    def connect_base(self):
        if not DB_CONFIG.get("host") or not DB_CONFIG.get("user"):
            logger.error("БД не настроена: задайте DB_HOST и DB_USER в .env")
            return None
        try:
            self.con = connect(**_connect_kwargs())
            if self.con.is_connected():
                return self.con
        except Exception:
            # Ловим всё: mysql.Error, ValueError, InterfaceError из сокета, ошибки C-расширения и т.д.
            logger.exception("Не удалось подключиться к MySQL")
        return None