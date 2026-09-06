import csv
import os
import sys
from pathlib import Path
from datetime import datetime

import psycopg
from dotenv import load_dotenv


# =========================================================
# PROJECT CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")


# Railpull output directory.
# By default, use: <project_root>/railpull/data/out
# You can optionally override this path in .env with RAILPULL_OUT_DIR.
RAILPULL_OUT_DIR = os.getenv("RAILPULL_OUT_DIR")

SOURCE_DIR = (
    Path(RAILPULL_OUT_DIR).expanduser().resolve()
    if RAILPULL_OUT_DIR
    else BASE_DIR / "railpull" / "data" / "out"
)


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


# =========================================================
# CSV DEFINITIONS
# =========================================================

CSV_FILES = {
    "stations": {
        "path": SOURCE_DIR / "stations.csv",
        "columns": [
            "code",
            "name",
            "lat",
            "lon",
        ],
    },

    "trains": {
        "path": SOURCE_DIR / "trains.csv",
        "columns": [
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
    },

    "stops": {
        "path": SOURCE_DIR / "stops.csv",
        "columns": [
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
    },
}


# =========================================================
# VALIDATION
# =========================================================

def validate_database_config():
    missing = [
        key
        for key, value in DB_CONFIG.items()
        if value is None or str(value).strip() == ""
    ]

    if missing:
        raise RuntimeError(
            "Missing database settings in .env: "
            + ", ".join(missing)
        )


def validate_csv(table_name, config):
    csv_path = config["path"]
    expected_columns = config["columns"]

    print(f"Checking {csv_path.name}...")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"File not found: {csv_path}"
        )

    if csv_path.stat().st_size == 0:
        raise RuntimeError(
            f"{csv_path.name} is empty."
        )

    with open(
        csv_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        try:
            header = next(reader)
        except StopIteration:
            raise RuntimeError(
                f"{csv_path.name} contains no data."
            )

    missing_columns = [
        column
        for column in expected_columns
        if column not in header
    ]

    if missing_columns:
        raise RuntimeError(
            f"{csv_path.name} is missing columns: "
            + ", ".join(missing_columns)
        )

    modified_time = datetime.fromtimestamp(
        csv_path.stat().st_mtime
    )

    print(
        f"  OK | "
        f"{csv_path.stat().st_size / 1024 / 1024:.2f} MB | "
        f"modified {modified_time}"
    )


def validate_all_files():
    print()
    print("==========================================")
    print("VALIDATING RAILPULL SNAPSHOT")
    print("==========================================")
    print(f"Source: {SOURCE_DIR}")
    print()

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Railpull output directory does not exist:\n"
            f"{SOURCE_DIR}"
        )

    for table_name, config in CSV_FILES.items():
        validate_csv(
            table_name,
            config
        )

    print()
    print("CSV validation passed.")


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_counts(cursor):
    cursor.execute("SELECT COUNT(*) FROM trains;")
    trains = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stations;")
    stations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stops;")
    stops = cursor.fetchone()[0]

    return {
        "trains": trains,
        "stations": stations,
        "stops": stops,
    }


def print_counts(title, counts):
    print()
    print(title)
    print("-" * 35)

    print(
        f"Trains:   "
        f"{counts['trains']:,}"
    )

    print(
        f"Stations: "
        f"{counts['stations']:,}"
    )

    print(
        f"Stops:    "
        f"{counts['stops']:,}"
    )


# =========================================================
# CSV COPY
# =========================================================

def copy_csv(
    cursor,
    csv_path,
    table_name,
    columns
):
    print(
        f"Importing "
        f"{csv_path.name} -> {table_name}..."
    )

    copy_sql = f"""
        COPY {table_name}
        ({", ".join(columns)})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            NULL ''
        )
    """

    with cursor.copy(copy_sql) as copy:

        with open(
            csv_path,
            "r",
            encoding="utf-8-sig"
        ) as file:

            while True:

                chunk = file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                copy.write(chunk)

    print(
        f"Finished importing {table_name}."
    )


# =========================================================
# DATABASE REFRESH
# =========================================================

def refresh_database():

    validate_database_config()

    print()
    print("Connecting to PostgreSQL...")

    with psycopg.connect(
        **DB_CONFIG
    ) as conn:

        with conn.cursor() as cursor:

            print("Connected successfully.")

            before_counts = get_counts(
                cursor
            )

            print_counts(
                "CURRENT DATABASE",
                before_counts
            )

            print()
            print(
                "Starting atomic database refresh..."
            )

            # =============================================
            # IMPORTANT:
            #
            # TRUNCATE and COPY occur inside ONE PostgreSQL
            # transaction.
            #
            # If ANY import fails, PostgreSQL rolls back
            # everything and keeps the previous dataset.
            # =============================================

            cursor.execute("""
                TRUNCATE TABLE
                    stops,
                    trains,
                    stations
                CASCADE;
            """)

            copy_csv(
                cursor,
                CSV_FILES["stations"]["path"],
                "stations",
                CSV_FILES["stations"]["columns"],
            )

            copy_csv(
                cursor,
                CSV_FILES["trains"]["path"],
                "trains",
                CSV_FILES["trains"]["columns"],
            )

            copy_csv(
                cursor,
                CSV_FILES["stops"]["path"],
                "stops",
                CSV_FILES["stops"]["columns"],
            )

            # =============================================
            # VERIFY NEW DATABASE
            # =============================================

            after_counts = get_counts(
                cursor
            )

            if after_counts["trains"] == 0:
                raise RuntimeError(
                    "Refresh produced zero trains."
                )

            if after_counts["stations"] == 0:
                raise RuntimeError(
                    "Refresh produced zero stations."
                )

            if after_counts["stops"] == 0:
                raise RuntimeError(
                    "Refresh produced zero stops."
                )

            cursor.execute("""
                SELECT COUNT(*)
                FROM stops s
                LEFT JOIN stations st
                    ON st.code = s.station_code
                WHERE st.code IS NULL;
            """)

            missing_station_codes = (
                cursor.fetchone()[0]
            )

            if missing_station_codes != 0:
                raise RuntimeError(
                    "Database validation failed: "
                    f"{missing_station_codes} stop records "
                    "reference missing stations."
                )

            print_counts(
                "NEW DATABASE",
                after_counts
            )

            print()
            print(
                "Missing station codes:",
                missing_station_codes
            )

            print()
            print(
                "Database validation passed."
            )

        # psycopg commits here automatically
        # because no exception occurred.

    print()
    print("==========================================")
    print("DATABASE REFRESH COMPLETE")
    print("==========================================")
    print(
        "The new railpull snapshot is now active."
    )


# =========================================================
# RUN SCRIPT
# =========================================================

def main():

    try:

        validate_all_files()

        refresh_database()

    except Exception as error:

        print()
        print("==========================================")
        print("DATABASE REFRESH FAILED")
        print("==========================================")

        print(
            f"{type(error).__name__}: {error}"
        )

        print()
        print(
            "The refresh was not completed."
        )

        print(
            "If a database transaction had started, "
            "PostgreSQL rolled it back."
        )

        sys.exit(1)


if __name__ == "__main__":
    main()