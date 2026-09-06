from pathlib import Path
import os

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


# =========================================================
# PROJECT / DATABASE CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


missing_settings = [
    key
    for key, value in DB_CONFIG.items()
    if value is None or str(value).strip() == ""
]

if missing_settings:
    raise RuntimeError(
        "Missing database settings in .env: "
        + ", ".join(missing_settings)
    )


# =========================================================
# CONNECTION POOL
# =========================================================

db_pool = ConnectionPool(
    conninfo="",
    kwargs={
        **DB_CONFIG,
        "row_factory": dict_row,
    },
    min_size=1,
    max_size=10,
    timeout=5,
    open=False,
)
