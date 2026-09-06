import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# CHANGE THIS to wherever your railpull folder is
RAILPULL_DIR = PROJECT_ROOT / "railpull"


def run_command(command, cwd):
    print(f"\n>>> Running: {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=cwd,
        check=True
    )

    return result


def main():
    try:
        print("=" * 60)
        print("TRAIN INFO FINDER - AUTOMATIC DATABASE REFRESH")
        print("=" * 60)

        # 1. Fetch latest timetable from NTES
        print("\n[1/4] Fetching latest railway data...")
        run_command(
            [sys.executable, "ntes/crawl.py"],
            RAILPULL_DIR
        )

        # 2. Generate new CSV files
        print("\n[2/4] Generating fresh CSV files...")
        run_command(
            [sys.executable, "transform/export.py"],
            RAILPULL_DIR
        )

        # 3. Refresh PostgreSQL database
        print("\n[3/4] Updating PostgreSQL database...")
        run_command(
            [sys.executable, "refresh_database.py"],
            BACKEND_DIR
        )

        # 4. Clear Redis cache
        print("\n[4/4] Clearing Redis cache...")

        run_command(
            [
                "docker",
                "exec",
                "train-info-redis",
                "redis-cli",
                "FLUSHDB"
            ],
            PROJECT_ROOT
        )

        print("\n" + "=" * 60)
        print("DATABASE REFRESH COMPLETED SUCCESSFULLY ✅")
        print("=" * 60)

    except subprocess.CalledProcessError as error:
        print("\n❌ Refresh failed.")
        print(error)

        sys.exit(1)


if __name__ == "__main__":
    main()