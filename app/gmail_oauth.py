import base64
import hashlib
import json
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib import error as urllib_error
from urllib import request as urllib_request

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app import db
from app.models import AppSetting


# gmail.send cannot call users.getProfile; gmail.metadata is minimal for profile email.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.metadata",
]
GMAIL_CREDENTIALS_KEY = "gmail_oauth_credentials"
GMAIL_ACCOUNT_EMAIL_KEY = "gmail_oauth_account_email"


def new_gmail_oauth_code_verifier():
    """Random PKCE verifier for OAuth (must be reused on authorize + token steps)."""
    return secrets.token_urlsafe(48)


def gmail_oauth_configured():
    """Return True when the OAuth client settings are available."""
    return all(
        current_app.config.get(key)
        for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI")
    )


def _setting_get(key, default=""):
    row = AppSetting.query.get(key)
    return (row.value if row and row.value is not None else default) or default


def _setting_set(key, value):
    row = AppSetting.query.get(key)
    if row:
        row.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))
    db.session.commit()


def _setting_delete(key):
    row = AppSetting.query.get(key)
    if row:
        db.session.delete(row)
        db.session.commit()


def _fernet():
    secret = current_app.config.get("SECRET_KEY") or current_app.secret_key or ""
    if not secret:
        raise RuntimeError("SECRET_KEY is required to store Gmail tokens.")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_text(value):
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _decrypt_text(value):
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")


def get_gmail_connection_status():
    """Return a small status payload for the assignments page."""
    credentials = load_gmail_credentials(refresh_if_needed=False)
    return {
        "configured": gmail_oauth_configured(),
        "connected": bool(credentials and (credentials.refresh_token or credentials.token)),
        "account_email": _setting_get(GMAIL_ACCOUNT_EMAIL_KEY, ""),
    }


def build_gmail_flow(redirect_uri=None, state=None, code_verifier=None):
    """Create an OAuth flow configured for the Gmail send scope.

    For web apps the authorize and token steps run on different requests; pass
    the same PKCE ``code_verifier`` on connect and callback (store in session).
    """
    if not gmail_oauth_configured():
        raise RuntimeError("Missing Google OAuth settings.")

    redirect_uri = redirect_uri or current_app.config.get("GOOGLE_REDIRECT_URI")
    client_config = {
        "web": {
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow_kwargs = {}
    if code_verifier is not None:
        flow_kwargs["code_verifier"] = code_verifier
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES, **flow_kwargs)
    if state is not None:
        flow.state = state
    flow.redirect_uri = redirect_uri
    return flow


def store_gmail_credentials(credentials):
    """Persist the OAuth credentials and the connected Gmail address."""
    _setting_set(GMAIL_CREDENTIALS_KEY, _encrypt_text(credentials.to_json()))


def _load_raw_credentials():
    raw_value = _setting_get(GMAIL_CREDENTIALS_KEY, "")
    if not raw_value:
        return None

    try:
        return json.loads(_decrypt_text(raw_value))
    except (InvalidToken, json.JSONDecodeError):
        clear_gmail_credentials()
        return None


def load_gmail_credentials(refresh_if_needed=True):
    """Load saved Gmail credentials and refresh them when possible."""
    raw_info = _load_raw_credentials()
    if not raw_info:
        return None

    credentials = Credentials.from_authorized_user_info(raw_info, scopes=GMAIL_SCOPES)
    if refresh_if_needed and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleRequest())
            store_gmail_credentials(credentials)
        except Exception:
            clear_gmail_credentials()
            return None

    return credentials


def clear_gmail_credentials():
    """Remove the stored Gmail OAuth credentials."""
    _setting_delete(GMAIL_CREDENTIALS_KEY)
    _setting_delete(GMAIL_ACCOUNT_EMAIL_KEY)


def set_gmail_account_email(email):
    _setting_set(GMAIL_ACCOUNT_EMAIL_KEY, email or "")


def get_gmail_account_email():
    return _setting_get(GMAIL_ACCOUNT_EMAIL_KEY, "")


def get_gmail_service(refresh_if_needed=True):
    """Build an authenticated Gmail API client."""
    credentials = load_gmail_credentials(refresh_if_needed=refresh_if_needed)
    if not credentials:
        raise RuntimeError("Gmail account is not connected.")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def get_gmail_profile_email():
    """Fetch the authenticated Gmail account email from the API."""
    service = get_gmail_service(refresh_if_needed=True)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def revoke_gmail_credentials():
    """Ask Google to revoke the current token and clear local storage."""
    credentials = load_gmail_credentials(refresh_if_needed=False)
    token = None
    if credentials:
        token = credentials.refresh_token or credentials.token

    if token:
        request = urllib_request.Request(
            "https://oauth2.googleapis.com/revoke",
            data=f"token={token}".encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urllib_request.urlopen(request, timeout=10)
        except urllib_error.HTTPError:
            pass
        except OSError:
            pass

    clear_gmail_credentials()


def _build_mime_message(subject, to_email, plain_body, html_body, from_email=None):
    message = MIMEMultipart("alternative")
    if from_email:
        message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(plain_body or "", "plain", "utf-8"))
    message.attach(MIMEText(html_body or "", "html", "utf-8"))
    return message


def send_gmail_message(subject, to_email, plain_body, html_body, from_email=None):
    """Send a message through Gmail API and return the API response."""
    service = get_gmail_service(refresh_if_needed=True)
    if from_email:
        sender_email = from_email
    else:
        sender_email = get_gmail_account_email()

    message = _build_mime_message(subject, to_email, plain_body, html_body, sender_email or None)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    try:
        return service.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()
    except HttpError as exc:
        raise RuntimeError(f"Gmail API error: {exc}") from exc
