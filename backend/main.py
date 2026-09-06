from pathlib import Path
import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


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
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}


def get_connection():
    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row
    )


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Train Info Finder API is running",
        "database": "PostgreSQL"
    }


@app.get("/train/{train_number}")
def get_train(train_number: str):
    train_number = train_number.strip()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
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
                ''',
                (train_number,)
            )

            train = cursor.fetchone()

            if train is None:
                raise HTTPException(
                    status_code=404,
                    detail="Train not found"
                )

            cursor.execute(
                '''
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
                ''',
                (train_number,)
            )

            route_rows = cursor.fetchall()

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
        "route": route_data
    }


@app.get("/stations/search")
def search_stations(q: str):
    q = q.strip()

    if len(q) < 1:
        return []

    search_pattern = f"%{q}%"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
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
                ''',
                (
                    search_pattern,
                    search_pattern,
                    f"{q}%",
                    f"{q}%"
                )
            )

            results = cursor.fetchall()

    return [
        {
            "code": row["code"],
            "name": row["name"] if row["name"] is not None else row["code"]
        }
        for row in results
    ]


@app.get("/station/{station_code}")
def get_station(station_code: str):
    station_code = station_code.strip().upper()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT
                    code,
                    name
                FROM stations
                WHERE UPPER(code) = %s
                ''',
                (station_code,)
            )

            station = cursor.fetchone()

            if station is None:
                raise HTTPException(
                    status_code=404,
                    detail="Station not found"
                )

            cursor.execute(
                '''
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
                ''',
                (station_code,)
            )

            train_rows = cursor.fetchall()

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

    return {
        "station_code": station["code"],
        "station_name": (
            station["name"]
            if station["name"] is not None
            else station["code"]
        ),
        "train_count": len(trains_here),
        "trains": trains_here
    }
