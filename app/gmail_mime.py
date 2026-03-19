"""
MIME multipart/alternative for Gmail API raw send (stdlib only).
SMTP policy RFC-2047-encodes non-ASCII Subject.
"""
from email.message import EmailMessage
from email.policy import SMTP


def build_multipart_email(subject, to_email, plain_body, html_body, from_email=None):
    message = EmailMessage(policy=SMTP)
    if from_email:
        message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject if subject is not None else ""
    message.set_content(plain_body or "", subtype="plain", charset="utf-8")
    message.add_alternative(html_body or "", subtype="html", charset="utf-8")
    return message
