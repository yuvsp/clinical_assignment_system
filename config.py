import os

try:
    from sqlalchemy.pool import NullPool
except ImportError:
    NullPool = None


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    _default_sqlite = f"sqlite:///{os.path.join(BASE_DIR, 'clinical_assignment.db')}"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", _default_sqlite)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24).hex()
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    # Use NullPool with Supabase transaction pooler (port 6543) to avoid connection limits
    _uri = os.getenv("DATABASE_URL", "")
    if _uri and _uri.startswith(("postgresql://", "postgres://")) and NullPool is not None:
        SQLALCHEMY_ENGINE_OPTIONS = {"poolclass": NullPool}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # Gmail OAuth2 (for sending rich student assignment emails)
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
