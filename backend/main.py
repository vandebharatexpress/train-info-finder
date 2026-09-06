from pathlib import Path
import os

import psycopg
import redis

from psycopg.rows import dict_row
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# PROJECT / ENVIRONMENT CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")


# =========================================================
# POSTGRESQL CONFIG
# =========================================================

# Railway / Neon connection string
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback for local development
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}


def get_connection():
    """
    Prefer DATABASE_URL on Railway/Neon.
    Fall back to separate DB_* variables locally.
    """

    if DATABASE_URL:
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            connect_timeout=5,
        )

    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row,
        connect_timeout=5,
    )


# =========================================================
# REDIS CONFIG
# =========================================================

REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

if REDIS_URL:
    try:
        REDIS_URL = REDIS_URL.strip().strip('"').strip("'")

        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    except Exception as exc:
        print("REDIS CONFIG ERROR TYPE:", type(exc).__name__)
        print("REDIS CONFIG ERROR MESSAGE:", str(exc))
        print("REDIS CONFIG ERROR ARGS:", exc.args)
        redis_client = None


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Train Info Finder API",
    version="1.0.0",
    description="Backend API for RailSync / Train Info Finder",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # React development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Capacitor Android
        "http://localhost",
        "https://localhost",
        "capacitor://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "Train Info Finder API is running",
        "database": "PostgreSQL",
        "cache": "Redis",
        "docs": "/docs",
        "health": "/health",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    database_status = "disconnected"
    redis_status = "disconnected"

    # -------------------------
    # PostgreSQL health
    # -------------------------

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        database_status = "connected"

    except Exception as exc:
        # Error will appear in Railway logs
        print("DATABASE HEALTH ERROR:", repr(exc))

    # -------------------------
    # Redis health
    # -------------------------

    try:
        if redis_client is None:
            raise RuntimeError("Redis client is not configured")

        redis_client.ping()
        redis_status = "connected"

    except Exception as exc:
        print("REDIS HEALTH ERROR TYPE:", type(exc).__name__)
        print("REDIS HEALTH ERROR MESSAGE:", str(exc))
        print("REDIS HEALTH ERROR ARGS:", exc.args)

    return {
        "status": (
            "ok"
            if database_status == "connected"
            else "error"
        ),
        "api": "running",
        "database": database_status,
        "redis": redis_status,
    }


# =========================================================
# TRAIN LOOKUP
# =========================================================

@app.get("/train/{train_number}")
def get_train(train_number: str):
    train_number = train_number.strip()

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    number,
                    name,
                    type_label,
                    source,
                    destination,
                    runs_days,
                    distance_km,
                    travel_time,
                    num_stops
                FROM trains
                WHERE number = %s
                """,
                (train_number,),
            )

            train = cursor.fetchone()

            if train is None:
                raise HTTPException(
                    status_code=404,
                    detail="Train not found",
                )

            cursor.execute(
                """
                SELECT
                    seq,
                    station_code,
                    station_name,
                    arrival,
                    departure,
                    day,
                    distance_km
                FROM stops
                WHERE train_number = %s
                ORDER BY seq
                """,
                (train_number,),
            )

            route_rows = cursor.fetchall()

    route_data = []

    for stop in route_rows:
        route_data.append(
            {
                "seq": stop["seq"],
                "station_code": stop["station_code"],
                "station_name": stop["station_name"],
                "arrival": stop["arrival"],
                "departure": stop["departure"],
                "day": stop["day"],
                "distance_km": (
                    float(stop["distance_km"])
                    if stop["distance_km"] is not None
                    else None
                ),
            }
        )

    return {
        "number": train["number"],
        "name": train["name"],
        "type": train["type_label"],
        "source": train["source"],
        "destination": train["destination"],
        "runs_days": train["runs_days"],
        "distance_km": (
            float(train["distance_km"])
            if train["distance_km"] is not None
            else None
        ),
        "travel_time": train["travel_time"],
        "num_stops": train["num_stops"],
        "route": route_data,
    }


# =========================================================
# STATION SEARCH
# =========================================================

@app.get("/stations/search")
def search_stations(q: str):
    q = q.strip()

    if len(q) < 1:
        return []

    search_pattern = f"%{q}%"

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    code,
                    name
                FROM stations
                WHERE
                    code ILIKE %s
                    OR name ILIKE %s
                ORDER BY
                    CASE
                        WHEN code ILIKE %s THEN 0
                        WHEN name ILIKE %s THEN 1
                        ELSE 2
                    END,
                    name NULLS LAST,
                    code
                LIMIT 10
                """,
                (
                    search_pattern,
                    search_pattern,
                    f"{q}%",
                    f"{q}%",
                ),
            )

            results = cursor.fetchall()

    return [
        {
            "code": row["code"],
            "name": (
                row["name"]
                if row["name"] is not None
                else row["code"]
            ),
        }
        for row in results
    ]


# =========================================================
# STATION DETAILS
# =========================================================

@app.get("/station/{station_code}")
def get_station(station_code: str):
    station_code = station_code.strip().upper()

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    code,
                    name
                FROM stations
                WHERE UPPER(code) = %s
                """,
                (station_code,),
            )

            station = cursor.fetchone()

            if station is None:
                raise HTTPException(
                    status_code=404,
                    detail="Station not found",
                )

            cursor.execute(
                """
                SELECT
                    x.number,
                    x.name,
                    x.type_label,
                    x.source,
                    x.destination,
                    x.arrival,
                    x.departure,
                    x.day
                FROM (
                    SELECT DISTINCT ON (s.train_number)
                        t.number,
                        t.name,
                        t.type_label,
                        t.source,
                        t.destination,
                        s.arrival,
                        s.departure,
                        s.day,
                        s.seq
                    FROM stops s
                    JOIN trains t
                        ON t.number = s.train_number
                    WHERE UPPER(s.station_code) = %s
                    ORDER BY
                        s.train_number,
                        s.seq
                ) AS x
                ORDER BY
                    x.number
                """,
                (station_code,),
            )

            train_rows = cursor.fetchall()

    trains_here = []

    for row in train_rows:
        trains_here.append(
            {
                "number": row["number"],
                "name": row["name"],
                "type": row["type_label"],
                "source": row["source"],
                "destination": row["destination"],
                "arrival": row["arrival"],
                "departure": row["departure"],
                "day": row["day"],
            }
        )

    return {
        "station_code": station["code"],
        "station_name": (
            station["name"]
            if station["name"] is not None
            else station["code"]
        ),
        "train_count": len(trains_here),
        "trains": trains_here,
    }