import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)



def _get(key: str, default=None):
    val = os.getenv(key)

    if isinstance(default, bool):
        return str(val if val is not None else default).casefold() == "true"

    return val if val is not None else default


class Settings:
    TZ: str = "UTC"

    @property
    def time_zone(self) -> ZoneInfo:
        return ZoneInfo(self.TZ)


    DATABASE_URL = _get("DATABASE_URL")
    SYNC_DATABASE_URL = _get("SYNC_DATABASE_URL")
    DB_ECHO = _get("DB_ECHO", "False").lower() == "true"

settings = Settings()