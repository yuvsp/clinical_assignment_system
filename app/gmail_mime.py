"""
MIME multipart/alternative for Gmail API raw send (stdlib only).
Use RFC 2047 encoded Subject for broad compatibility.
"""
from email.charset import QP, Charset
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def build_multipart_email(
    subject,
    to_email,
    plain_body,
    html_body,
    from_email=None,
):
    message = MIMEMultipart("alternative")
    if from_email:
        message["From"] = from_email
    message["To"] = to_email
    subj = "" if subject is None else str(subject)
    utf8_q = Charset("utf-8")
    utf8_q.header_encoding = QP
    message["Subject"] = utf8_q.header_encode(subj)
    message.attach(MIMEText(plain_body or "", "plain", "utf-8"))
    message.attach(MIMEText(html_body or "", "html", "utf-8"))
    return message
