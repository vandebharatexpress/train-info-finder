from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import redis
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
RAILPULL_DIR = PROJECT_ROOT / "railpull"
DATA_DIR = RAILPULL_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_DIR = DATA_DIR / "out"

REFRESH_SCRIPT = BACKEND_DIR / "refresh_database.py"
ENV_FILE = PROJECT_ROOT / ".env"
LOG_FILE = BACKEND_DIR / "data_sync.log"
MARKER_FILE = BACKEND_DIR / ".last_successful_data_refresh"

load_dotenv(ENV_FILE)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))
DEFAULT_INTERVAL_DAYS = int(os.getenv("DATA_REFRESH_DAYS", "14"))

EXPECTED_CSVS = [
    OUT_DIR / "stations.csv",
    OUT_DIR / "trains.csv",
    OUT_DIR / "stops.csv",
]


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_command(command: list[str], cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
    )

    if result.stdout.strip():
        log(result.stdout.strip())

    if result.returncode != 0:
        if result.stderr.strip():
            log(result.stderr.strip())

        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}"
        )

    return result.stdout.strip()


def sync_owner_repo() -> None:
    if not (RAILPULL_DIR / ".git").exists():
        raise RuntimeError(
            f"{RAILPULL_DIR} is not a Git repository."
        )

    log("Checking owner's Railpull repository...")

    remote_url = run_command(
        ["git", "remote", "get-url", "origin"],
        RAILPULL_DIR,
    )
    log(f"Watching remote source: {remote_url}")

    branch = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        RAILPULL_DIR,
    )

    if branch == "HEAD":
        raise RuntimeError("Railpull is in detached HEAD state.")

    tracked_changes = run_command(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        RAILPULL_DIR,
    )

    if tracked_changes:
        raise RuntimeError(
            "Railpull has local changes to tracked code. "
            "Automatic pull stopped to protect them."
        )

    run_command(["git", "fetch", "origin"], RAILPULL_DIR)

    local_commit = run_command(
        ["git", "rev-parse", "HEAD"],
        RAILPULL_DIR,
    )

    remote_commit = run_command(
        ["git", "rev-parse", f"origin/{branch}"],
        RAILPULL_DIR,
    )

    if local_commit == remote_commit:
        log("Owner repository is already up to date.")
        return

    log("Owner repository update found. Pulling latest code...")

    run_command(
        ["git", "pull", "--ff-only", "origin", branch],
        RAILPULL_DIR,
    )

    log("Owner repository updated successfully.")


def parse_marker() -> datetime | None:
    if not MARKER_FILE.exists():
        return None

    try:
        return datetime.fromisoformat(
            MARKER_FILE.read_text(encoding="utf-8").strip()
        )
    except Exception:
        return None


def existing_snapshot_time() -> datetime | None:
    times = [
        datetime.fromtimestamp(path.stat().st_mtime)
        for path in EXPECTED_CSVS
        if path.exists()
    ]

    if len(times) != len(EXPECTED_CSVS):
        return None

    return min(times)


def last_refresh_time() -> datetime | None:
    return parse_marker() or existing_snapshot_time()


def refresh_due(interval_days: int) -> tuple[bool, datetime | None]:
    previous = last_refresh_time()

    if previous is None:
        return True, None

    return (
        datetime.now() >= previous + timedelta(days=interval_days),
        previous,
    )


def validate_csv_outputs() -> None:
    missing = [
        str(path)
        for path in EXPECTED_CSVS
        if not path.exists() or path.stat().st_size == 0
    ]

    if missing:
        raise RuntimeError(
            "Fresh Railpull export did not create valid required CSVs:\n"
            + "\n".join(missing)
        )

    log("Fresh CSV snapshot validated.")


def unique_backup_path(name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"_sync_backup_{name}_{stamp}"


def move_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False

    source.rename(destination)
    return True


def restore_directory(
    current: Path,
    backup: Path,
    backup_existed: bool,
) -> None:
    if current.exists():
        shutil.rmtree(current)

    if backup_existed and backup.exists():
        backup.rename(current)


def build_fresh_snapshot() -> tuple[Path, Path, bool, bool]:
    backup_raw = unique_backup_path("raw")
    backup_out = unique_backup_path("out")

    raw_existed = move_if_exists(RAW_DIR, backup_raw)
    out_existed = move_if_exists(OUT_DIR, backup_out)

    try:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        log("Starting fresh NTES crawl.")
        log(
            "This is intentionally slow and polite; "
            "a full Railpull crawl may take hours."
        )

        run_command(
            [sys.executable, "ntes/crawl.py"],
            RAILPULL_DIR,
        )

        log("NTES crawl completed. Exporting CSV files...")

        run_command(
            [sys.executable, "transform/export.py"],
            RAILPULL_DIR,
        )

        validate_csv_outputs()

        return backup_raw, backup_out, raw_existed, out_existed

    except Exception:
        log(
            "Fresh crawl/export failed. Restoring previous "
            "Railpull snapshot."
        )
        restore_directory(RAW_DIR, backup_raw, raw_existed)
        restore_directory(OUT_DIR, backup_out, out_existed)
        raise


def preflight_redis() -> None:
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    client.ping()
    log(f"Redis preflight OK at {REDIS_HOST}:{REDIS_PORT}.")


def refresh_postgresql() -> None:
    if not REFRESH_SCRIPT.exists():
        raise FileNotFoundError(
            f"refresh_database.py not found: {REFRESH_SCRIPT}"
        )

    log("Refreshing PostgreSQL from fresh Railpull CSVs...")

    result = subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT)],
        cwd=BACKEND_DIR,
        text=True,
        capture_output=True,
    )

    if result.stdout.strip():
        log(result.stdout.strip())

    if result.returncode != 0:
        if result.stderr.strip():
            log(result.stderr.strip())

        raise RuntimeError(
            "PostgreSQL refresh failed. "
            "The previous database should remain active."
        )

    log("PostgreSQL refresh completed successfully.")


def clear_redis() -> None:
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    client.flushdb()
    log("Redis cache cleared successfully.")


def delete_backup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automatic Train Info Finder data refresh"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="check owner repo and refresh age without crawling",
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="run a fresh NTES crawl immediately",
    )

    parser.add_argument(
        "--interval-days",
        type=int,
        default=DEFAULT_INTERVAL_DAYS,
        help=f"automatic refresh interval (default {DEFAULT_INTERVAL_DAYS})",
    )

    args = parser.parse_args()

    log("=" * 62)
    log("TRAIN INFO FINDER AUTOMATIC DATA SYNC")
    log("=" * 62)

    backup_raw = None
    backup_out = None
    raw_existed = False
    out_existed = False
    database_switched = False

    try:
        sync_owner_repo()

        due, previous = refresh_due(args.interval_days)

        if previous is None:
            log("No previous successful snapshot timestamp found.")
        else:
            log(
                "Current data snapshot time: "
                + previous.strftime("%Y-%m-%d %H:%M:%S")
            )

        log(f"Configured refresh interval: {args.interval_days} days.")

        if args.check_only:
            if due:
                log("CHECK ONLY: a fresh crawl is due.")
            else:
                next_time = previous + timedelta(days=args.interval_days)
                log(
                    "CHECK ONLY: data is not due yet. "
                    "Next refresh due around: "
                    + next_time.strftime("%Y-%m-%d %H:%M:%S")
                )
            return 0

        if not args.force_refresh and not due:
            next_time = previous + timedelta(days=args.interval_days)
            log(
                "No fresh crawl needed yet. Next refresh due around: "
                + next_time.strftime("%Y-%m-%d %H:%M:%S")
            )
            return 0

        if args.force_refresh:
            log("Forced refresh requested.")
        else:
            log("Scheduled timetable refresh is due.")

        preflight_redis()

        (
            backup_raw,
            backup_out,
            raw_existed,
            out_existed,
        ) = build_fresh_snapshot()

        refresh_postgresql()
        database_switched = True

        clear_redis()

        MARKER_FILE.write_text(
            datetime.now().isoformat(timespec="seconds"),
            encoding="utf-8",
        )

        delete_backup(backup_raw)
        delete_backup(backup_out)

        log(
            "SYNC COMPLETE: fresh NTES data is now active "
            "in PostgreSQL and Redis has been invalidated."
        )
        return 0

    except Exception as error:
        log(f"SYNC FAILED: {type(error).__name__}: {error}")

        if (
            not database_switched
            and backup_raw is not None
            and backup_out is not None
        ):
            try:
                restore_directory(RAW_DIR, backup_raw, raw_existed)
                restore_directory(OUT_DIR, backup_out, out_existed)
                log("Previous Railpull snapshot restored.")
            except Exception as restore_error:
                log(
                    "WARNING: could not restore previous data directories: "
                    f"{restore_error}"
                )

        return 1

    finally:
        log("=" * 62)


if __name__ == "__main__":
    raise SystemExit(main())
