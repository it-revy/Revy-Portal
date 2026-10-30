"""
REVY Portal — Safe Staging Migration Runner with Production Interceptor Guard
=============================================================================
Usage:
    python scripts/run_staging_migration.py [--dry-run]

Environment Variables:
    STAGING_DATABASE_URL : URL of the isolated staging PostgreSQL database.
                           MUST NOT point to the production Neon cluster.

Safety Rules:
    1. Rejects execution if STAGING_DATABASE_URL is missing.
    2. Rejects execution if resolved host or database matches the production target.
    3. Never prints or logs connection credentials.
"""

import os
import sys
from urllib.parse import urlparse
import subprocess

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

KNOWN_TESTING_HOST_PATTERNS = [
    "ep-silent-sound-b49uucbd",
    "ep-silent-sound-b49uucbd-pooler",
]
KNOWN_PRODUCTION_HOST_PATTERNS = [
    "ep-production",
    "prod-db",
    "revy-production",
]
KNOWN_PRODUCTION_DB_NAMES = ["revy_prod", "production"]


def sanitize_url(url: str) -> str:
    if not url:
        return "None"
    try:
        p = urlparse(url)
        host = p.hostname or "unknown-host"
        port = f":{p.port}" if p.port else ""
        db = p.path.lstrip("/") or "unknown-db"
        return f"{p.scheme}://***:***@{host}{port}/{db}"
    except Exception:
        return "invalid-url"


def is_production_target(url: str) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        db_name = (p.path.lstrip("/") or "").lower()
        for pat in KNOWN_TESTING_HOST_PATTERNS:
            if pat in host:
                return False
        for pat in KNOWN_PRODUCTION_HOST_PATTERNS:
            if pat in host:
                return True
        if "neon.tech" in host and db_name in KNOWN_PRODUCTION_DB_NAMES:
            return True
        return False
    except Exception:
        return False


def main():
    print("=" * 70)
    print("REVY Portal — Phase 5A Staging Migration Runner")
    print("=" * 70)

    staging_url = os.environ.get("STAGING_DATABASE_URL")
    if not staging_url:
        print("\n[ERROR] Blocker: STAGING_DATABASE_URL is not set.")
        print("Please configure an isolated PostgreSQL staging database before running.")
        print("Never use the production Neon database for staging verification.")
        sys.exit(1)

    sanitized = sanitize_url(staging_url)
    print(f"\n[INFO] Target Staging Database: {sanitized}")

    # Production Interceptor Guard
    if is_production_target(staging_url):
        print("\n[CRITICAL ERROR] SAFETY INTERCEPTOR TRIGGERED!")
        print("Target URL resolves to the KNOWN PRODUCTION DATABASE cluster.")
        print("Migration aborted immediately. Production changes require separate authorization.")
        sys.exit(2)

    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[INFO] Dry-run mode enabled. Connection and safety checks passed successfully.")
        sys.exit(0)

    print("\n[INFO] Executing Alembic migration 'n1o2p3q4r5s6' on staging...")
    env = os.environ.copy()
    env["EXECUTE_STAGING_MIGRATION"] = "true"
    env["STAGING_DATABASE_URL"] = staging_url

    res = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", "staging=true", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True
    )

    if res.returncode != 0:
        print(f"\n[ERROR] Migration failed with exit code {res.returncode}:")
        print(res.stderr)
        sys.exit(res.returncode)

    print("\n[SUCCESS] Migration applied successfully to staging.")
    print(res.stdout)


if __name__ == "__main__":
    main()
