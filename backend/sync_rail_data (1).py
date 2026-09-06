from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import redis
from dotenv import load_dotenv


# =========================================================
# PATHS / CONFIG
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
RAILPULL_DIR = PROJECT_ROOT / "railpull"
REFRESH_SCRIPT = BACKEND_DIR / "refresh_database.py"
ENV_FILE = PROJECT_ROOT / ".env"
LOG_FILE = BACKEND_DIR / "data_sync.log"

load_dotenv(ENV_FILE)

CSV_FILES = [
    RAILPULL_DIR / "data" / "out" / "stations.csv",
    RAILPULL_DIR / "data" / "out" / "trains.csv",
    RAILPULL_DIR / "data" / "out" / "stops.csv",
]

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))


# =========================================================
# LOGGING
# =========================================================

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


# =========================================================
# COMMAND HELPER
# =========================================================

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
            f"Command failed ({result.returncode}): "
            + " ".join(command)
        )

    return result.stdout.strip()


# =========================================================
# CSV CHANGE DETECTION
# =========================================================

def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def csv_snapshot() -> dict[str, str | None]:
    return {
        path.name: file_hash(path)
        for path in CSV_FILES
    }


def changed_csvs(
    before: dict[str, str | None],
    after: dict[str, str | None],
) -> list[str]:
    return [
        name
        for name in after
        if before.get(name) != after.get(name)
    ]


# =========================================================
# GIT REMOTE SYNC
# =========================================================

def sync_remote_repo() -> None:
    if not RAILPULL_DIR.exists():
        raise FileNotFoundError(
            f"Railpull folder not found: {RAILPULL_DIR}"
        )

    if not (RAILPULL_DIR / ".git").exists():
        raise RuntimeError(
            "The railpull folder is not a Git repository. "
            "It must be cloned from the owner's remote repository "
            "for automatic owner updates to work."
        )

    log("Checking Railpull remote repository...")

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
        raise RuntimeError(
            "Railpull is in detached HEAD state. "
            "Switch it to a normal branch before automation."
        )

    # Refuse to overwrite local edits automatically.
    local_changes = run_command(
        ["git", "status", "--porcelain"],
        RAILPULL_DIR,
    )

    if local_changes:
        raise RuntimeError(
            "Railpull has uncommitted local changes. "
            "Automatic pull stopped to avoid overwriting your work."
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
        log("Remote repository is already up to date.")
        return

    log(
        f"Remote update found on branch '{branch}'. "
        "Pulling latest owner changes..."
    )

    run_command(
        ["git", "pull", "--ff-only", "origin", branch],
        RAILPULL_DIR,
    )

    log("Railpull remote update pulled successfully.")


# =========================================================
# POSTGRESQL REFRESH
# =========================================================

def refresh_postgresql() -> None:
    if not REFRESH_SCRIPT.exists():
        raise FileNotFoundError(
            f"refresh_database.py not found: {REFRESH_SCRIPT}"
        )

    log("Refreshing PostgreSQL from updated CSV files...")

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
            "Redis was NOT cleared, and the previous database "
            "should remain active because refresh_database.py "
            "uses a transaction."
        )

    log("PostgreSQL refresh completed successfully.")


# =========================================================
# REDIS INVALIDATION
# =========================================================

def clear_redis_cache() -> None:
    log(
        f"Clearing Redis cache at "
        f"{REDIS_HOST}:{REDIS_PORT}..."
    )

    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    client.ping()
    client.flushdb()

    log("Redis cache cleared successfully.")


# =========================================================
# MAIN PIPELINE
# =========================================================

def main() -> int:
    log("=" * 58)
    log("TRAIN INFO FINDER DATA SYNC STARTED")
    log("=" * 58)

    try:
        before = csv_snapshot()

        sync_remote_repo()

        after = csv_snapshot()
        changed = changed_csvs(before, after)

        if not changed:
            log(
                "No changes detected in stations.csv, "
                "trains.csv, or stops.csv."
            )
            log("PostgreSQL and Redis were left untouched.")
            return 0

        log("Updated CSV files detected: " + ", ".join(changed))

        missing = [
            str(path)
            for path in CSV_FILES
            if not path.exists()
        ]

        if missing:
            raise FileNotFoundError(
                "Required CSV file(s) missing after pull:\n"
                + "\n".join(missing)
            )

        # IMPORTANT ORDER:
        # 1. PostgreSQL refresh succeeds.
        # 2. Only THEN clear Redis.
        refresh_postgresql()
        clear_redis_cache()

        log(
            "SYNC COMPLETE: website will now serve the "
            "latest pulled CSV data."
        )
        return 0

    except Exception as error:
        log(
            f"SYNC FAILED: {type(error).__name__}: {error}"
        )
        return 1

    finally:
        log("=" * 58)


if __name__ == "__main__":
    raise SystemExit(main())
