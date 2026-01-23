import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

basedir = os.path.abspath(os.path.dirname(__file__))


def _normalize_database_url(raw_url: str) -> str:
    """
    Normalizes DB URLs for SQLAlchemy and cloud providers.
    - Converts postgres:// to postgresql://
    - Ensures sslmode=require for Supabase/hosted Postgres unless already set
    """
    if not raw_url:
        return raw_url

    # SQLAlchemy prefers "postgresql://"
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql://" + raw_url[len("postgres://") :]

    # Add sslmode=require when using Postgres unless already set
    if raw_url.startswith("postgresql://"):
        parts = urlparse(raw_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("sslmode", "require")
        parts = parts._replace(query=urlencode(query))
        raw_url = urlunparse(parts)

    return raw_url


def _is_supabase_pooler(url: str) -> bool:
    """
    Heuristic: Supabase pooler host typically contains 'pooler.supabase.com'
    and often uses port 6543 (transaction pooler).
    """
    if not url or not url.startswith("postgresql://"):
        return False

    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    port = parts.port
    return ("pooler.supabase.com" in host) or (port == 6543)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # If DATABASE_URL is set (Render env var), use it. Otherwise fallback to local sqlite.
    _raw_db_url = os.environ.get("DATABASE_URL")
    _db_url = _normalize_database_url(_raw_db_url) if _raw_db_url else None

    if _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # Local fallback (Linux/Render disk path not needed if using Supabase)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'clinical_assignment.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options:
    # - For Supabase pooler (transaction mode): let Supavisor pool; disable SQLAlchemy pooling (NullPool).
    # - For other Postgres: use pre_ping to avoid stale connections.
    if _db_url and _is_supabase_pooler(_db_url):
        # Import inside to avoid dependency issues when running sqlite-only locally
        from sqlalchemy.pool import NullPool

        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            "pool_pre_ping": True,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
        }
