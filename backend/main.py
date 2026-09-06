from pathlib import Path
import os
import json

import psycopg
import redis

from psycopg.rows import dict_row
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder


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


# =========================================================
# REDIS CONFIG
# =========================================================

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=int(os.getenv("REDIS_PORT", 6380)),
    db=0,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


# =========================================================
# CACHE SETTINGS
# =========================================================

TRAIN_CACHE_TTL = 3600
STATION_CACHE_TTL = 3600
SEARCH_CACHE_TTL = 600


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row
    )


# =========================================================
# REDIS HELPERS
# =========================================================

def get_cached_data(key: str):
    """
    Try to retrieve JSON data from Redis.

    If Redis is unavailable, return None instead of
    crashing the application.
    """
    try:
        cached = redis_client.get(key)

        if cached is not None:
            print(f"REDIS HIT: {key}")
            return json.loads(cached)

        print(f"REDIS MISS: {key}")

    except Exception as exc:
        print(f"REDIS READ ERROR [{key}]: {exc}")

    return None


def set_cached_data(key: str, data, ttl: int):
    """
    Store JSON data in Redis.

    Failure to cache should never stop PostgreSQL
    responses from being returned.
    """
    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(jsonable_encoder(data))
        )

        print(f"REDIS SAVED: {key} (TTL={ttl}s)")

    except Exception as exc:
        print(f"REDIS WRITE ERROR [{key}]: {exc}")



# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Train Info Finder API",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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
        "redis_host": os.getenv("REDIS_HOST", "127.0.0.1"),
        "redis_port": int(os.getenv("REDIS_PORT", 6380)),
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
    # PostgreSQL check
    # -------------------------

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok;")
                cursor.fetchone()

        database_status = "connected"

    except Exception:
        database_status = "disconnected"

    # -------------------------
    # Redis check
    # -------------------------

    try:
        redis_client.ping()
        redis_status = "connected"

    except Exception:
        redis_status = "disconnected"

    # PostgreSQL is essential.
    # Redis is optional.

    if database_status != "connected":
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "api": "running",
                "database": database_status,
                "redis": redis_status,
            }
        )

    return {
        "status": "ok",
        "api": "running",
        "database": database_status,
        "redis": redis_status,
        "redis_host": os.getenv("REDIS_HOST", "127.0.0.1"),
        "redis_port": int(os.getenv("REDIS_PORT", 6380)),
    }


# =========================================================
# TRAIN SEARCH
# =========================================================

@app.get("/train/{train_number}")
def get_train(train_number: str):

    train_number = train_number.strip()

    cache_key = f"train:{train_number}"

    # =====================================================
    # CHECK REDIS FIRST
    # =====================================================

    cached_train = get_cached_data(cache_key)

    if cached_train is not None:
        return cached_train

    # =====================================================
    # REDIS MISS → QUERY POSTGRESQL
    # =====================================================

    try:

        with get_connection() as conn:

            with conn.cursor() as cursor:

                # -----------------------------------------
                # MAIN TRAIN INFORMATION
                # -----------------------------------------

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
                    (train_number,)
                )

                train = cursor.fetchone()

                if train is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Train not found"
                    )

                # -----------------------------------------
                # COMPLETE ROUTE
                # -----------------------------------------

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
                    (train_number,)
                )

                route_rows = cursor.fetchall()

    except HTTPException:
        raise

    except Exception as exc:

        print("DATABASE ERROR:", exc)

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )


    # =====================================================
    # FORMAT ROUTE
    # =====================================================

    route_data = []

    for stop in route_rows:

        route_data.append({
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
            )
        })


    # =====================================================
    # RESPONSE
    # =====================================================

    response = {
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
        "route": route_data
    }


    # =====================================================
    # STORE IN REDIS FOR 1 HOUR
    # =====================================================

    set_cached_data(
        cache_key,
        response,
        TRAIN_CACHE_TTL
    )

    return response


# =========================================================
# STATION AUTOCOMPLETE
# =========================================================

@app.get("/stations/search")
def search_stations(q: str):

    q = q.strip()

    if len(q) < 1:
        return []


    # Normalize so:
    #
    # hyd
    # HYD
    # Hyd
    #
    # all use the same Redis key.

    normalized_query = q.lower()

    cache_key = f"station_search:{normalized_query}"


    # =====================================================
    # CHECK REDIS
    # =====================================================

    cached_results = get_cached_data(cache_key)

    if cached_results is not None:
        return cached_results


    # =====================================================
    # QUERY POSTGRESQL
    # =====================================================

    search_pattern = f"%{q}%"

    try:

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
                        f"{q}%"
                    )
                )

                results = cursor.fetchall()

    except Exception as exc:

        print("DATABASE ERROR:", exc)

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )


    # =====================================================
    # FORMAT RESULT
    # =====================================================

    response = [

        {
            "code": row["code"],

            "name": (
                row["name"]
                if row["name"] is not None
                else row["code"]
            )
        }

        for row in results
    ]


    # =====================================================
    # CACHE AUTOCOMPLETE FOR 10 MINUTES
    # =====================================================

    set_cached_data(
        cache_key,
        response,
        SEARCH_CACHE_TTL
    )


    return response


# =========================================================
# STATION DETAILS
# =========================================================

@app.get("/station/{station_code}")
def get_station(station_code: str):

    station_code = station_code.strip().upper()

    cache_key = f"station:{station_code}"


    # =====================================================
    # CHECK REDIS FIRST
    # =====================================================

    cached_station = get_cached_data(cache_key)

    if cached_station is not None:
        return cached_station


    # =====================================================
    # QUERY POSTGRESQL
    # =====================================================

    try:

        with get_connection() as conn:

            with conn.cursor() as cursor:

                # -----------------------------------------
                # GET STATION
                # -----------------------------------------

                cursor.execute(
                    """
                    SELECT
                        code,
                        name
                    FROM stations
                    WHERE UPPER(code) = %s
                    """,
                    (station_code,)
                )

                station = cursor.fetchone()

                if station is None:

                    raise HTTPException(
                        status_code=404,
                        detail="Station not found"
                    )


                # -----------------------------------------
                # GET TRAINS SERVING STATION
                # -----------------------------------------

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

                    ORDER BY x.number
                    """,

                    (station_code,)
                )

                train_rows = cursor.fetchall()

    except HTTPException:
        raise

    except Exception as exc:

        print("DATABASE ERROR:", exc)

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )


    # =====================================================
    # FORMAT TRAINS
    # =====================================================

    trains_here = []

    for row in train_rows:

        trains_here.append({
            "number": row["number"],
            "name": row["name"],
            "type": row["type_label"],
            "source": row["source"],
            "destination": row["destination"],
            "arrival": row["arrival"],
            "departure": row["departure"],
            "day": row["day"]
        })


    # =====================================================
    # RESPONSE
    # =====================================================

    response = {

        "station_code": station["code"],

        "station_name": (
            station["name"]
            if station["name"] is not None
            else station["code"]
        ),

        "train_count": len(trains_here),

        "trains": trains_here
    }


    # =====================================================
    # CACHE STATION FOR 1 HOUR
    # =====================================================

    set_cached_data(
        cache_key,
        response,
        STATION_CACHE_TTL
    )


    return response