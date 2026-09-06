import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# -----------------------------
# PROJECT PATHS
# -----------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

TRAINS_CSV = DATA_DIR / "trains.csv"
STATIONS_CSV = DATA_DIR / "stations.csv"
STOPS_CSV = DATA_DIR / "stops.csv"


# -----------------------------
# LOAD .ENV
# -----------------------------

load_dotenv(BASE_DIR / ".env")


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def copy_csv(cursor, csv_path, table_name, columns):
    print(f"Importing {csv_path.name} -> {table_name}...")

    copy_sql = f"""
        COPY {table_name} ({", ".join(columns)})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            NULL ''
        )
    """

    with cursor.copy(copy_sql) as copy:
        with open(csv_path, "r", encoding="utf-8-sig") as file:
            while True:
                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                copy.write(chunk)

    print(f"Finished importing {table_name}.")


def main():
    print("Connecting to PostgreSQL...")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:

            print("Connected successfully.")

            print("Clearing existing railway data...")

            cursor.execute("""
                TRUNCATE TABLE
                    stops,
                    trains,
                    stations
                CASCADE;
            """)

            copy_csv(
                cursor,
                STATIONS_CSV,
                "stations",
                [
                    "code",
                    "name",
                    "lat",
                    "lon",
                ],
            )

            copy_csv(
                cursor,
                TRAINS_CSV,
                "trains",
                [
                    "number",
                    "name",
                    "type",
                    "type_label",
                    "runs_days",
                    "source_code",
                    "source",
                    "dest_code",
                    "destination",
                    "distance_km",
                    "travel_time",
                    "num_stops",
                ],
            )

            copy_csv(
                cursor,
                STOPS_CSV,
                "stops",
                [
                    "train_number",
                    "seq",
                    "station_code",
                    "station_name",
                    "day",
                    "arrival",
                    "departure",
                    "halt_min",
                    "distance_km",
                ],
            )

            cursor.execute("SELECT COUNT(*) FROM trains;")
            train_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM stations;")
            station_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM stops;")
            stop_count = cursor.fetchone()[0]

            print()
            print("==============================")
            print("IMPORT COMPLETE")
            print("==============================")
            print(f"Trains:   {train_count:,}")
            print(f"Stations: {station_count:,}")
            print(f"Stops:    {stop_count:,}")
            print("==============================")


if __name__ == "__main__":
    main()