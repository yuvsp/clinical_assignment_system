"""create_db.py

Local helper for initializing the database.

- For SQLite: creates the local DB file (and directory if needed) and creates tables.
- For Postgres/Supabase: DOES NOT drop data by default. Use migrations ('flask db upgrade')
  or run this script with --create-only to create tables in an empty DB.

Usage:
  python create_db.py                # safe create (no drop) for Postgres; create tables for SQLite
  python create_db.py --reset        # DANGEROUS: drops all tables then recreates (use only on dev DB)
"""

import argparse
import os
import logging
from urllib.parse import urlparse

from app import create_app, db

logging.basicConfig(level=logging.INFO)

def _is_sqlite(uri: str) -> bool:
    return (uri or "").startswith("sqlite:")

def _ensure_sqlite_dir(uri: str):
    # sqlite:////abs/path.db or sqlite:///relative.db
    if not uri.startswith("sqlite:"):
        return
    # Strip scheme
    path = uri.replace("sqlite:///", "").replace("sqlite:////", "/")
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop all tables then recreate (DEV ONLY).")
    args = parser.parse_args()

    app = create_app()
    uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    logging.info(f"DB URI: {uri}")

    if _is_sqlite(uri):
        _ensure_sqlite_dir(uri)

    with app.app_context():
        if args.reset:
            logging.warning("Dropping ALL tables...")
            db.drop_all()
        logging.info("Creating tables (create_all)...")
        db.create_all()
        logging.info("Done.")

if __name__ == "__main__":
    main()
