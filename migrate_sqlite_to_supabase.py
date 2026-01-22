import os
import sqlite3
from typing import Dict, List, Any, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# -------------------------
# Config
# -------------------------
SQLITE_PATH = os.getenv("SQLITE_PATH", "instance/your_database.db")
POSTGRES_URL = os.getenv("DATABASE_URL")  # Supabase Postgres (pooler/direct)
DEFAULT_STUDENT_EMAIL = os.getenv("DEFAULT_STUDENT_EMAIL", "add_email@gmail.com")
DEFAULT_STUDENT_SEMESTER = os.getenv("DEFAULT_STUDENT_SEMESTER", "א")

# Migration order for FK safety
TABLES_IN_ORDER = [
    "field",
    "clinical_instructor",
    "student",
    "assignment",
]


# -------------------------
# Helpers
# -------------------------
def die(msg: str):
    raise RuntimeError(msg)


def sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def sqlite_fetch_all(conn: sqlite3.Connection, table: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM "{table}"')
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows


def pg_truncate(pg: Engine, table: str):
    # Force schema public to avoid search_path surprises
    with pg.begin() as tx:
        tx.execute(text(f'TRUNCATE TABLE public."{table}" RESTART IDENTITY CASCADE;'))


def pg_insert_upsert(
    pg: Engine,
    table: str,
    rows: List[Dict[str, Any]],
    pk: str = "id",
):
    if not rows:
        print(f"ℹ️  {table}: no rows to insert")
        return

    cols = list(rows[0].keys())
    col_list = ", ".join([f'"{c}"' for c in cols])
    placeholders = ", ".join([f":{c}" for c in cols])

    # Upsert: update all columns except PK
    update_cols = [c for c in cols if c != pk]
    set_clause = ", ".join([f'"{c}"=EXCLUDED."{c}"' for c in update_cols]) if update_cols else ""

    if set_clause:
        sql = text(
            f'INSERT INTO public."{table}" ({col_list}) VALUES ({placeholders}) '
            f'ON CONFLICT ("{pk}") DO UPDATE SET {set_clause}'
        )
    else:
        sql = text(
            f'INSERT INTO public."{table}" ({col_list}) VALUES ({placeholders}) '
            f'ON CONFLICT ("{pk}") DO NOTHING'
        )

    with pg.begin() as tx:
        for r in rows:
            tx.execute(sql, r)


def normalize_student_rows(sqlite_cols: List[str], sqlite_rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
    """
    Create rows dicts that match Postgres student schema (including email/semester defaults),
    regardless of whether SQLite has those columns.
    Expected Postgres columns (based on your newer design):
      id, name, email, preferred_field_id_1/2/3, preferred_practice_area, semester
    """
    out: List[Dict[str, Any]] = []
    for tup in sqlite_rows:
        d = dict(zip(sqlite_cols, tup))

        # Required base fields from SQLite
        base = {
            "id": d.get("id"),
            "name": d.get("name"),
            "preferred_field_id_1": d.get("preferred_field_id_1"),
            "preferred_field_id_2": d.get("preferred_field_id_2"),
            "preferred_field_id_3": d.get("preferred_field_id_3"),
            "preferred_practice_area": d.get("preferred_practice_area"),
        }

        # Fill defaults / handle missing columns
        email_val = d.get("email") if "email" in sqlite_cols else None
        sem_val = d.get("semester") if "semester" in sqlite_cols else None

        base["email"] = (email_val if email_val not in (None, "") else DEFAULT_STUDENT_EMAIL)
        base["semester"] = (sem_val if sem_val not in (None, "") else DEFAULT_STUDENT_SEMESTER)

        out.append(base)
    return out


def normalize_generic_rows(sqlite_cols: List[str], sqlite_rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
    """
    Generic: copy columns as-is.
    Good for tables where schema matches between SQLite and Postgres.
    """
    return [dict(zip(sqlite_cols, tup)) for tup in sqlite_rows]


def normalize_assignment_rows(sqlite_cols: List[str], sqlite_rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
    """
    Assignment schema can vary; we map only common known columns.
    Typical columns:
      id, student_id, instructor_id (nullable), assigned_day
    If your table has different columns, tell me and I’ll adjust.
    """
    out: List[Dict[str, Any]] = []
    for tup in sqlite_rows:
        d = dict(zip(sqlite_cols, tup))

        row = {}

        # Try the usual suspects:
        for col in ["id", "student_id", "instructor_id", "assigned_day"]:
            if col in sqlite_cols:
                row[col] = d.get(col)

        # If older schema had "date" instead of "assigned_day"
        if "assigned_day" not in row and "date" in sqlite_cols:
            row["assigned_day"] = d.get("date")

        # If instructor_id missing entirely, keep it NULL (Postgres must allow it)
        if "instructor_id" not in row:
            row["instructor_id"] = None

        out.append(row)

    return out


# -------------------------
# Main migration
# -------------------------
def main():
    if not POSTGRES_URL:
        die("Missing DATABASE_URL (target Supabase Postgres). Set it in your shell env vars.")

    if not os.path.exists(SQLITE_PATH):
        die(f"SQLite file not found: {SQLITE_PATH}")

    print(f"SQLite: {SQLITE_PATH}")
    # DO NOT print DATABASE_URL (secrets)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg = create_engine(POSTGRES_URL, pool_pre_ping=True)

    for table in TABLES_IN_ORDER:
        if not sqlite_table_exists(sqlite_conn, table):
            print(f"⚠️  SQLite table not found, skipping: {table}")
            continue

        sqlite_cols, sqlite_rows = sqlite_fetch_all(sqlite_conn, table)

        print(f"🧹 Truncating Postgres table: {table}")
        pg_truncate(pg, table)

        print(f"➡️  Migrating {table}: {len(sqlite_rows)} rows")

        # Normalize per table
        if table == "student":
            rows = normalize_student_rows(sqlite_cols, sqlite_rows)
        elif table == "assignment":
            rows = normalize_assignment_rows(sqlite_cols, sqlite_rows)
        else:
            rows = normalize_generic_rows(sqlite_cols, sqlite_rows)

        # Insert with upsert
        pg_insert_upsert(pg, table, rows, pk="id")
        print(f"✅ Done {table}")

    sqlite_conn.close()
    print("🎉 Migration completed successfully")


if __name__ == "__main__":
    main()
