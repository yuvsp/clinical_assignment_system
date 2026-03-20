import os
from pathlib import Path

from app import create_app


def _load_local_env(env_file: str = ".env") -> None:
    """Load simple KEY=VALUE pairs from .env into process env."""
    env_path = Path(env_file)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        # Keep existing exported env vars as highest priority.
        os.environ.setdefault(key, value)


_load_local_env()
app = create_app()


def _resolve_ssl_context():
    """Return ssl_context value for Flask dev server."""
    use_https = os.getenv("LOCAL_HTTPS", "0").lower() in ("1", "true", "yes")
    if not use_https:
        return None

    cert_file = os.getenv("SSL_CERT_FILE", "").strip()
    key_file = os.getenv("SSL_KEY_FILE", "").strip()

    if cert_file and key_file:
        cert_path = Path(cert_file).expanduser().resolve()
        key_path = Path(key_file).expanduser().resolve()
        if not cert_path.exists():
            raise FileNotFoundError(f"SSL_CERT_FILE not found: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"SSL_KEY_FILE not found: {key_path}")
        return (str(cert_path), str(key_path))

    if cert_file or key_file:
        raise ValueError("Set both SSL_CERT_FILE and SSL_KEY_FILE, or neither.")

    # Avoid implicit adhoc certs; require explicit cert+key files for HTTPS.
    # This keeps local OAuth flows stable on HTTP unless certs are configured.
    return None


if __name__ == '__main__':
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=app.config.get("DEBUG", False),
        ssl_context=_resolve_ssl_context(),
    )
