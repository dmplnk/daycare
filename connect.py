import pymysql
import logging
from config import DB_CONFIG

logger = logging.getLogger(__name__)

class Connect_base:
    def __init__(self):
        self.con = None

    def connect_base(self):
        try:
            self.con = pymysql.connect(
                host=DB_CONFIG.get("host"),
                user=DB_CONFIG.get("user"),
                password=DB_CONFIG.get("password"),
                database=DB_CONFIG.get("database"),
                cursorclass=pymysql.cursors.Cursor
            )
            return self.con
        except Exception:
            logger.exception("Ошибка подключения к БД")
            return None