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

    # Mail (for sending rich student assignment emails)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME or None)
