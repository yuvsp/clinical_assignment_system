import os
import platform
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def _normalize_database_url(url: str) -> str:
    """
    Normalizes DATABASE_URL for SQLAlchemy + Postgres providers (e.g., Supabase).

    - Converts legacy 'postgres://' to 'postgresql://'
    - Ensures sslmode=require for Supabase/managed Postgres when not specified
    """
    if not url:
        return url

    # Heroku-style URLs sometimes start with postgres://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Add sslmode=require for Supabase if missing
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if ("supabase.com" in host) or (host.endswith(".supabase.co")):
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if "sslmode" not in q:
                q["sslmode"] = "require"
                parsed = parsed._replace(query=urlencode(q))
                url = urlunparse(parsed)
    except Exception:
        # If parsing fails, just return the original URL
        return url

    return url

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Prefer DATABASE_URL (Postgres/Supabase). Fallback to SQLite.
    if platform.system() == "Windows":
        default_sqlite = f"sqlite:///{os.path.join(BASE_DIR, 'clinical_assignment.db')}"
    else:
        default_sqlite = "sqlite:////data/clinical_assignment.db"

    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL", default_sqlite))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Helps long-running connections and managed Postgres
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
