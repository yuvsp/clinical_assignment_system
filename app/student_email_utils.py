"""Unique synthetic emails for students without a real address."""

import re
import secrets

from app import db
from app.models import Student

# Historical single placeholder shared by many rows (migration replaces these)
LEGACY_PLACEHOLDER_EMAIL = "add_email@gmail.com"

# New placeholders: add_email_<8 hex chars>@gmail.com
SYNTHETIC_EMAIL_RE = re.compile(r"^add_email_[a-f0-9]{8}@gmail\.com$", re.IGNORECASE)


def is_legacy_placeholder_email(email: str) -> bool:
    if not email or not str(email).strip():
        return True
    return str(email).strip().lower() == LEGACY_PLACEHOLDER_EMAIL.lower()


def is_synthetic_student_email(email: str) -> bool:
    return bool(email and SYNTHETIC_EMAIL_RE.match(str(email).strip()))


def generate_unique_student_email() -> str:
    """Return a unique placeholder email (add_email_<hex8>@gmail.com)."""
    for _ in range(64):
        candidate = f"add_email_{secrets.token_hex(4)}@gmail.com"
        exists = db.session.query(Student.id).filter(Student.email == candidate).first()
        if not exists:
            return candidate
    raise RuntimeError("לא ניתן ליצור כתובת אימייל ייחודית לסטודנטית — נסו שוב.")
